import asyncio
import time
from typing import Optional, Callable, Awaitable
from .api import WeixinClient, WeixinApiError
from .config import load_weixin_account, load_sync_buf, save_sync_buf
from .models import GetUpdatesReq, WeixinMessage
from .utils import logger

SESSION_EXPIRED_ERRCODE = -14
SESSION_PAUSE_DURATION_MS = 3600 * 1000

async def monitor_weixin(
    account_id: str,
    message_handler: Callable[[WeixinMessage, WeixinClient, str], Awaitable[None]],
    base_url: Optional[str] = None
):
    account = load_weixin_account(account_id)
    if not account or not account.token:
        logger.error(f"Account {account_id} not configured or token missing.")
        return

    # Use configured base_url if not provided, else default
    api_url = base_url or account.baseUrl or "https://ilinkai.weixin.qq.com"
    client = WeixinClient(base_url=api_url, token=account.token)
    sync_buf = load_sync_buf(account_id)
    
    logger.info(f"Starting monitor for {account_id} with sync_buf len={len(sync_buf)}")
    
    consecutive_failures = 0
    next_timeout_ms = 35000
    
    try:
        while True:
            try:
                logger.debug(f"[{account_id}] getUpdates: buf_len={len(sync_buf)}, timeout={next_timeout_ms}ms")
                req = GetUpdatesReq(get_updates_buf=sync_buf)
                resp = await client.get_updates(req, timeout_ms=next_timeout_ms)
                
                if resp.longpolling_timeout_ms and resp.longpolling_timeout_ms > 0:
                    next_timeout_ms = resp.longpolling_timeout_ms
                    logger.debug(f"[{account_id}] next polling timeout: {next_timeout_ms}ms")

                # Check for API errors
                errcode = resp.ret if resp.ret is not None and resp.ret != 0 else resp.errcode
                if errcode is not None and errcode != 0:
                     if errcode == SESSION_EXPIRED_ERRCODE:
                         logger.error(f"[{account_id}] Session expired. Pausing for 1 hour.")
                         await asyncio.sleep(3600)
                         consecutive_failures = 0
                         continue
                     
                     consecutive_failures += 1
                     logger.error(f"[{account_id}] getUpdates failed: ret={resp.ret} errcode={resp.errcode} errmsg={resp.errmsg}")
                     await asyncio.sleep(min(30, 2 * consecutive_failures))
                     continue

                consecutive_failures = 0
                
                # Update sync_buf if provided and different. Use get_updates_buf primarily.
                # Skip empty strings to avoid cursor reset (matching TS behavior)
                new_buf = resp.get_updates_buf if resp.get_updates_buf is not None else resp.sync_buf
                if new_buf and new_buf != sync_buf:
                    logger.debug(f"[{account_id}] Updating sync_buf: {len(sync_buf)} -> {len(new_buf)}")
                    sync_buf = new_buf
                    save_sync_buf(account_id, sync_buf)
                
                msgs = resp.msgs or []
                if msgs:
                    logger.info(f"[{account_id}] Received {len(msgs)} messages in this poll.")
                    for msg in msgs:
                        try:
                            # Try multiple ID fields for logging
                            msg_id = getattr(msg, 'message_id', None) or getattr(msg, 'msg_id', None) or getattr(msg, 'seq', 'unknown')
                            logger.debug(f"[{account_id}] Dispatching message: id={msg_id} from={getattr(msg, 'from_user_id', '?')}")
                            await message_handler(msg, client, account_id)
                        except Exception as e:
                            logger.error(f"[{account_id}] Error in message_handler: {e}")
                else:
                    logger.debug(f"[{account_id}] No new messages in this poll (msgs is empty or None).")

            except asyncio.CancelledError:
                logger.info("Monitor cancelled.")
                break
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(min(30, 2 * consecutive_failures))
    finally:
        await client.close()
