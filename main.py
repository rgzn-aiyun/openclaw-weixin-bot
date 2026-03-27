import argparse
import asyncio
import sys
from .auth import start_weixin_login_with_qr, wait_for_weixin_login
from .config import (
    register_weixin_account_id, 
    save_weixin_account, 
    list_indexed_weixin_account_ids,
    clear_weixin_account,
    unregister_weixin_account_id
)
from .monitor import monitor_weixin
from .messaging import send_message
from .models import WeixinMessage, MessageItemType
from .utils import logger

async def echo_handler(msg: WeixinMessage, client, bot_id: str):
    from_user = msg.from_user_id
    logger.info(f"Received message from {from_user}")
    
    if msg.item_list:
        for item in msg.item_list:
            if item.type == MessageItemType.TEXT and item.text_item:
                text = item.text_item.text
                logger.info(f"Text: {text}")
                if text == "ping":
                    logger.info(f"Sending pong reply to {from_user} with context_token={msg.context_token[:20]}...")
                    await send_message(client, bot_id, from_user, "pong", msg.context_token)
                    logger.info(f"Reply sent to {from_user}")

async def cmd_login(args):
    res = await start_weixin_login_with_qr(
        api_base_url=args.base_url,
        account_id=args.account_id,
        force=args.force
    )
    if not res.qrcodeUrl:
        logger.error(f"Login failed: {res.message}")
        return

    # QR code is printed by wait_for_weixin_login if verbose=True
    # But wait_for_weixin_login also refreshes it.
    
    wait_res = await wait_for_weixin_login(
        session_key=res.sessionKey,
        api_base_url=args.base_url,
        verbose=True
    )
    
    if wait_res.connected:
        save_weixin_account(
            account_id=wait_res.accountId,
            token=wait_res.botToken,
            base_url=wait_res.baseUrl,
            user_id=wait_res.userId
        )
        register_weixin_account_id(wait_res.accountId)
        logger.info(f"Login success! Account ID: {wait_res.accountId}")
    else:
        logger.error(f"Login failed: {wait_res.message}")

async def cmd_run(args):
    accounts = list_indexed_weixin_account_ids()
    if not accounts:
        logger.error("No accounts found. Please login first.")
        return
    
    logger.info(f"Starting bot for accounts: {accounts}")
    
    tasks = []
    for acc in accounts:
        tasks.append(monitor_weixin(acc, echo_handler))
    
    await asyncio.gather(*tasks)

async def cmd_list(args):
    accounts = list_indexed_weixin_account_ids()
    if not accounts:
        print("没有找到已注册的账号。")
        return
    print("已注册账号：")
    for acc in accounts:
        print(f"- {acc}")

async def cmd_logout(args):
    accounts = list_indexed_weixin_account_ids()
    if not accounts:
        print("没有找到已注册的账号。")
        return

    target_id = args.account_id
    if not target_id:
        print("当前已登录账号：")
        for i, acc in enumerate(accounts):
            print(f"{i + 1}. {acc}")
        
        try:
            choice = input("\n请输入要退出的账号序号或 ID (按回车取消): ").strip()
            if not choice:
                return
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(accounts):
                    target_id = accounts[idx]
                else:
                    print("错误: 无效的序号。")
                    return
            else:
                if choice in accounts:
                    target_id = choice
                else:
                    print(f"错误: 未找到账号 ID '{choice}'。")
                    return
        except EOFError:
            return

    clear_weixin_account(target_id)
    unregister_weixin_account_id(target_id)
    print(f"✅ 已成功退出并清除账号数据: {target_id}")

def main():
    parser = argparse.ArgumentParser(description="OpenClaw Weixin Bot (Python)")
    subparsers = parser.add_subparsers(dest="command")
    
    login_parser = subparsers.add_parser("login", help="通过二维码登录")
    login_parser.add_argument("--base-url", default="https://ilinkai.weixin.qq.com", help="API 基础 URL")
    login_parser.add_argument("--account-id", help="可选的账号 ID")
    login_parser.add_argument("--force", action="store_true", help="强制重新登录")
    
    subparsers.add_parser("run", help="运行机器人")
    
    subparsers.add_parser("list", help="列出已登录账号")
    
    logout_parser = subparsers.add_parser("logout", help="退出账号并清除数据")
    logout_parser.add_argument("account_id", nargs="?", help="要退出的账号 ID (可选)")
    
    args = parser.parse_args()
    
    if args.command == "login":
        asyncio.run(cmd_login(args))
    elif args.command == "run":
        asyncio.run(cmd_run(args))
    elif args.command == "list":
        asyncio.run(cmd_list(args))
    elif args.command == "logout":
        asyncio.run(cmd_logout(args))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
