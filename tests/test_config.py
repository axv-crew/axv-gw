"""Test to see what config sees."""
import os

# Set ENV before import
os.environ["AXV_HMAC_SECRET"] = "test123"

from app.config import settings

print(f"ENV AXV_HMAC_SECRET: {os.getenv('AXV_HMAC_SECRET')}")
print(f"Settings object: {settings}")
print(f"Settings AXV_HMAC_SECRET: {getattr(settings, 'AXV_HMAC_SECRET', 'NOT FOUND')}")
print(f"Settings HMAC_SECRET: {getattr(settings, 'HMAC_SECRET', 'NOT FOUND')}")
print(f"Settings dir: {[x for x in dir(settings) if 'HMAC' in x.upper()]}")
