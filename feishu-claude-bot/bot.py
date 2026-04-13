#!/usr/bin/env python3
"""
飞书 Claude Bot
用户在飞书里 @ 机器人 → Claude 理解意图 → lark-cli 执行操作 → 回复结果
"""

import json
import subprocess
import re
import threading
import os
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

# ── 配置 ─────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FEISHU_VERIFICATION_TOKEN = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
PORT = int(os.environ.get("PORT", 8080))

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是飞书上的 Claude AI 助手，可以通过 lark-cli 帮用户操作飞书。

当用户发来请求时，你的处理流程：
1. 理解用户的需求
2. 如果需要操作飞书，输出 <cmd>lark-cli 命令</cmd> 来执行
3. 收到命令结果后，用简洁中文告诉用户结果

## 常用 lark-cli 命令

### 文档
- 创建文档：lark-cli docs +create --title "标题" --markdown "内容"
- 搜索文档：lark-cli docs +search --query "关键词"
- 获取文档：lark-cli docs +fetch --doc-url "URL"

### 日历
- 查看今日日程：lark-cli calendar +agenda
- 创建日历事件：lark-cli calendar event create --summary "标题" --start "2024-01-01T10:00:00+08:00" --end "2024-01-01T11:00:00+08:00"

### 消息
- 发消息给某人：lark-cli im +messages-send --user-id "open_id" --text "内容"
- 发消息到群：lark-cli im +messages-send --chat-id "oc_xxx" --text "内容"

### 任务
- 创建任务：lark-cli task +create --title "任务名" --due "2024-01-01"
- 查看任务：lark-cli task +list

### 云文档搜索
- 搜索文件：lark-cli drive +search --query "关键词"

## 注意事项
- 每次只输出一条 <cmd>...</cmd>，等结果后再决定下一步
- 如果命令失败，分析错误并尝试修正
- 回复要简洁，关键信息用 markdown 格式
- 如果用户只是聊天（不需要操作飞书），直接回复即可
"""

# ── lark-cli 执行 ─────────────────────────────────────────────────────────────
def run_lark_cli(cmd: str) -> str:
    """执行 lark-cli 命令，返回输出"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = (result.stdout or result.stderr or "").strip()
        return output if output else "(命令执行成功，无输出)"
    except subprocess.TimeoutExpired:
        return "错误：命令执行超时（30s）"
    except Exception as e:
        return f"错误：{e}"


# ── Claude 对话处理 ───────────────────────────────────────────────────────────
def process_with_claude(user_message: str, message_id: str):
    """调用 Claude，执行 lark-cli 命令，返回最终回复文本"""
    messages = [{"role": "user", "content": user_message}]

    for _ in range(5):  # 最多 5 轮工具调用
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        reply = response.content[0].text

        # 检查是否有 lark-cli 命令
        cmds = re.findall(r"<cmd>(.*?)</cmd>", reply, re.DOTALL)
        if not cmds:
            return reply  # 无命令，直接返回最终回复

        # 执行命令并把结果喂回 Claude
        messages.append({"role": "assistant", "content": reply})
        results = []
        for cmd in cmds:
            cmd = cmd.strip()
            print(f"[执行] {cmd}")
            result = run_lark_cli(cmd)
            print(f"[结果] {result[:200]}")
            results.append(f"命令: {cmd}\n结果:\n{result}")

        messages.append({
            "role": "user",
            "content": "命令执行结果：\n\n" + "\n\n---\n\n".join(results)
                       + "\n\n请根据以上结果给用户一个简洁友好的回复（不要输出 <cmd> 标签）。"
        })

    return "抱歉，处理超时，请重试。"


def handle_message(text: str, message_id: str):
    """在后台线程中处理消息并回复"""
    try:
        reply = process_with_claude(text, message_id)
    except Exception as e:
        reply = f"出错了：{e}"

    # 通过 lark-cli 回复
    safe = reply.replace("'", "'\\''")  # 转义单引号
    cmd = f"lark-cli im +messages-reply --message-id '{message_id}' --markdown '{safe}' --as user"
    result = run_lark_cli(cmd)
    print(f"[回复] {result[:100]}")


# ── Webhook ───────────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # 尝试多种方式解析请求体
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}

    print(f"[Webhook] data={json.dumps(data)[:200]}")

    # 飞书 URL 验证（两种格式都支持）
    challenge = data.get("challenge")
    if data.get("type") == "url_verification" or challenge:
        return jsonify({"challenge": challenge or ""})

    # 验证 Token（可选，建议开启）
    if FEISHU_VERIFICATION_TOKEN:
        token = data.get("header", {}).get("token") or data.get("token", "")
        if token != FEISHU_VERIFICATION_TOKEN:
            return jsonify({"code": 403, "msg": "invalid token"}), 403

    # 处理消息事件
    event_type = data.get("header", {}).get("event_type", "")
    if event_type != "im.message.receive_v1":
        return jsonify({"code": 0})

    event = data.get("event", {})
    message = event.get("message", {})

    # 只处理文本消息
    if message.get("message_type") != "text":
        return jsonify({"code": 0})

    # 解析消息内容
    try:
        content = json.loads(message.get("content", "{}"))
        text = content.get("text", "").strip()
    except Exception:
        return jsonify({"code": 0})

    # 去掉 @机器人 前缀
    text = re.sub(r"@\S+\s*", "", text).strip()
    if not text:
        return jsonify({"code": 0})

    message_id = message.get("message_id", "")
    if not message_id:
        return jsonify({"code": 0})

    print(f"[收到] {text[:80]}")

    # 异步处理，避免 webhook 超时
    t = threading.Thread(target=handle_message, args=(text, message_id), daemon=True)
    t.start()

    return jsonify({"code": 0})


# ── 启动 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not ANTHROPIC_API_KEY:
        print("❌ 请设置环境变量 ANTHROPIC_API_KEY")
        exit(1)
    print(f"🤖 飞书 Claude Bot 启动，监听端口 {PORT}")
    print(f"   Webhook: http://localhost:{PORT}/webhook")
    app.run(host="0.0.0.0", port=PORT, debug=False)
