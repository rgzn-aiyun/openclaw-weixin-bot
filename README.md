# OpenClaw Weixin (Python)

[简体中文](./README.zh_CN.md)

This is a Python rewrite of the OpenClaw Weixin plugin. It can run as a standalone bot.

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Login

Scan the QR code with your Weixin account.

```bash
python3 -m openclaw-weixin-bot.main login
```

### 2. Run the Bot

Start the long-polling loop.

```bash
python3 -m openclaw-weixin-bot.main run
```

### 3. List Accounts

```bash
python3 -m openclaw-weixin-bot.main list
```

### 4. Logout

Logout and clear account data.

```bash
python3 -m openclaw-weixin-bot.main logout
```

## Features

- QR Code Login
- Long-polling for messages (`getUpdates`)
- Automatic session restoration and sync_buf management
- Echo bot example (responds to "ping" with "pong")
