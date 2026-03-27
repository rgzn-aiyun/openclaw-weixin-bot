import os
import random
import base64
import struct
from pathlib import Path
from loguru import logger

def random_wechat_uin() -> str:
    """Generate a random X-WECHAT-UIN header value."""
    # Generate a random 32-bit unsigned integer
    uint32_val = random.getrandbits(32)
    # Convert it to a string representation of the number
    uint32_str = str(uint32_val)
    # Base64 encode the string
    return base64.b64encode(uint32_str.encode("utf-8")).decode("utf-8")

def ensure_trailing_slash(url: str) -> str:
    return url if url.endswith("/") else f"{url}/"

def read_channel_version() -> str:
    try:
        # Assuming run from root or package
        pkg_path = Path(__file__).parent.parent / "package.json"
        if pkg_path.exists():
            import json
            with open(pkg_path, "r") as f:
                data = json.load(f)
                return data.get("version", "unknown")
    except Exception:
        pass
    return "unknown"

CHANNEL_VERSION = read_channel_version()

def generate_id(prefix: str = "") -> str:
    import uuid
    uid = str(uuid.uuid4()).replace("-", "")[:16]
    return f"{prefix}-{uid}" if prefix else uid
