from typing import List, Optional, Dict, Any, Union
from enum import IntEnum
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UploadMediaType(IntEnum):
    IMAGE = 1
    VIDEO = 2
    FILE = 3
    VOICE = 4

class MessageType(IntEnum):
    NONE = 0
    USER = 1
    BOT = 2

class MessageItemType(IntEnum):
    NONE = 0
    TEXT = 1
    IMAGE = 2
    VOICE = 3
    FILE = 4
    VIDEO = 5

class MessageState(IntEnum):
    NEW = 0
    GENERATING = 1
    FINISH = 2

class TypingStatus(IntEnum):
    TYPING = 1
    CANCEL = 2

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BaseInfo(BaseModel):
    channel_version: Optional[str] = None

class GetUploadUrlReq(BaseModel):
    filekey: Optional[str] = None
    media_type: Optional[int] = None
    to_user_id: Optional[str] = None
    rawsize: Optional[int] = None
    rawfilemd5: Optional[str] = None
    filesize: Optional[int] = None
    thumb_rawsize: Optional[int] = None
    thumb_rawfilemd5: Optional[str] = None
    thumb_filesize: Optional[int] = None
    no_need_thumb: Optional[bool] = False
    aeskey: Optional[str] = None

class GetUploadUrlResp(BaseModel):
    upload_param: Optional[str] = None
    thumb_upload_param: Optional[str] = None

class CDNMedia(BaseModel):
    encrypt_query_param: Optional[str] = None
    aes_key: Optional[str] = None
    encrypt_type: Optional[int] = None

class TextItem(BaseModel):
    text: Optional[str] = None

class ImageItem(BaseModel):
    media: Optional[CDNMedia] = None
    thumb_media: Optional[CDNMedia] = None
    aeskey: Optional[str] = None
    url: Optional[str] = None
    mid_size: Optional[int] = None
    thumb_size: Optional[int] = None
    thumb_height: Optional[int] = None
    thumb_width: Optional[int] = None
    hd_size: Optional[int] = None

class VoiceItem(BaseModel):
    media: Optional[CDNMedia] = None
    encode_type: Optional[int] = None
    bits_per_sample: Optional[int] = None
    sample_rate: Optional[int] = None
    playtime: Optional[int] = None
    text: Optional[str] = None

class FileItem(BaseModel):
    media: Optional[CDNMedia] = None
    file_name: Optional[str] = None
    md5: Optional[str] = None
    len: Optional[str] = None

class VideoItem(BaseModel):
    media: Optional[CDNMedia] = None
    video_size: Optional[int] = None
    play_length: Optional[int] = None
    video_md5: Optional[str] = None
    thumb_media: Optional[CDNMedia] = None
    thumb_size: Optional[int] = None
    thumb_height: Optional[int] = None
    thumb_width: Optional[int] = None

class MessageItem(BaseModel):
    type: Optional[int] = None
    create_time_ms: Optional[int] = None
    update_time_ms: Optional[int] = None
    is_completed: Optional[bool] = None
    msg_id: Optional[Union[int, str]] = None
    ref_msg: Optional["RefMessage"] = None
    text_item: Optional[TextItem] = None
    image_item: Optional[ImageItem] = None
    voice_item: Optional[VoiceItem] = None
    file_item: Optional[FileItem] = None
    video_item: Optional[VideoItem] = None

class RefMessage(BaseModel):
    message_item: Optional[MessageItem] = None
    title: Optional[str] = None

# Update MessageItem to include RefMessage
MessageItem.model_rebuild()

class WeixinMessage(BaseModel):
    seq: Optional[int] = None
    message_id: Optional[Union[int, str]] = None
    msg_id: Optional[Union[int, str]] = None
    from_user_id: Optional[str] = None
    to_user_id: Optional[str] = None
    client_id: Optional[str] = None
    create_time_ms: Optional[int] = None
    update_time_ms: Optional[int] = None
    delete_time_ms: Optional[int] = None
    session_id: Optional[str] = None
    group_id: Optional[str] = None
    message_type: Optional[int] = None
    message_state: Optional[int] = None
    item_list: Optional[List[MessageItem]] = None
    context_token: Optional[str] = None

class GetUpdatesReq(BaseModel):
    sync_buf: Optional[str] = None
    get_updates_buf: Optional[str] = None

class GetUpdatesResp(BaseModel):
    ret: Optional[int] = None
    errcode: Optional[int] = None
    errmsg: Optional[str] = None
    msgs: Optional[List[WeixinMessage]] = None
    sync_buf: Optional[str] = None
    get_updates_buf: Optional[str] = None
    longpolling_timeout_ms: Optional[int] = None

class SendMessageReq(BaseModel):
    msg: Optional[WeixinMessage] = None

class SendMessageResp(BaseModel):
    pass

class SendTypingReq(BaseModel):
    ilink_user_id: Optional[str] = None
    typing_ticket: Optional[str] = None
    status: Optional[int] = None

class SendTypingResp(BaseModel):
    ret: Optional[int] = None
    errmsg: Optional[str] = None

class GetConfigResp(BaseModel):
    ret: Optional[int] = None
    errmsg: Optional[str] = None
    typing_ticket: Optional[str] = None

class ActiveLogin(BaseModel):
    sessionKey: str
    id: str
    qrcode: str
    qrcodeUrl: str
    startedAt: float
    botToken: Optional[str] = None
    status: Optional[str] = None # "wait" | "scaned" | "confirmed" | "expired"
    error: Optional[str] = None

class QRCodeResponse(BaseModel):
    qrcode: str
    qrcode_img_content: str

class StatusResponse(BaseModel):
    status: str
    bot_token: Optional[str] = None
    ilink_bot_id: Optional[str] = None
    baseurl: Optional[str] = None
    ilink_user_id: Optional[str] = None

class WeixinQrStartResult(BaseModel):
    qrcodeUrl: Optional[str] = None
    message: str
    sessionKey: str

class WeixinQrWaitResult(BaseModel):
    connected: bool
    botToken: Optional[str] = None
    accountId: Optional[str] = None
    baseUrl: Optional[str] = None
    userId: Optional[str] = None
    message: str
