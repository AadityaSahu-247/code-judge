"""Deterministic fake for the ``litellm`` package.

The production LLM gateway imports ``litellm`` at module import time. When the
package is not installed (or must never be called for real) we inject this fake
into ``sys.modules`` from the test ``conftest`` *before* any ``app`` module is
imported, so ``LITELLM_AVAILABLE`` becomes ``True`` and ``litellm.completion``
is a controllable stub that tests can monkeypatch.

The default ``completion`` raises a descriptive error so an accidental real
call is loud instead of silently returning garbage.
"""

import sys
import types


def _completion_unpatched(**kwargs):  # pragma: no cover - guard only
    raise RuntimeError(
        "litellm.completion was called but no mock behaviour was installed. "
        "Configure the 'completion' fixture in a gateway test first."
    )


def install_fake_litellm() -> None:
    """Insert a fake ``litellm`` module into ``sys.modules`` (idempotent)."""
    if sys.modules.get("litellm") is not None:
        return
    fake = types.ModuleType("litellm")
    fake.completion = _completion_unpatched
    fake.telemetry = False
    fake.suppress_debug_info = True
    fake.set_verbose = False
    fake.drop_params = True
    sys.modules["litellm"] = fake
