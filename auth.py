import sys
import time
import asyncio
import uuid
import qrcode
from typing import Dict, Optional, Any
from .api import WeixinClient, DEFAULT_LONG_POLL_TIMEOUT_MS
from .models import ActiveLogin, WeixinQrStartResult, WeixinQrWaitResult
from .utils import logger

ACTIVE_LOGIN_TTL_MS = 300_000
DEFAULT_ILINK_BOT_TYPE = "3"
MAX_QR_REFRESH_COUNT = 3

active_logins: Dict[str, ActiveLogin] = {}

def is_login_fresh(login: ActiveLogin) -> bool:
    return (time.time() * 1000) - login.startedAt < ACTIVE_LOGIN_TTL_MS

def purge_expired_logins():
    expired = [sid for sid, login in active_logins.items() if not is_login_fresh(login)]
    for sid in expired:
        del active_logins[sid]

async def start_weixin_login_with_qr(
    api_base_url: str,
    account_id: Optional[str] = None,
    bot_type: str = DEFAULT_ILINK_BOT_TYPE,
    force: bool = False
) -> WeixinQrStartResult:
    session_key = account_id or str(uuid.uuid4())
    purge_expired_logins()

    existing = active_logins.get(session_key)
    if not force and existing and is_login_fresh(existing) and existing.qrcodeUrl:
         return WeixinQrStartResult(
             qrcodeUrl=existing.qrcodeUrl,
             message="二维码已就绪，请使用微信扫描。",
             sessionKey=session_key
         )

    client = WeixinClient(base_url=api_base_url)
    try:
        logger.info(f"Starting Weixin login with bot_type={bot_type}")
        qr_resp = await client.get_bot_qrcode(bot_type)
        
        qrcode_str = qr_resp.get("qrcode")
        qrcode_img_content = qr_resp.get("qrcode_img_content")
        
        if not qrcode_str:
             raise ValueError("No qrcode returned")

        login = ActiveLogin(
            sessionKey=session_key,
            id=str(uuid.uuid4()),
            qrcode=qrcode_str,
            qrcodeUrl=qrcode_img_content or "",
            startedAt=time.time() * 1000
        )
        active_logins[session_key] = login
        
        return WeixinQrStartResult(
            qrcodeUrl=qrcode_img_content,
            message="使用微信扫描以下二维码，以完成连接。",
            sessionKey=session_key
        )
    except Exception as e:
        logger.error(f"Failed to start Weixin login: {e}")
        return WeixinQrStartResult(
            message=f"Failed to start login: {e}",
            sessionKey=session_key
        )
    finally:
        await client.close()

async def wait_for_weixin_login(
    session_key: str,
    api_base_url: str,
    timeout_ms: int = 480_000,
    verbose: bool = True,
    bot_type: str = DEFAULT_ILINK_BOT_TYPE
) -> WeixinQrWaitResult:
    
    active_login = active_logins.get(session_key)
    if not active_login:
        return WeixinQrWaitResult(
            connected=False,
            message="当前没有进行中的登录，请先发起登录。"
        )
        
    if not is_login_fresh(active_login):
        del active_logins[session_key]
        return WeixinQrWaitResult(
            connected=False,
            message="二维码已过期，请重新生成。"
        )

    deadline = (time.time() * 1000) + timeout_ms
    scanned_printed = False
    qr_refresh_count = 1
    
    client = WeixinClient(base_url=api_base_url)
    
    # Print QR code initially
    if verbose and active_login.qrcodeUrl:
         qr = qrcode.QRCode()
         qr.add_data(active_login.qrcodeUrl)
         qr.print_ascii(out=sys.stdout)
         print(f"二维码链接: {active_login.qrcodeUrl}")

    try:
        while (time.time() * 1000) < deadline:
            status_resp = await client.get_qrcode_status(active_login.qrcode)
            status = status_resp.get("status")
            active_login.status = status
            
            if status == "wait":
                if verbose:
                    sys.stdout.write(".")
                    sys.stdout.flush()
            elif status == "scaned":
                if not scanned_printed:
                    print("\n👀 已扫码，在微信继续操作...\n")
                    scanned_printed = True
            elif status == "expired":
                qr_refresh_count += 1
                if qr_refresh_count > MAX_QR_REFRESH_COUNT:
                    logger.warning(f"QR expired {MAX_QR_REFRESH_COUNT} times, giving up.")
                    del active_logins[session_key]
                    return WeixinQrWaitResult(
                        connected=False,
                        message="登录超时：二维码多次过期，请重新开始登录流程。"
                    )
                
                print(f"\n⏳ 二维码已过期，正在刷新...({qr_refresh_count}/{MAX_QR_REFRESH_COUNT})\n")
                
                # Refresh QR code
                try:
                     qr_resp = await client.get_bot_qrcode(bot_type)
                     active_login.qrcode = qr_resp.get("qrcode")
                     active_login.qrcodeUrl = qr_resp.get("qrcode_img_content")
                     active_login.startedAt = time.time() * 1000
                     scanned_printed = False
                     
                     print("🔄 新二维码已生成，请重新扫描\n")
                     if verbose and active_login.qrcodeUrl:
                         qr = qrcode.QRCode()
                         qr.add_data(active_login.qrcodeUrl)
                         qr.print_ascii(out=sys.stdout)
                         print(f"二维码链接: {active_login.qrcodeUrl}")
                except Exception as e:
                     logger.error(f"Failed to refresh QR code: {e}")
                     del active_logins[session_key]
                     return WeixinQrWaitResult(
                         connected=False,
                         message=f"刷新二维码失败: {e}"
                     )
            elif status == "confirmed":
                bot_token = status_resp.get("bot_token")
                ilink_bot_id = status_resp.get("ilink_bot_id")
                baseurl = status_resp.get("baseurl")
                ilink_user_id = status_resp.get("ilink_user_id")

                if not ilink_bot_id:
                     del active_logins[session_key]
                     return WeixinQrWaitResult(
                         connected=False,
                         message="登录失败：服务器未返回 ilink_bot_id。"
                     )

                active_login.botToken = bot_token
                del active_logins[session_key]
                
                return WeixinQrWaitResult(
                    connected=True,
                    botToken=bot_token,
                    accountId=ilink_bot_id,
                    baseUrl=baseurl,
                    userId=ilink_user_id,
                    message="✅ 与微信连接成功！"
                )
            
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error polling QR status: {e}")
        del active_logins[session_key]
        return WeixinQrWaitResult(
            connected=False,
            message=f"Login failed: {e}"
        )
    finally:
        await client.close()

    del active_logins[session_key]
    return WeixinQrWaitResult(
        connected=False,
        message="登录超时，请重试。"
    )
