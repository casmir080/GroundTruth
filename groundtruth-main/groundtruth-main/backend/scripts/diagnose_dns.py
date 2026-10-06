"""Isolate whether Python can resolve the DashScope host, independent of the app.

Usage (from backend/):
    python -m scripts.diagnose_dns
"""
import socket
import time

HOST = "dashscope-intl.aliyuncs.com"

for i in range(5):
    start = time.perf_counter()
    try:
        info = socket.getaddrinfo(HOST, 443)
        elapsed = time.perf_counter() - start
        print(f"attempt {i + 1}: OK in {elapsed:.2f}s -> {info[0][4][0]}")
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"attempt {i + 1}: FAILED in {elapsed:.2f}s -> {e}")
    time.sleep(1)
