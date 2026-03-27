import time
from typing import Optional, Dict, Any, List
from .api import WeixinClient
from .models import SendMessageReq, WeixinMessage, MessageItem, TextItem, MessageItemType, MessageType, MessageState
from .utils import logger, generate_id

async def send_message(
    client: WeixinClient,
    bot_id: str,
    to_user_id: str,
    text: str,
    context_token: Optional[str] = None
) -> None:
    msg_item = MessageItem(
        type=MessageItemType.TEXT,
        text_item=TextItem(text=text)
    )
    
    # Matching TypeScript behavior:
    # - from_user_id: empty string
    # - client_id: generated with prefix
    # - message_state: FINISH
    weixin_msg = WeixinMessage(
        from_user_id="", 
        to_user_id=to_user_id,
        client_id=generate_id("openclaw-weixin"),
        message_type=MessageType.BOT,
        message_state=MessageState.FINISH,
        item_list=[msg_item],
        context_token=context_token,
        create_time_ms=int(time.time() * 1000)
    )
    
    req = SendMessageReq(msg=weixin_msg)
    try:
        await client.send_message(req)
    except Exception as e:
        logger.error(f"Failed to send message via API: {e}")
        raise
