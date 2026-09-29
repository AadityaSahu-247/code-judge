"""Multi-provider LLM gateway built on LiteLLM.

Reads the API keys declared in the project ``.env`` file once at startup and
rotates across them automatically:

  * ``GEMINI_API_KEY``, ``GEMINI_API_KEY1..4``  (5 keys)
  * ``GROQ_API_KEY``, ``GROQ_API_KEY1..4``      (5 keys)

Providers are interleaved (Gemini #0, Groq #0, Gemini #1, Groq #1, ...) so a
single provider outage does not exhaust every request on that provider before
failing over. Keys are cached in memory and can be re-read with ``refresh()``.

Every endpoint is identified by a stable ``provider:key_hash`` id. Cooldowns
and circuit-breaker state are tracked per id (never by list index). A circuit
breaker opens after repeated failures and recovers automatically through a
half-open probe. Errors are failed-over only for transient statuses (429, 500,
502, 503, 504 and transport errors); client errors (400, 401, 403) are never
retried.
"""

import hashlib
import json
import logging
import os
import re
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4

from dotenv import load_dotenv

from app.config import settings
from app.logging_config import get_logger, log_event

try:
    import litellm
    LITELLM_AVAILABLE = True
except Exception:  # pragma: no cover - environment without litellm
    litellm = None
    LITELLM_AVAILABLE = False

logger = get_logger("llm_gateway")

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_FILE, override=False)

if litellm is not None:
    litellm.telemetry = False
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    litellm.drop_params = True

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT_SECONDS = 30
GATEWAY_TIMEOUT_SECONDS = 120

COOLDOWN_BASE_SECONDS = 30
COOLDOWN_MAX_SECONDS = 300
BREAKER_FAILURE_THRESHOLD = 3

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
NON_RETRYABLE_STATUSES = frozenset({400, 401, 403})

GEMINI_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


class LLMGatewayError(RuntimeError):
    pass


class LLMTimeoutError(LLMGatewayError):
    pass


@dataclass(frozen=True)
class ProviderEndpoint:
    provider: str
    model: str
    litellm_model: str
    api_key: str
    endpoint_id: str
    key_index: int


@dataclass
class HealthStats:
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    last_latency_ms: Optional[float] = None
    last_failure: Optional[str] = None
    last_failure_at: Optional[float] = None
    last_error: Optional[str] = None
    state: str = "closed"  # closed | open | half_open
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    open_until: float = 0.0

    def avg_latency_ms(self) -> float:
        if self.success_count <= 0:
            return 0.0
        return round(self.total_latency_ms / self.success_count, 1)


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class CompletionResult:
    content: str
    provider: str
    model: str
    key_index: int
    model_version: str
    endpoint_id: str
    latency_ms: float
    tokens: TokenUsage
    request_id: str


def _env_keys(prefix: str) -> list[str]:
    values = []
    for index in range(20):
        name = prefix if index == 0 else f"{prefix}{index}"
        value = os.getenv(name, "")
        if value:
            values.append(value)
    return values


def _normalize_groq_model(raw: str) -> str:
    raw = raw.strip()
    for prefix in ("groq:", "groq/"):
        if raw.lower().startswith(prefix):
            return raw[len(prefix):].strip()
    return raw


def _endpoint_id(provider: str, api_key: str) -> str:
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:8]
    return f"{provider}:{digest}"


def _status_code(exc: Exception) -> Optional[int]:
    status = getattr(exc, "status_code", None)
    if status is None:
        match = re.search(r"\b([45]\d\d)\b", str(exc))
        if match:
            status = int(match.group(1))
    return status


def _is_timeout(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    lowered = str(exc).lower()
    return any(
        token in lowered
        for token in ("timed out", "read timeout", "request timed out", "timeout error")
    )


def _classify_timeout(exc: Exception) -> Optional[str]:
    if not _is_timeout(exc):
        return None
    lowered = str(exc).lower()
    if isinstance(exc, TimeoutError):
        return "network"
    if any(token in lowered for token in ("connect", "connection", "conn refused")):
        return "network"
    if "gateway" in lowered:
        return "gateway"
    return "provider"


def _is_retryable(status: Optional[int]) -> bool:
    if status is None:
        return True
    return status in RETRYABLE_STATUSES


def _backoff_seconds(streak: int) -> float:
    if streak <= 0:
        return 0.0
    return min(COOLDOWN_BASE_SECONDS * (2 ** (streak - 1)), COOLDOWN_MAX_SECONDS)


def _retry_after(exc: Exception) -> float:
    retry = getattr(exc, "retry_after", None)
    if retry:
        try:
            return max(1.0, min(float(retry), COOLDOWN_MAX_SECONDS))
        except (TypeError, ValueError):
            pass
    match = re.search(r"retry in ([0-9.]+)s", str(exc))
    if match:
        try:
            return max(1.0, min(float(match.group(1)), COOLDOWN_MAX_SECONDS))
        except (TypeError, ValueError):
            pass
    return COOLDOWN_BASE_SECONDS


def _extract_body(exc: Exception) -> Optional[str]:
    body = getattr(exc, "body", None)
    if body is not None and not isinstance(body, str):
        try:
            body = json.dumps(body, default=str)
        except Exception:
            body = str(body)
    if body is None:
        response = getattr(exc, "response", None)
        if response is not None:
            body = getattr(response, "text", None)
    if isinstance(body, str) and len(body) > 2000:
        body = body[:2000]
    return body


def _extract_content(response: object) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError):
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if text:
                    parts.append(text)
            else:
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)
        return "".join(parts)
    return str(content)


