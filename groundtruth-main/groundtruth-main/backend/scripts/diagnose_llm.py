"""Diagnose the app's actual configured connection to the LLM, end to end.

Reads the real DASHSCOPE_BASE_URL from your .env (doesn't print the API key),
tests DNS for that exact host, then makes one real API call outside the
retry wrapper so we see the raw error if something still fails.

Usage (from backend/):
    python -m scripts.diagnose_llm
"""
import socket
import time
from urllib.parse import urlparse

from openai import OpenAI

from app.config import settings

url = settings.dashscope_base_url
host = urlparse(url).hostname
print(f"configured DASHSCOPE_BASE_URL: {url}")
print(f"resolving host: {host}\n")

for i in range(3):
    start = time.perf_counter()
    try:
        info = socket.getaddrinfo(host, 443)
        elapsed = time.perf_counter() - start
        print(f"DNS attempt {i + 1}: OK in {elapsed:.2f}s -> {info[0][4][0]}")
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"DNS attempt {i + 1}: FAILED in {elapsed:.2f}s -> {e}")
    time.sleep(1)

print()
try:
    client = OpenAI(api_key=settings.dashscope_api_key, base_url=url)
    start = time.perf_counter()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": "Say OK"}],
    )
    elapsed = time.perf_counter() - start
    print(f"live API call: OK in {elapsed:.2f}s -> {resp.choices[0].message.content!r}")
except Exception as e:
    print(f"live API call: FAILED -> {type(e).__name__}: {e}")
