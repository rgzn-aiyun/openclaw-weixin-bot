# OpenClaw Weixin (Python)

这是 OpenClaw Weixin 插件的 Python 重写版本，可以作为独立的机器人运行。

## 环境要求

- Python 3.8+
- 依赖项已列在 `requirements.txt` 中

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

设置 `PYTHONPATH` 以包含当前目录，使 Python 能够找到包：

```bash
export PYTHONPATH=$PYTHONPATH:.
```

### 1. 登录

使用微信扫描终端中生成的二维码。

```bash
python3 -m openclaw-weixin-bot.main login
```

### 2. 运行机器人

启动长轮询循环。

```bash
python3 -m openclaw-weixin-bot.main run
```

### 3. 列出账号

```bash
python3 -m openclaw-weixin-bot.main list
```

### 4. 退出登录

退出账号并清除本地数据。

```bash
python3 -m openclaw-weixin-bot.main logout
```

## 功能特性

- 二维码登录
- 消息长轮询 (`getUpdates`)
- 自动会话恢复与 sync_buf 管理
- Echo 机器人示例 (对 "ping" 回复 "pong")