def _extract_usage(response: object) -> TokenUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
        completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
    )


def _safe_log(level: int, event: str, **fields) -> None:
    try:
        log_event(logger, level, event, **fields)
    except Exception:
        try:
            logger.log(level, event)
        except Exception:
            pass


class LLMGateway:
    """Thread-safe multi-provider completion gateway with key rotation,
    exponential-backoff cooldowns, a circuit breaker and health tracking."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._health: dict[str, HealthStats] = {}
        self._endpoints: list[ProviderEndpoint] = []
        self._refresh_endpoints()

    # ------------------------------------------------------------------ keys
    def _refresh_endpoints(self) -> None:
        gemini_keys = _env_keys("GEMINI_API_KEY")
        groq_keys = _env_keys("GROQ_API_KEY")
        self._endpoints = self._build_endpoints(gemini_keys, groq_keys)

    def _build_endpoints(
        self,
        gemini_keys: list[str],
        groq_keys: list[str],
    ) -> list[ProviderEndpoint]:
        gemini_model = settings.gemini_model
        groq_model = _normalize_groq_model(os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL))

        gemini = [
            ProviderEndpoint(
                provider="gemini",
                model=gemini_model,
                litellm_model=f"gemini/{gemini_model}",
                api_key=key,
                endpoint_id=_endpoint_id("gemini", key),
                key_index=index,
            )
            for index, key in enumerate(gemini_keys)
        ]
        groq = [
            ProviderEndpoint(
                provider="groq",
                model=groq_model,
                litellm_model=f"groq/{groq_model}",
                api_key=key,
                endpoint_id=_endpoint_id("groq", key),
                key_index=index,
            )
            for index, key in enumerate(groq_keys)
        ]

        interleaved: list[ProviderEndpoint] = []
        for index in range(max(len(gemini), len(groq))):
            if index < len(gemini):
                interleaved.append(gemini[index])
            if index < len(groq):
                interleaved.append(groq[index])
        return interleaved

    def refresh(self) -> int:
        """Re-read API keys from the environment and rebuild the endpoint list.

        Health/circuit state for endpoints that still exist is preserved;
        state for removed keys is dropped. Returns the new endpoint count.
        """
        with self._lock:
            old_ids = {e.endpoint_id for e in self._endpoints}
            self._refresh_endpoints()
            new_ids = {e.endpoint_id for e in self._endpoints}
            self._health = {
                endpoint_id: stats
                for endpoint_id, stats in self._health.items()
                if endpoint_id in new_ids
            }
            return len(self._endpoints)

    def endpoints(self) -> list[ProviderEndpoint]:
        with self._lock:
            return list(self._endpoints)

    def candidates(self) -> list[ProviderEndpoint]:
        return self.endpoints()

    def available(self) -> int:
        return len(self.endpoints())

    def health(self) -> dict[str, HealthStats]:
        with self._lock:
            return {endpoint_id: stats for endpoint_id, stats in self._health.items()}

    # ---------------------------------------------------------------- state
    def _eligible(self, endpoint: ProviderEndpoint) -> bool:
        with self._lock:
            now = time.monotonic()
            health = self._health.setdefault(endpoint.endpoint_id, HealthStats())
            if health.state == "open":
                if now < health.open_until:
                    return False
                health.state = "half_open"
                return True
            if now < health.cooldown_until:
                return False
            return True

    def _record_success(self, endpoint: ProviderEndpoint, latency_ms: float) -> None:
        with self._lock:
            health = self._health.setdefault(endpoint.endpoint_id, HealthStats())
            health.success_count += 1
            health.consecutive_failures = 0
            health.state = "closed"
            health.cooldown_until = 0.0
            health.open_until = 0.0
            health.last_latency_ms = latency_ms
            health.total_latency_ms += latency_ms
            health.last_error = None
            health.last_failure = None

    def _record_failure(
        self,
        endpoint: ProviderEndpoint,
        exc: Exception,
        status: Optional[int],
        retryable: bool,
    ) -> float:
        with self._lock:
            now = time.monotonic()
            health = self._health.setdefault(endpoint.endpoint_id, HealthStats())
            health.failure_count += 1
            health.consecutive_failures += 1
            health.last_failure = f"{type(exc).__name__}:{status if status is not None else 'transport'}"
            health.last_failure_at = now
            health.last_error = str(exc)[:300]

            streak = health.consecutive_failures
            backoff = _backoff_seconds(streak)
            error_retry = _retry_after(exc) if retryable else COOLDOWN_MAX_SECONDS
            cooldown = min(max(backoff, error_retry), COOLDOWN_MAX_SECONDS)

            if not retryable:
                # Client errors (400/401/403) are permanent for this key.
                health.state = "open"
                health.open_until = now + cooldown
            elif streak >= BREAKER_FAILURE_THRESHOLD:
                health.state = "open"
                health.open_until = now + cooldown
            else:
                health.state = "closed"
                health.cooldown_until = now + cooldown
            return cooldown

    # ----------------------------------------------------------------- call
    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 500,
        json_mode: bool = False,
    ) -> CompletionResult:
        """Send a completion through the first healthy provider/key.

        Returns a :class:`CompletionResult`. Raises ``LLMTimeoutError`` when no
        endpoint answers within the request/gateway timeout budget, and
        ``LLMGatewayError`` when every endpoint failed for other reasons.
        """
        request_id = uuid4().hex[:12]
        endpoints = self.endpoints()
        if not endpoints:
            raise LLMGatewayError(
                "no LLM API keys configured (GEMINI_API_KEY / GROQ_API_KEY)"
            )

        started = time.monotonic()
        deadline = started + GATEWAY_TIMEOUT_SECONDS
        attempts = 0
        failovers = 0
        last_error: Optional[Exception] = None
        last_status: Optional[int] = None
        last_timeout_type: Optional[str] = None
        last_cooldown: Optional[float] = None
        result: Optional[CompletionResult] = None

        for offset, endpoint in enumerate(endpoints):
            if time.monotonic() > deadline:
                self._log_metrics(
                    request_id=request_id,
                    success=False,
                    provider=endpoint.provider,
                    model=endpoint.model,
                    latency_ms=round((time.monotonic() - started) * 1000, 1),
                    tokens=None,
                    attempts=attempts,
                    failovers=failovers,
                    timeout="gateway",
                    response_size=None,
                )
                raise LLMTimeoutError(
                    f"request {request_id}: gateway timeout after "
                    f"{GATEWAY_TIMEOUT_SECONDS}s ({attempts} attempts)"
                )

            if not self._eligible(endpoint):
                continue

            attempts += 1
            try:
                result = self._call(
                    endpoint,
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    request_id=request_id,
                )
                self._record_success(endpoint, result.latency_ms)
                break
            except LLMTimeoutError as exc:
                last_error = exc
                last_status = None
                last_timeout_type = _classify_timeout(exc) or "provider"
                last_cooldown = self._record_failure(endpoint, exc, None, retryable=True)
                failovers += 1
            except Exception as exc:
                last_error = exc
                last_status = _status_code(exc)
                last_cooldown = self._record_failure(
                    endpoint, exc, last_status, _is_retryable(last_status)
                )
                failovers += 1
            self._log_attempt(
                request_id=request_id,
                endpoint=endpoint,
                status=last_status,
                error=type(last_error).__name__,
                cooldown=last_cooldown,
            )

        elapsed_ms = round((time.monotonic() - started) * 1000, 1)

        if result is not None:
            self._log_metrics(
                request_id=request_id,
                success=True,
                provider=result.provider,
                model=result.model,
                latency_ms=elapsed_ms,
                tokens=result.tokens,
                attempts=attempts,
                failovers=failovers,
                timeout=False,
                response_size=len(result.content),
            )
            return result

        # Everything failed or was unavailable.
        if last_timeout_type is not None:
            self._log_metrics(
                request_id=request_id,
                success=False,
                provider=endpoints[-1].provider,
                model=endpoints[-1].model,
                latency_ms=elapsed_ms,
                tokens=None,
                attempts=attempts,
                failovers=failovers,
                timeout=last_timeout_type,
                response_size=None,
            )
            raise LLMTimeoutError(
                f"request {request_id}: all endpoints failed by timeout "
                f"({last_timeout_type}); attempts={attempts}; "
                f"cooldown={last_cooldown}s; last error: "
                f"{type(last_error).__name__}: {str(last_error)[:300]}"
            ) from last_error

        self._log_metrics(
            request_id=request_id,
            success=False,
            provider=endpoints[-1].provider,
            model=endpoints[-1].model,
            latency_ms=elapsed_ms,
            tokens=None,
            attempts=attempts,
            failovers=failovers,
            timeout=None,
            response_size=None,
        )
        if attempts == 0:
            raise LLMGatewayError(
                f"request {request_id}: all {len(endpoints)} endpoints are "
                f"unavailable (cooldown/circuit open); try again shortly"
            )
        raise LLMGatewayError(
            f"request {request_id}: all {len(endpoints)} endpoints failed; "
            f"attempts={attempts}; last status={last_status}; "
            f"cooldown={last_cooldown}s; last error: "
            f"{type(last_error).__name__}: {str(last_error)[:300]}"
        ) from last_error

    def _call(
        self,
        endpoint: ProviderEndpoint,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        request_id: str,
    ) -> CompletionResult:
        if not LITELLM_AVAILABLE:
            raise LLMGatewayError("litellm is not installed")

        kwargs = {
            "model": endpoint.litellm_model,
            "messages": messages,
            "api_key": endpoint.api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": REQUEST_TIMEOUT_SECONDS,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if endpoint.provider == "gemini":
            kwargs["safety_settings"] = GEMINI_SAFETY_SETTINGS

        started = time.monotonic()
        _safe_log(
            logging.INFO,
            "llm_request",
            request_id=request_id,
            provider=endpoint.provider,
            model=endpoint.model,
            endpoint_id=endpoint.endpoint_id,
            key_index=endpoint.key_index,
            json_mode=json_mode,
        )
        try:
            response = litellm.completion(**kwargs)
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - started) * 1000, 1)
            status = _status_code(exc)
            timed_out = _is_timeout(exc)
            timeout_type = _classify_timeout(exc)
            _safe_log(
                logging.ERROR,
                "llm_error",
                request_id=request_id,
                provider=endpoint.provider,
                model=endpoint.model,
                endpoint_id=endpoint.endpoint_id,
                key_index=endpoint.key_index,
                status=status,
                timeout=timed_out,
                timeout_type=timeout_type,
                latency_ms=elapsed_ms,
                error=type(exc).__name__,
                detail=str(exc)[:2000],
                response_body=_extract_body(exc),
                traceback=traceback.format_exc(),
            )
            if timed_out:
                raise LLMTimeoutError(
                    f"request {request_id}: {timeout_type or 'provider'} timeout on "
                    f"{endpoint.litellm_model} after {REQUEST_TIMEOUT_SECONDS}s"
                ) from exc
            raise

        content = _extract_content(response)
        usage = _extract_usage(response)
        latency_ms = round((time.monotonic() - started) * 1000, 1)
        _safe_log(
            logging.INFO,
            "llm_response",
            request_id=request_id,
            provider=endpoint.provider,
            model=endpoint.model,
            endpoint_id=endpoint.endpoint_id,
            key_index=endpoint.key_index,
            status=200,
            latency_ms=latency_ms,
            tokens=asdict(usage),
            response_size=len(content),
            preview=content[:200],
        )
        return CompletionResult(
            content=content,
            provider=endpoint.provider,
            model=endpoint.model,
            key_index=endpoint.key_index,
            model_version=f"{endpoint.provider}/{endpoint.model}#{endpoint.key_index}",
            endpoint_id=endpoint.endpoint_id,
            latency_ms=latency_ms,
            tokens=usage,
            request_id=request_id,
        )

    # ------------------------------------------------------------- metrics
    def _log_attempt(
        self,
        *,
        request_id: str,
        endpoint: ProviderEndpoint,
        status: Optional[int],
        error: str,
        cooldown: Optional[float],
    ) -> None:
        _safe_log(
            logging.WARNING,
            "gateway_attempt",
            request_id=request_id,
            provider=endpoint.provider,
            model=endpoint.model,
            endpoint_id=endpoint.endpoint_id,
            status=status,
            error=error,
            cooldown_seconds=cooldown,
        )

    def _log_metrics(
        self,
        *,
        request_id: str,
        success: bool,
        provider: Optional[str],
        model: Optional[str],
        latency_ms: float,
        tokens: Optional[TokenUsage],
        attempts: int,
        failovers: int,
        timeout: object,
        response_size: Optional[int],
    ) -> None:
        _safe_log(
            logging.INFO if success else logging.WARNING,
            "gateway_metrics",
            request_id=request_id,
            success=success,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            tokens=asdict(tokens) if tokens is not None else None,
            retries=max(0, attempts - 1),
            failovers=failovers,
            timeout=timeout,
            response_size=response_size,
        )


gateway = LLMGateway()
