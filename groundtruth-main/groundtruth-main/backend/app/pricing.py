"""Approximate per-token USD pricing, for the cost_usd column on llm_calls.

Rates below are qwen-plus's published per-1M-token pricing as of mid-2026
(verify current figures at https://www.alibabacloud.com/help/en/model-studio/pricing
before relying on this for real budgeting -- provider pricing changes).
"""
from typing import Optional

# {model: (usd per 1M input tokens, usd per 1M output tokens)}
RATES_PER_MILLION = {
    "qwen-plus": (0.40, 1.20),
}
DEFAULT_RATE = (0.40, 1.20)  # fallback for an unlisted model, same as qwen-plus


def estimate_cost_usd(model: str, prompt_tokens: Optional[int], completion_tokens: Optional[int]) -> Optional[float]:
    if prompt_tokens is None or completion_tokens is None:
        return None
    in_rate, out_rate = RATES_PER_MILLION.get(model, DEFAULT_RATE)
    return round((prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000, 8)
