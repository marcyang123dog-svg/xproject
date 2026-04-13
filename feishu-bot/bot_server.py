"""
方案A：飞书机器人 Webhook Server
- 接收飞书消息 → 调用 Claude（带工具定义）→ 执行飞书 API → 回复用户
"""
import os
import json
import hashlib
import hmac
import time
from flask import Flask, request, jsonify
import anthropic
import feishu_client as fs

app = Flask(__name__)

claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ─── Claude 工具定义 ──────────────────────────────────────

TOOLS = [
    {
        "name": "send_feishu_message",
        "description": "发送飞书消息给指定用户或群组",
        "input_schema": {
            "type": "object",
            "properties": {
                "receive_id": {"type": "string", "description": "接收者 open_id 或 chat_id"},
                "text": {"type": "string", "description": "消息内容"},
                "receive_id_type": {
                    "type": "string",
                    "enum": ["open_id", "chat_id", "email", "user_id"],
                    "description": "ID 类型，默认 open_id",
                },
            },
            "required": ["receive_id", "text"],
        },
    },
    {
        "name": "create_feishu_document",
        "description": "创建一个新的飞书文档，返回文档链接",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "文档标题"},
                "folder_token": {"type": "string", "description": "存放的文件夹 token（可选）"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "append_to_document",
        "description": "向已有飞书文档末尾追加文字内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "文档 ID"},
                "text": {"type": "string", "description": "要追加的文字"},
            },
            "required": ["document_id", "text"],
        },
    },
    {
        "name": "get_document_info",
        "description": "获取飞书文档的信息（标题、修改时间等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "文档 ID"},
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "list_drive_files",
        "description": "列出飞书云空间中的文件",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_token": {"type": "string", "description": "文件夹 token（可选，不填则列出根目录）"},
            },
        },
    },
]


def run_tool(name: str, inputs: dict) -> str:
    """执行工具调用，返回结果字符串"""
    try:
        if name == "send_feishu_message":
            result = fs.send_text_message(
                inputs["receive_id"],
                inputs["text"],
                inputs.get("receive_id_type", "open_id"),
            )
            return f"消息发送成功: {json.dumps(result, ensure_ascii=False)}"

        elif name == "create_feishu_document":
            result = fs.create_document(
                inputs["title"],
                inputs.get("folder_token"),
            )
            return f"文档创建成功！文档 ID: {result['document_id']}，链接: {result['url']}"

        elif name == "append_to_document":
            result = fs.append_text_to_document(inputs["document_id"], inputs["text"])
            return f"内容追加成功: {json.dumps(result, ensure_ascii=False)}"

        elif name == "get_document_info":
            result = fs.get_document_info(inputs["document_id"])
            return json.dumps(result, ensure_ascii=False)

        elif name == "list_drive_files":
            result = fs.list_drive_files(inputs.get("folder_token"))
            return json.dumps(result, ensure_ascii=False)

        else:
            return f"未知工具: {name}"
    except Exception as e:
        return f"工具执行失败: {e}"


def chat_with_claude(user_message: str, sender_open_id: str) -> str:
    """
    调用 Claude，支持多轮工具调用（agentic loop）
    """
    messages = [{"role": "user", "content": user_message}]
    system_prompt = (
        f"你是飞书智能助手。当前用户的 open_id 是 {sender_open_id}。"
        "你可以使用提供的工具来操作飞书：发送消息、创建文档、编辑文档、列出文件等。"
        "请用中文回复，操作完成后告知用户结果。"
    )

    while True:
        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # 收集 Claude 的回复内容
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # 提取最终文本回复
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "操作完成。"

        if response.stop_reason == "tool_use":
            # 执行所有工具调用
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "处理完成。"


# ─── Webhook 验证（防重放） ───────────────────────────────

def verify_feishu_signature(timestamp: str, nonce: str, body: bytes,
                            secret: str) -> bool:
    verify_str = timestamp + nonce + secret + body.decode("utf-8")
    signature = hmac.new(verify_str.encode("utf-8"),
                         digestmod=hashlib.sha256).hexdigest()
    return True  # 简化处理，生产环境需对比 X-Lark-Signature header


_processed_ids: set = set()  # 防止重复处理


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # 1. URL 验证握手
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # 2. 解析事件
    header = data.get("header", {})
    event_type = header.get("event_type", "")
    event_id = header.get("event_id", "")

    # 防重复处理
    if event_id in _processed_ids:
        return jsonify({"code": 0})
    _processed_ids.add(event_id)
    if len(_processed_ids) > 1000:
        _processed_ids.clear()

    if event_type == "im.message.receive_v1":
        event = data.get("event", {})
        msg = event.get("message", {})
        sender = event.get("sender", {})

        # 只处理文本消息，忽略机器人自己发的
        if msg.get("message_type") != "text":
            return jsonify({"code": 0})
        if sender.get("sender_type") == "app":
            return jsonify({"code": 0})

        content = json.loads(msg.get("content", "{}"))
        user_text = content.get("text", "").strip()
        message_id = msg.get("message_id", "")
        open_id = sender.get("sender_id", {}).get("open_id", "")

        if not user_text:
            return jsonify({"code": 0})

        # 调用 Claude 处理
        reply = chat_with_claude(user_text, open_id)

        # 回复消息
        fs.reply_message(message_id, reply)

    return jsonify({"code": 0})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
