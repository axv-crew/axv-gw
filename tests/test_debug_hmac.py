"""Debug HMAC signature generation."""

import hmac
import hashlib
import json
import time

TEST_SECRET = "test123"

# Test case
ts = 1234567890
payload = {"source": "test", "ping": True}

# Method 1: Our way
body_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
body_bytes = body_json.encode()
message = f"{ts}.".encode() + body_bytes

sig = hmac.new(
    TEST_SECRET.encode(),
    message,
    hashlib.sha256
).hexdigest()

print(f"Timestamp: {ts}")
print(f"Body JSON: {body_json}")
print(f"Body bytes: {body_bytes}")
print(f"Message: {message}")
print(f"Signature: sha256={sig}")
print()

# What security.py does
raw = body_json
msg_str = f"{ts}.{raw}"
msg_bytes = msg_str.encode("utf-8")
sig2 = hmac.new(TEST_SECRET.encode("utf-8"), msg_bytes, hashlib.sha256).hexdigest()

print(f"Security.py method:")
print(f"Message str: {msg_str}")
print(f"Message bytes: {msg_bytes}")
print(f"Signature: sha256={sig2}")
