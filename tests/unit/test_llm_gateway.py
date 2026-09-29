"""Unit tests for the LLM gateway (app.services.llm_gateway).

All provider calls go through the injected fake ``litellm`` module; no real
API keys or network traffic are used.
"""

import importlib
import json
import threading
import time as time_module

import pytest

from app.services.llm_gateway import (
    LLMGateway,
    LLMGatewayError,
    LLMTimeoutError,
)
from tests.mocks.providers import FakeHttpError, FakeResponse, FakeUsage

gw = importlib.import_module("app.services.llm_gateway.gateway")

MESSAGES = [{"role": "user", "content": "hello"}]


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(time_module, "monotonic", fake)
    return fake


@pytest.fixture
def env(monkeypatch):
    """Control the environment keys the gateway reads on construction."""
    values = {"GROQ_MODEL": "llama-3.3-70b-versatile"}

    def fake_getenv(name, default=""):
        return values.get(name, default)

    monkeypatch.setattr(gw.os, "getenv", fake_getenv)
    return values


@pytest.fixture
def completion(monkeypatch):
    """Provide a controllable, thread-safe fake for litellm.completion."""
    calls = []
    queue = []
    lock = threading.Lock()

    def fake_completion(**kwargs):
        with lock:
            calls.append(kwargs)
            behavior = queue.pop(0) if queue else None
        if callable(behavior):
            return behavior(kwargs)
        if isinstance(behavior, Exception):
            raise behavior
        if behavior is None:
            return FakeResponse()
        return behavior

    monkeypatch.setattr(gw.litellm, "completion", fake_completion)
    return {"calls": calls, "queue": queue}


def make_gateway(gemini=(), groq=(), env=None):
    if env is not None:
        env.pop("GEMINI_API_KEY", None)
        env.pop("GROQ_API_KEY", None)
        for index in range(1, 20):
            env.pop(f"GEMINI_API_KEY{index}", None)
            env.pop(f"GROQ_API_KEY{index}", None)
        if gemini:
            env["GEMINI_API_KEY"] = gemini[0]
        for index, key in enumerate(gemini[1:], start=1):
            env[f"GEMINI_API_KEY{index}"] = key
        if groq:
            env["GROQ_API_KEY"] = groq[0]
        for index, key in enumerate(groq[1:], start=1):
            env[f"GROQ_API_KEY{index}"] = key
    return LLMGateway()


def health_wait(g, endpoint_id):
    h = g.health()[endpoint_id]
    if h.state == "open":
        return h.open_until - time_module.monotonic()
    return h.cooldown_until - time_module.monotonic()


# ------------------------------------------------------------ rotation order
def test_rotation_interleaves_providers(env):
    g = make_gateway(gemini=("g0", "g1"), groq=("q0", "q1"), env=env)
    order = [(e.provider, e.key_index) for e in g.endpoints()]
    assert order == [
        ("gemini", 0),
        ("groq", 0),
        ("gemini", 1),
        ("groq", 1),
    ]


def test_uneven_key_sets_still_interleave(env):
    g = make_gateway(gemini=("g0", "g1", "g2"), groq=("q0",), env=env)
    order = [e.provider for e in g.endpoints()]
    assert order == ["gemini", "groq", "gemini", "gemini"]


def test_endpoint_ids_are_stable_and_scoped(env):
    g = make_gateway(gemini=("g0",), groq=("q0",), env=env)
    e0, e1 = g.endpoints()
    assert e0.endpoint_id.startswith("gemini:")
    assert e1.endpoint_id.startswith("groq:")
    assert e0.endpoint_id != e1.endpoint_id
    g2 = make_gateway(gemini=("g0",), groq=("q0",), env=env)
    assert g2.endpoints()[0].endpoint_id == e0.endpoint_id


# -------------------------------------------------------------- no API keys
def test_no_api_keys_raises(env):
    g = make_gateway(env=env)
    assert g.available() == 0
    with pytest.raises(LLMGatewayError, match="no LLM API keys"):
        g.complete(MESSAGES)


