import os
import json
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel

DEFAULT_BASE_URL = "https://ilinkai.weixin.qq.com"
CDN_BASE_URL = "https://novac2c.cdn.weixin.qq.com/c2c"

class WeixinAccountData(BaseModel):
    token: Optional[str] = None
    savedAt: Optional[str] = None
    baseUrl: Optional[str] = None
    userId: Optional[str] = None

def resolve_state_dir() -> Path:
    state_dir = os.environ.get("OPENCLAW_STATE_DIR") or os.environ.get("CLAWDBOT_STATE_DIR")
    if state_dir and state_dir.strip():
        return Path(state_dir.strip())
    return Path.home() / ".openclaw"

def resolve_weixin_state_dir() -> Path:
    return resolve_state_dir() / "openclaw-weixin"

def resolve_account_index_path() -> Path:
    return resolve_weixin_state_dir() / "accounts.json"

def resolve_accounts_dir() -> Path:
    return resolve_weixin_state_dir() / "accounts"

def resolve_account_path(account_id: str) -> Path:
    return resolve_accounts_dir() / f"{account_id}.json"

def list_indexed_weixin_account_ids() -> List[str]:
    path = resolve_account_index_path()
    try:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(item) for item in data if isinstance(item, str) and item.strip()]
        return []
    except Exception:
        return []

def register_weixin_account_id(account_id: str) -> None:
    directory = resolve_weixin_state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    
    existing = list_indexed_weixin_account_ids()
    if account_id in existing:
        return
    
    updated = existing + [account_id]
    with open(resolve_account_index_path(), "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2)

def unregister_weixin_account_id(account_id: str) -> None:
    existing = list_indexed_weixin_account_ids()
    updated = [mid for mid in existing if mid != account_id]
    if len(updated) != len(existing):
        with open(resolve_account_index_path(), "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2)


def load_weixin_account(account_id: str) -> Optional[WeixinAccountData]:
    path = resolve_account_path(account_id)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return WeixinAccountData(**data)
    except Exception:
        pass
    # Legacy fallback and compat logic omitted for simplicity unless requested
    return None

def save_weixin_account(account_id: str, token: Optional[str] = None, base_url: Optional[str] = None, user_id: Optional[str] = None) -> None:
    directory = resolve_accounts_dir()
    directory.mkdir(parents=True, exist_ok=True)
    
    existing = load_weixin_account(account_id) or WeixinAccountData()
    
    # Update logic
    import datetime
    if token:
        existing.token = token.strip()
        existing.savedAt = datetime.datetime.now().isoformat()
    if base_url:
        existing.baseUrl = base_url.strip()
    if user_id is not None: # check for None explicitly as empty string might be valid to clear? No, logic says userId stores when provided
         existing.userId = user_id.strip() if user_id.strip() else None

    path = resolve_account_path(account_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(existing.model_dump_json(indent=2, exclude_none=True))
    
    try:
        path.chmod(0o600)
    except Exception:
        pass

def clear_weixin_account(account_id: str) -> None:
    directory = resolve_accounts_dir()
    files = [
        f"{account_id}.json",
        f"{account_id}.sync.json",
        f"{account_id}.context-tokens.json"
    ]
    for file_name in files:
        try:
            (directory / file_name).unlink(missing_ok=True)
        except Exception:
            pass

def resolve_sync_buf_path(account_id: str) -> Path:
    return resolve_accounts_dir() / f"{account_id}.sync.json"

def load_sync_buf(account_id: str) -> str:
    path = resolve_sync_buf_path(account_id)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Try both keys for backward compatibility
                return data.get("get_updates_buf") or data.get("buf") or ""
    except Exception:
        pass
    return ""

def save_sync_buf(account_id: str, buf: str) -> None:
    directory = resolve_accounts_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = resolve_sync_buf_path(account_id)
    with open(path, "w", encoding="utf-8") as f:
        # Save with the same key and format as TypeScript version
        json.dump({"get_updates_buf": buf, "savedAt": datetime.datetime.now().isoformat()}, f, indent=2)
