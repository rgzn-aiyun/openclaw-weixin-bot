import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel

from .models import (
    BaseInfo, GetUpdatesReq, GetUpdatesResp,
    GetUploadUrlReq, GetUploadUrlResp,
    SendMessageReq, SendMessageResp,
    SendTypingReq, SendTypingResp,
    GetConfigResp
)
from .utils import random_wechat_uin, ensure_trailing_slash, CHANNEL_VERSION, logger

DEFAULT_LONG_POLL_TIMEOUT_MS = 35_000
DEFAULT_API_TIMEOUT_MS = 15_000
DEFAULT_CONFIG_TIMEOUT_MS = 10_000

class WeixinApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")

class WeixinClient:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = ensure_trailing_slash(base_url)
        self.token = token
        self._session: Optional[aiohttp.ClientSession] = None
        self._uin = random_wechat_uin()  # Keep UIN constant for this client instance

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _build_headers(self, body_bytes: bytes) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "Content-Length": str(len(body_bytes)),
            "X-WECHAT-UIN": random_wechat_uin(),
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token.strip()}"
        return headers

    def _build_base_info(self) -> Dict[str, Any]:
        return {"channel_version": CHANNEL_VERSION}

    async def _request(self, endpoint: str, payload: Dict[str, Any], timeout_ms: int) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        
        # Add base_info to payload
        if "base_info" not in payload:
            payload["base_info"] = self._build_base_info()
            
        body_json = json.dumps(payload)
        body_bytes = body_json.encode("utf-8")
        headers = self._build_headers(body_bytes)

        session = await self._get_session()
        
        timeout_sec = timeout_ms / 1000.0
        
        try:
            async with session.post(url, data=body_bytes, headers=headers, timeout=timeout_sec) as resp:
                raw_text = await resp.text()
                if not resp.ok:
                    raise WeixinApiError(resp.status, raw_text)
                
                if not raw_text or raw_text.strip() == "":
                    return {}
                
                try:
                    data = json.loads(raw_text)
                    if endpoint == "ilink/bot/getupdates":
                        logger.debug(f"getUpdates raw response: {raw_text[:1000]}...")
                    return data
                except json.JSONDecodeError:
                    if raw_text.lower() == "ok":
                        return {"ret": 0}
                    return {"raw_text": raw_text}
        except asyncio.TimeoutError:
             raise asyncio.TimeoutError(f"Request to {endpoint} timed out after {timeout_ms}ms")

    async def get_updates(self, req: GetUpdatesReq, timeout_ms: int = DEFAULT_LONG_POLL_TIMEOUT_MS) -> GetUpdatesResp:
        endpoint = "ilink/bot/getupdates"
        payload = req.model_dump(exclude_none=True)
        # Ensure get_updates_buf is present even if empty
        if "get_updates_buf" not in payload:
            payload["get_updates_buf"] = ""
            
        try:
            data = await self._request(endpoint, payload, timeout_ms)
            try:
                return GetUpdatesResp(**data)
            except Exception as ve:
                logger.error(f"Failed to parse getUpdates response: {ve}")
                # Log the data that failed to parse for debugging
                logger.debug(f"Data that failed to parse: {json.dumps(data)[:500]}...")
                return GetUpdatesResp(ret=0, msgs=[], get_updates_buf=req.get_updates_buf)
        except asyncio.TimeoutError:
            # Long-poll timeout is normal, return empty response
            return GetUpdatesResp(ret=0, msgs=[], get_updates_buf=req.get_updates_buf)

    async def get_upload_url(self, req: GetUploadUrlReq, timeout_ms: int = DEFAULT_API_TIMEOUT_MS) -> GetUploadUrlResp:
        endpoint = "ilink/bot/getuploadurl"
        payload = req.model_dump(exclude_none=True)
        data = await self._request(endpoint, payload, timeout_ms)
        return GetUploadUrlResp(**data)

    async def send_message(self, req: SendMessageReq, timeout_ms: int = DEFAULT_API_TIMEOUT_MS) -> SendMessageResp:
        endpoint = "ilink/bot/sendmessage"
        payload = req.model_dump(exclude_none=True)
        await self._request(endpoint, payload, timeout_ms)
        return SendMessageResp()

    async def send_typing(self, req: SendTypingReq, timeout_ms: int = DEFAULT_CONFIG_TIMEOUT_MS) -> SendTypingResp:
        endpoint = "ilink/bot/sendtyping"
        payload = req.model_dump(exclude_none=True)
        data = await self._request(endpoint, payload, timeout_ms)
        return SendTypingResp(**data)

    async def get_config(self, ilink_user_id: str, context_token: Optional[str] = None, timeout_ms: int = DEFAULT_CONFIG_TIMEOUT_MS) -> GetConfigResp:
        endpoint = "ilink/bot/getconfig"
        payload = {
            "ilink_user_id": ilink_user_id,
            "context_token": context_token
        }
        data = await self._request(endpoint, payload, timeout_ms)
        return GetConfigResp(**data)

    async def get_bot_qrcode(self, bot_type: str) -> Dict[str, Any]:
        url = f"{self.base_url}ilink/bot/get_bot_qrcode?bot_type={bot_type}"
        # No token, no body, just GET? TS uses fetch(url, {headers}). 
        # TS code: const response = await fetch(url.toString(), { headers });
        # It seems it's a GET request.
        
        headers = {} 
        # Add SKRouteTag if needed, handled by config logic which I haven't fully ported yet
        # For now, minimal headers.
        
        session = await self._get_session()
        async with session.get(url, headers=headers) as resp:
            if not resp.ok:
                raise WeixinApiError(resp.status, await resp.text())
            return await resp.json(content_type=None)

    async def get_qrcode_status(self, qrcode: str, timeout_ms: int = 35_000) -> Dict[str, Any]:
        # TS: long-poll with timeout.
        url = f"{self.base_url}ilink/bot/get_qrcode_status?qrcode={qrcode}"
        headers = {"iLink-App-ClientVersion": "1"}
        
        session = await self._get_session()
        timeout_sec = timeout_ms / 1000.0
        
        try:
            async with session.get(url, headers=headers, timeout=timeout_sec) as resp:
                if not resp.ok:
                    raise WeixinApiError(resp.status, await resp.text())
                return await resp.json(content_type=None)
        except asyncio.TimeoutError:
            # Client-side timeout, return status=wait
            return {"status": "wait"}