# ----------------------------------------------------------------- success
def test_success_uses_first_endpoint(env, completion):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    result = g.complete(MESSAGES)
    assert result.content == "ok"
    assert result.provider == "gemini"
    assert result.key_index == 0
    assert result.model_version == f"gemini/{gw.settings.gemini_model}#0"
    assert result.tokens.total_tokens == 30
    assert completion["calls"] and completion["calls"][0]["api_key"] == "g0"
    health = g.health()
    assert health[result.endpoint_id].success_count == 1
    assert health[result.endpoint_id].state == "closed"


# ---------------------------------------------------------------- failover
def test_failover_on_429(env, completion, clock):
    g = make_gateway(gemini=("g0",), groq=("q0",), env=env)
    completion["queue"].append(FakeHttpError("quota", status_code=429, retry_after=2))
    completion["queue"].append(FakeResponse(content="groq answer"))
    result = g.complete(MESSAGES)
    assert result.content == "groq answer"
    assert result.provider == "groq"
    health = g.health()
    gemini_id = [e.endpoint_id for e in g.endpoints() if e.provider == "gemini"][0]
    assert health[gemini_id].failure_count == 1
    assert health_wait(g, gemini_id) > 0
    assert health[result.endpoint_id].success_count == 1


def test_failover_on_500(env, completion):
    g = make_gateway(gemini=("g0",), groq=("q0",), env=env)
    completion["queue"].append(FakeHttpError("boom", status_code=500))
    completion["queue"].append(FakeResponse())
    result = g.complete(MESSAGES)
    assert result.provider == "groq"


def test_non_retryable_401_opens_breaker_but_fails_over(env, completion):
    g = make_gateway(gemini=("g0",), groq=("q0",), env=env)
    completion["queue"].append(FakeHttpError("bad key", status_code=401))
    completion["queue"].append(FakeResponse())
    result = g.complete(MESSAGES)
    assert result.provider == "groq"
    gemini_id = [e.endpoint_id for e in g.endpoints() if e.provider == "gemini"][0]
    assert g.health()[gemini_id].state == "open"
    assert g.health()[gemini_id].open_until > 0


# ---------------------------------------------------------------- retryable
@pytest.mark.parametrize(
    "status,expected",
    [
        (429, True), (500, True), (502, True), (503, True), (504, True),
        (400, False), (401, False), (403, False), (404, False), (None, True),
    ],
)
def test_retryable_status_classification(status, expected):
    assert gw._is_retryable(status) is expected


# ---------------------------------------------------- pure helper functions
def test_status_code_extracted_from_message():
    class WeirdError(Exception):
        pass

    assert gw._status_code(WeirdError("rate limit hit 429 quota")) == 429
    assert gw._status_code(WeirdError("no status here")) is None
    assert gw._status_code(FakeHttpError("x", status_code=403)) == 403


def test_classify_timeout_variants():
    assert gw._classify_timeout(TimeoutError("boom")) == "network"
    assert gw._classify_timeout(ValueError("connection timed out")) == "network"
    assert gw._classify_timeout(ValueError("gateway request timed out")) == "gateway"
    assert gw._classify_timeout(ValueError("provider request timed out")) == "provider"
    assert gw._classify_timeout(ValueError("not a timeout")) is None


def test_backoff_caps_at_max():
    assert gw._backoff_seconds(0) == 0.0
    assert gw._backoff_seconds(1) == gw.COOLDOWN_BASE_SECONDS
    assert gw._backoff_seconds(100) == gw.COOLDOWN_MAX_SECONDS


def test_avg_latency_zero_when_no_success():
    health = gw.HealthStats()
    assert health.avg_latency_ms() == 0.0


class _BodyErr(Exception):
    def __init__(self, body=None, response=None):
        super().__init__("boom")
        self.body = body
        self.response = response


class _RespText:
    def __init__(self, text):
        self.text = text


def test_retry_after_parsing():
    assert gw._retry_after(FakeHttpError("x", retry_after=45)) == 45.0
    assert gw._retry_after(FakeHttpError("x", retry_after=0)) == gw.COOLDOWN_BASE_SECONDS
    assert gw._retry_after(FakeHttpError("x", retry_after="oops")) == gw.COOLDOWN_BASE_SECONDS
    assert gw._retry_after(ValueError("rate limited, retry in 12s")) == 12.0
    assert gw._retry_after(ValueError("retry in NaN s")) == gw.COOLDOWN_BASE_SECONDS
    assert gw._retry_after(ValueError("nothing here")) == gw.COOLDOWN_BASE_SECONDS
    assert gw._retry_after(FakeHttpError("x", retry_after=999999)) == gw.COOLDOWN_MAX_SECONDS


