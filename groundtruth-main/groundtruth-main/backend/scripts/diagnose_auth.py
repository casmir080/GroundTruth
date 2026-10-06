"""Check what GROUNDTRUTH_API_KEY the app would actually load right now,
and from where. Catches two common causes of "still 401 after I fixed
.env": (1) the server process was never actually restarted, so it's still
holding the old value, or (2) it's being run from a directory that doesn't
have this .env file in it.

Usage (from backend/):
    python -m scripts.diagnose_auth
"""
import os
from pathlib import Path

from app.config import settings

print(f"current working directory: {os.getcwd()}")
print(f".env found here: {Path('.env').exists()}")

key = settings.api_key
if not key:
    print("GROUNDTRUTH_API_KEY: NOT SET -- every protected route will 401 no matter what header you send")
else:
    masked = key[:2] + "*" * max(len(key) - 4, 0) + key[-2:] if len(key) > 4 else "*" * len(key)
    print(f"GROUNDTRUTH_API_KEY loaded: {masked} (length {len(key)})")
