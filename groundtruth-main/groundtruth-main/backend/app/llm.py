import time
from typing import Optional

from openai import OpenAI
from opentelemetry import trace

from .config import settings
from .db import get_client
from .pricing import estimate_cost_usd
from .telemetry import chat_span

_client: Optional[OpenAI] = None


def _llm() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
        )
    return _client


def _call_with_retry(messages, attempts: int = 3, base_delay: float = 2.0):
    """Retry on transient failures (DNS timeouts, dropped connections, etc).

    A slow first DNS attempt is normal on some networks -- nslookup itself
    retries automatically. Python's socket layer doesn't, so we do it here:
    2s, then 4s between attempts.
    """
    last_err: Optional[Exception] = None
    for i in range(attempts):
        try:
            return _llm().chat.completions.create(
                model=settings.llm_model,
                messages=messages,
            )
        except Exception as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(base_delay * (i + 1))
    raise last_err


def logged_completion(
    prompt: str,
    *,
    source: str = "live",
    query_type: Optional[str] = None,
    system: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Call the LLM and log the call (success or failure) to Supabase.
    Also emits an OpenTelemetry span (GenAI semantic conventions) and
    estimates cost from token usage.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    text = None
    model_version = None
    prompt_tokens = None
    completion_tokens = None
    error = None

    start = time.perf_counter()
    with chat_span(model=settings.llm_model) as span:
        try:
            resp = _call_with_retry(messages)
            text = resp.choices[0].message.content
            model_version = resp.model
            if resp.usage:
                prompt_tokens = resp.usage.prompt_tokens
                completion_tokens = resp.usage.completion_tokens
        except Exception as e:
            error = str(e)
        latency_ms = int((time.perf_counter() - start) * 1000)
        cost_usd = estimate_cost_usd(settings.llm_model, prompt_tokens, completion_tokens)

        if model_version:
            span.set_attribute("gen_ai.response.model", model_version)
        if prompt_tokens is not None:
            span.set_attribute("gen_ai.usage.input_tokens", prompt_tokens)
        if completion_tokens is not None:
            span.set_attribute("gen_ai.usage.output_tokens", completion_tokens)
        span.set_attribute("groundtruth.latency_ms", latency_ms)
        if cost_usd is not None:
            span.set_attribute("groundtruth.cost_usd", cost_usd)
        if error:
            span.set_attribute("error.type", "APIError")
            span.set_status(trace.Status(trace.StatusCode.ERROR, error))

    row = {
        "source": source,
        "query_type": query_type,
        "prompt": prompt,
        "response": text,
        "model": settings.llm_model,
        "model_version": model_version,
        "latency_ms": latency_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost_usd,
        "error": error,
        "metadata": metadata or {},
    }
    saved = get_client().table("llm_calls").insert(row).execute().data[0]

    if error:
        raise RuntimeError(error)

    return {
        "id": saved["id"],
        "response": text,
        "model_version": model_version,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
    }