def test_extract_body_handles_json_truncation_and_response():
    err = _BodyErr(body={"detail": "bad"})
    assert gw._extract_body(err) == '{"detail": "bad"}'

    class _Unserializable:
        pass

    err2 = _BodyErr(body=_Unserializable())
    assert gw._extract_body(err2) == json.dumps(str(err2.body))
    err3 = _BodyErr(body=None, response=_RespText("raw response"))
    assert gw._extract_body(err3) == "raw response"
    err4 = _BodyErr(body="x" * 3000)
    assert len(gw._extract_body(err4)) == 2000
    assert gw._extract_body(ValueError("no attrs")) is None


def test_extract_content_supports_list_and_empty():
    assert gw._extract_content(FakeResponse(content="plain")) == "plain"
    assert gw._extract_content(FakeResponse(content=["a", {"text": "b"}])) == "ab"
    assert gw._extract_content(FakeResponse(content=123)) == "123"
    assert gw._extract_content(object()) == ""
    assert gw._extract_content(FakeResponse(content=[])) == ""


def test_normalize_groq_model_strips_prefixes():
    assert gw._normalize_groq_model("  llama-3.3-70b ") == "llama-3.3-70b"
    assert gw._normalize_groq_model("groq:llama-3.3") == "llama-3.3"
    assert gw._normalize_groq_model("GROQ/llama-3.3") == "llama-3.3"


def test_avg_latency_with_successes():
    health = gw.HealthStats(success_count=3, total_latency_ms=124.6)
    assert health.avg_latency_ms() == 41.5


def test_retry_after_regex_parse_failure_falls_back():
    assert gw._retry_after(ValueError("rate limited, retry in NaN s")) == gw.COOLDOWN_BASE_SECONDS
    assert gw._retry_after(ValueError("rate limited, retry in 1..2s")) == gw.COOLDOWN_BASE_SECONDS


def test_extract_body_json_dump_failure_falls_back_to_str():
    err = _BodyErr(body={(1, 2): "x"})  # tuple key cannot be JSON-serialised
    assert gw._extract_body(err) == str(err.body)


def test_extract_usage_none_returns_empty():
    usage = gw._extract_usage(None)
    assert usage.total_tokens == 0


def test_extract_content_object_part_with_text():
    class _Part:
        def __init__(self, text):
            self.text = text

    assert gw._extract_content(FakeResponse(content=[_Part("hello"), "world"])) == "helloworld"


def test_candidates_returns_endpoints(env):
    g = make_gateway(gemini=("g0",), groq=("q0",), env=env)
    assert len(g.candidates()) == 2


def test_complete_json_mode_sets_response_format(env, completion):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    g.complete(MESSAGES, json_mode=True)
    assert completion["calls"][0]["response_format"] == {"type": "json_object"}


def test_complete_raises_when_litellm_missing(env, monkeypatch):
    monkeypatch.setattr(gw, "LITELLM_AVAILABLE", False)
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    with pytest.raises(LLMGatewayError, match="litellm is not installed"):
        g.complete(MESSAGES)


def test_safe_log_swallows_all_failures(env, completion, monkeypatch):
    g = make_gateway(gemini=("g0",), groq=(), env=env)

    def broken_log_event(*args, **kwargs):
        raise RuntimeError("log_event down")

    def broken_logger_log(*args, **kwargs):
        raise RuntimeError("logger.log down")

    monkeypatch.setattr(gw, "log_event", broken_log_event)
    monkeypatch.setattr(gw.logger, "log", broken_logger_log)
    result = g.complete(MESSAGES)  # must not raise despite both log paths failing
    assert result.content == "ok"


# -------------------------------------------------------------- all failing
def test_all_fail_raises_aggregate(env, completion):
    g = make_gateway(gemini=("g0", "g1"), groq=("q0",), env=env)
    for _ in range(3):
        completion["queue"].append(FakeHttpError("nope", status_code=503))
    with pytest.raises(LLMGatewayError, match="all 3 endpoints failed"):
        g.complete(MESSAGES)


