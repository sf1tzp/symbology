"""Dynamic context-window sizing for the OpenAI-compatible (LM Studio) endpoint.

Filing sections vary wildly in size: a ``business_description`` may be a few KB
while a ``risk_factors`` section can run past 70k tokens. When a generation
request's prompt exceeds the context window the served model instance was loaded
with, LM Studio rejects it with a non-retryable 4xx — which previously aborted
the whole page-content pipeline for that company.

LM Studio can hold several *instances* of the same model, each with its own
``context_length``, and routes ``/v1/chat/completions`` by the ``model`` field:
the bare key (``google/gemma-4-e4b``) hits whichever instance LM Studio picks
(often a small default), while a suffixed id (``google/gemma-4-e4b:2``) targets
that exact instance. Crucially, ``/api/v1/models/load`` *adds a new instance*
rather than resizing the existing one — so naively loading a bigger context and
then calling the bare key still routed to the old, too-small instance.

So we don't unload-and-replace (which would break instances other workers are
mid-request on). Instead, before each call we:

1. ask LM Studio which instances of the model are loaded and how big each is,
2. reuse the largest one if it already covers this request, otherwise load a new
   instance sized to the request, and
3. return that instance's id so the caller can route the completion straight to
   it (``model="google/gemma-4-e4b:2"``).

Reusing the largest instance means same-size requests converge on one instance
instead of piling up new ones. This is LM Studio-specific and gated behind
``settings.openai.manage_context``; when disabled, or if the management API is
unreachable, generation falls back to the bare model name unchanged.
"""
import math
import threading
from typing import Dict, List, Optional, Tuple

import requests

from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# Serialises load decisions within a process so two threads don't each spin up a
# new instance for the same model at the same time.
_state_lock = threading.Lock()


def estimate_tokens(text: Optional[str]) -> int:
    """Roughly estimate the token count of ``text`` from its length.

    Uses ``settings.openai.chars_per_token`` (kept conservatively low so the
    estimate runs high — over-loading context is cheap, under-loading aborts the
    request). No tokenizer dependency: this only needs to be in the right
    ballpark to pick a context size.
    """
    if not text:
        return 0
    return int(len(text) / settings.openai.chars_per_token) + 1


def required_context_length(prompt_tokens: int, max_output_tokens: int) -> int:
    """Pick a context window large enough for the prompt plus its output.

    Adds a safety margin, rounds up to the configured bucket, and clamps to
    ``[context_min, context_max]``. The model's own ``max_context_length`` is
    applied separately by the caller (it isn't known here).
    """
    cfg = settings.openai
    raw = (prompt_tokens + max_output_tokens) * cfg.context_safety_margin
    bucketed = int(math.ceil(raw / cfg.context_bucket) * cfg.context_bucket)
    return max(cfg.context_min, min(cfg.context_max, bucketed))


def _request(method: str, path: str, timeout: float, **kwargs) -> dict:
    """Call the LM Studio management API and return the parsed JSON body."""
    cfg = settings.openai
    headers = {"Content-Type": "application/json"}
    # Reuse the OpenAI bearer token (same endpoint); skip the placeholder.
    if cfg.api_key and cfg.api_key != "not-needed":
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    response = requests.request(
        method,
        f"{cfg.management_url}{path}",
        headers=headers,
        timeout=timeout,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.content else {}


def _list_instances(model: str) -> Tuple[List[Dict], Optional[int]]:
    """Return ``(loaded_instances, model_max_context)`` for ``model``.

    Each instance is ``{"id": str, "context_length": int}``. ``model_max_context``
    is the model's own ceiling (``max_context_length``), or ``None`` if unknown.
    """
    data = _request("GET", "/models", timeout=settings.openai.request_timeout)
    for entry in data.get("models", []):
        if entry.get("key") == model:
            instances = [
                {
                    "id": inst.get("id"),
                    "context_length": inst.get("config", {}).get("context_length", 0),
                }
                for inst in entry.get("loaded_instances", [])
            ]
            return instances, entry.get("max_context_length")
    return [], None


def _load_instance(model: str, context_length: int) -> Optional[str]:
    """Load a new instance of ``model`` at ``context_length``; return its id."""
    data = _request(
        "POST",
        "/models/load",
        timeout=settings.openai.model_load_timeout,
        json={"model": model, "context_length": context_length},
    )
    return data.get("instance_id")


def ensure_model_loaded(
    model: str,
    prompt_text: str,
    max_output_tokens: int,
) -> Optional[str]:
    """Ensure an instance of ``model`` exists with enough context for this request.

    Returns the **instance id** the caller should send the completion to (e.g.
    ``"google/gemma-4-e4b:2"``), or ``None`` to fall back to the bare model name
    (when dynamic management is disabled, or the management API was unreachable).
    """
    cfg = settings.openai
    if not cfg.manage_context:
        return None

    prompt_tokens = estimate_tokens(prompt_text)
    target = required_context_length(prompt_tokens, max_output_tokens)
    needed = prompt_tokens + max_output_tokens

    with _state_lock:
        try:
            instances, model_max = _list_instances(model)
        except Exception as e:
            # Can't see server state — best-effort load so we at least try to
            # size up, then fall back to the bare model name for routing.
            logger.warning("model_list_failed", model=model, error=str(e))
            try:
                return _load_instance(model, target)
            except Exception as e2:
                logger.warning(
                    "model_load_failed", model=model, context_length=target, error=str(e2)
                )
                return None

        # Never ask for more than the model itself supports.
        if model_max:
            target = min(target, model_max)
        if needed > target:
            logger.warning(
                "model_context_exceeds_max",
                model=model,
                needed=needed,
                target=target,
                model_max=model_max,
            )

        # Reuse the largest already-loaded instance if it covers the request, so
        # similar-sized requests share one instance instead of spawning more.
        largest = max(instances, key=lambda i: i["context_length"], default=None)
        if largest and largest["context_length"] >= target:
            logger.debug(
                "reusing_model_instance",
                model=model,
                instance_id=largest["id"],
                context_length=largest["context_length"],
                target=target,
            )
            return largest["id"]

        # Nothing big enough: load a correctly-sized instance and route to it.
        try:
            logger.info(
                "loading_model_context",
                model=model,
                context_length=target,
                prompt_tokens=prompt_tokens,
                max_output_tokens=max_output_tokens,
                existing_instances=len(instances),
            )
            instance_id = _load_instance(model, target)
            logger.info(
                "loaded_model_instance",
                model=model,
                instance_id=instance_id,
                context_length=target,
            )
            return instance_id
        except Exception as e:
            logger.warning(
                "model_load_failed", model=model, context_length=target, error=str(e)
            )
            return None