def test_timeout_raises_timeout_error(env, completion):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    completion["queue"].append(TimeoutError("Request timed out"))
    with pytest.raises(LLMTimeoutError, match="timeout"):
        g.complete(MESSAGES)


# ------------------------------------------------------ circuit breaker
def test_circuit_breaker_skips_open_endpoint(env, completion, clock):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    endpoint_id = g.endpoints()[0].endpoint_id
    for _ in range(3):
        completion["queue"].append(FakeHttpError("fail", status_code=503))
        with pytest.raises(LLMGatewayError):
            g.complete(MESSAGES)
        clock.advance(61)
    assert g.health()[endpoint_id].state == "open"
    assert len(completion["calls"]) == 3  # no attempt once breaker opened
    with pytest.raises(LLMGatewayError, match="unavailable"):
        g.complete(MESSAGES)  # still open -> skipped, no new attempt
    assert len(completion["calls"]) == 3


def test_circuit_breaker_recovery_via_half_open(env, completion, clock):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    endpoint_id = g.endpoints()[0].endpoint_id
    for _ in range(3):
        completion["queue"].append(FakeHttpError("fail", status_code=503))
        with pytest.raises(LLMGatewayError):
            g.complete(MESSAGES)
        clock.advance(61)
    health = g.health()[endpoint_id]
    assert health.state == "open"
    clock.advance(health.open_until - clock.now + 1)
    completion["queue"].append(FakeResponse(content="recovered"))
    result = g.complete(MESSAGES)
    assert result.content == "recovered"
    assert g.health()[endpoint_id].state == "closed"
    assert g.health()[endpoint_id].success_count == 1


# ------------------------------------------------------------ cooldown
def test_cooldown_exponential_backoff(env, completion, clock):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    endpoint_id = g.endpoints()[0].endpoint_id
    waits = []
    for _ in range(3):
        completion["queue"].append(FakeHttpError("busy", status_code=429))
        with pytest.raises(LLMGatewayError):
            g.complete(MESSAGES)
        waits.append(round(health_wait(g, endpoint_id)))
        clock.advance(61)
    assert waits == [30, 60, 120]


def test_cooldown_respects_server_retry_after(env, completion, clock):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    endpoint_id = g.endpoints()[0].endpoint_id
    completion["queue"].append(FakeHttpError("quota", status_code=429, retry_after=45))
    with pytest.raises(LLMGatewayError):
        g.complete(MESSAGES)
    assert round(health_wait(g, endpoint_id)) == 45


def test_recovery_after_cooldown(env, completion, clock):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    endpoint_id = g.endpoints()[0].endpoint_id
    completion["queue"].append(FakeHttpError("busy", status_code=429))
    with pytest.raises(LLMGatewayError):
        g.complete(MESSAGES)
    clock.advance(31)
    completion["queue"].append(FakeResponse(content="back"))
    result = g.complete(MESSAGES)
    assert result.content == "back"
    assert g.health()[endpoint_id].success_count == 1
    assert g.health()[endpoint_id].consecutive_failures == 0


def test_all_cooled_down_short_circuit(env, completion, clock):
    g = make_gateway(gemini=("g0", "g1"), groq=(), env=env)
    for _ in range(2):
        completion["queue"].append(FakeHttpError("busy", status_code=429))
    with pytest.raises(LLMGatewayError, match="all 2 endpoints failed"):
        g.complete(MESSAGES)
    with pytest.raises(LLMGatewayError, match="unavailable"):
        g.complete(MESSAGES)


# ---------------------------------------------------------------- timeout
def test_timeout_failover_to_next_provider(env, completion, clock):
    g = make_gateway(gemini=("g0",), groq=("q0",), env=env)
    completion["queue"].append(TimeoutError("Request timed out"))
    completion["queue"].append(FakeResponse(content="groq ok"))
    result = g.complete(MESSAGES)
    assert result.provider == "groq"
    assert result.content == "groq ok"


def test_gateway_deadline_raises(env, completion, clock):
    g = make_gateway(gemini=("g0", "g1", "g2", "g3"), groq=(), env=env)

    def slow_behavior(kwargs):
        clock.advance(130)  # simulate a call that blows past the deadline
        raise TimeoutError("Request timed out")

    for _ in range(4):
        completion["queue"].append(slow_behavior)
    with pytest.raises(LLMTimeoutError, match="gateway timeout"):
        g.complete(MESSAGES)


# ------------------------------------------------------ caching and refresh
def test_keys_cached_until_refresh(env, completion):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    assert g.available() == 1
    env["GEMINI_API_KEY1"] = "g1"  # simulate new key appearing in env
    assert g.available() == 1  # not picked up until refresh
    assert g.refresh() == 2
    assert g.available() == 2


def test_refresh_drops_stale_health(env, completion):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    gemini_id = g.endpoints()[0].endpoint_id
    completion["queue"].append(FakeHttpError("fail", status_code=503))
    with pytest.raises(LLMGatewayError):
        g.complete(MESSAGES)
    assert gemini_id in g.health()
    env.pop("GEMINI_API_KEY", None)
    assert g.refresh() == 0
    assert gemini_id not in g.health()


def test_refresh_preserves_health_for_surviving_keys(env, completion):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    gemini_id = g.endpoints()[0].endpoint_id
    completion["queue"].append(FakeResponse(content="ok"))
    g.complete(MESSAGES)
    env["GEMINI_API_KEY1"] = "g1"
    g.refresh()
    assert g.health()[gemini_id].success_count == 1


# ----------------------------------------------------------------- metrics
def test_metrics_and_events_logged(env, completion, monkeypatch):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    events = []

    def fake_log_event(logger, level, event, **fields):
        events.append((event, fields))

    monkeypatch.setattr(gw, "log_event", fake_log_event)
    result = g.complete(MESSAGES)
    assert result.content == "ok"
    names = [e[0] for e in events]
    assert "llm_request" in names
    assert "llm_response" in names
    metrics = [e for e in events if e[0] == "gateway_metrics"]
    assert metrics
    fields = metrics[-1][1]
    assert fields["success"] is True
    assert fields["provider"] == "gemini"
    assert fields["model"] == gw.settings.gemini_model
    assert fields["latency_ms"] >= 0
    assert fields["tokens"]["total_tokens"] == 30
    assert fields["retries"] == 0
    assert fields["failovers"] == 0
    assert fields["timeout"] is False
    assert fields["response_size"] == 2


def test_metrics_report_failover_and_tokens(env, completion, monkeypatch):
    g = make_gateway(gemini=("g0",), groq=("q0",), env=env)
    events = []

    def fake_log_event(logger, level, event, **fields):
        events.append((event, fields))

    monkeypatch.setattr(gw, "log_event", fake_log_event)
    completion["queue"].append(FakeHttpError("busy", status_code=503))
    completion["queue"].append(FakeResponse(content="groq ok", usage=FakeUsage(5, 7)))
    g.complete(MESSAGES)
    metrics = [e for e in events if e[0] == "gateway_metrics"][0][1]
    assert metrics["success"] is True
    assert metrics["provider"] == "groq"
    assert metrics["failovers"] == 1
    assert metrics["retries"] == 1
    assert metrics["tokens"]["completion_tokens"] == 7


def test_logging_never_raises(env, completion, monkeypatch):
    g = make_gateway(gemini=("g0",), groq=(), env=env)

    def broken_log_event(*args, **kwargs):
        raise RuntimeError("log subsystem down")

    monkeypatch.setattr(gw, "log_event", broken_log_event)
    result = g.complete(MESSAGES)  # must not raise despite broken logging
    assert result.content == "ok"


# ------------------------------------------------------------- thread safety
def test_concurrent_calls_are_consistent(env, completion):
    g = make_gateway(gemini=("g0",), groq=(), env=env)
    completion["queue"][:] = [FakeResponse(content=f"r{i}") for i in range(50)]
    results = []
    results_lock = threading.Lock()

    def worker():
        r = g.complete(MESSAGES)
        with results_lock:
            results.append(r.content)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert set(results) == {f"r{i}" for i in range(50)}
    endpoint_id = g.endpoints()[0].endpoint_id
    assert g.health()[endpoint_id].success_count == 50
