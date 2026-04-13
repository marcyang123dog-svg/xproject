"""
方案B：飞书 MCP Server
让 Claude Code CLI 直接拥有飞书操作能力。

使用方式：
  在 ~/.claude/claude.json 或项目 .claude/settings.json 中添加：
  {
    "mcpServers": {
      "feishu": {
        "command": "python",
        "args": ["/path/to/feishu_mcp_server.py"],
        "env": {
          "FEISHU_APP_ID": "...",
          "FEISHU_APP_SECRET": "..."
        }
      }
    }
  }

然后在 Claude Code 中就可以直接说：
  "帮我创建一个飞书文档，标题是《项目周报》"
  "发消息给 ou_xxx 说明天下午开会"
"""
import sys
import json
import asyncio
import feishu_client as fs

# MCP 协议：通过 stdin/stdout 通信（JSON-RPC 2.0）

def send_response(resp: dict):
    line = json.dumps(resp, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def send_error(req_id, code: int, message: str):
    send_response({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    })


TOOLS = [
    {
        "name": "feishu_send_message",
        "description": "发送飞书消息给指定用户（open_id）或群组（chat_id）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "receive_id": {
                    "type": "string",
                    "description": "接收者的 open_id 或 chat_id",
                },
                "text": {
                    "type": "string",
                    "description": "消息正文（纯文本）",
                },
                "receive_id_type": {
                    "type": "string",
                    "enum": ["open_id", "chat_id", "email", "user_id"],
                    "description": "ID 类型，默认 open_id",
                    "default": "open_id",
                },
            },
            "required": ["receive_id", "text"],
        },
    },
    {
        "name": "feishu_create_document",
        "description": "在飞书云空间创建一个新文档，返回文档 ID 和访问链接",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "文档标题"},
                "folder_token": {
                    "type": "string",
                    "description": "目标文件夹的 token（不填则放到根目录）",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "feishu_append_to_document",
        "description": "向已有飞书文档末尾追加段落文字",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "目标文档 ID"},
                "text": {"type": "string", "description": "要追加的文字内容"},
            },
            "required": ["document_id", "text"],
        },
    },
    {
        "name": "feishu_get_document_info",
        "description": "查询飞书文档的基本信息（标题、创建者、修改时间等）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "文档 ID"},
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "feishu_list_drive_files",
        "description": "列出飞书云空间（或指定文件夹）中的文件和文档",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder_token": {
                    "type": "string",
                    "description": "文件夹 token（不填则列出根目录）",
                },
            },
        },
    },
    {
        "name": "feishu_reply_message",
        "description": "回复飞书中的某条消息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "被回复的消息 ID"},
                "text": {"type": "string", "description": "回复内容"},
            },
            "required": ["message_id", "text"],
        },
    },
]


def handle_tool_call(tool_name: str, arguments: dict) -> str:
    if tool_name == "feishu_send_message":
        result = fs.send_text_message(
            arguments["receive_id"],
            arguments["text"],
            arguments.get("receive_id_type", "open_id"),
        )
        return f"消息发送成功。消息 ID: {result.get('data', {}).get('message_id', 'N/A')}"

    elif tool_name == "feishu_create_document":
        result = fs.create_document(
            arguments["title"],
            arguments.get("folder_token"),
        )
        return (
            f"文档创建成功！\n"
            f"文档 ID: {result['document_id']}\n"
            f"访问链接: {result['url']}"
        )

    elif tool_name == "feishu_append_to_document":
        fs.append_text_to_document(arguments["document_id"], arguments["text"])
        return "内容已成功追加到文档末尾。"

    elif tool_name == "feishu_get_document_info":
        result = fs.get_document_info(arguments["document_id"])
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif tool_name == "feishu_list_drive_files":
        result = fs.list_drive_files(arguments.get("folder_token"))
        files = result.get("data", {}).get("files", [])
        if not files:
            return "该目录下没有文件。"
        lines = [f"共 {len(files)} 个文件:"]
        for f in files:
            lines.append(f"  - [{f.get('type','?')}] {f.get('name','?')}  (token: {f.get('token','?')})")
        return "\n".join(lines)

    elif tool_name == "feishu_reply_message":
        result = fs.reply_message(arguments["message_id"], arguments["text"])
        return f"回复成功。消息 ID: {result.get('data', {}).get('message_id', 'N/A')}"

    else:
        raise ValueError(f"未知工具: {tool_name}")


def main():
    """MCP 服务主循环（JSON-RPC over stdio）"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method", "")

        # ── 初始化 ──────────────────────────────────────────
        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "feishu-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            })

        # ── 列出工具 ─────────────────────────────────────────
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS},
            })

        # ── 调用工具 ─────────────────────────────────────────
        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                output = handle_tool_call(tool_name, arguments)
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": output}],
                        "isError": False,
                    },
                })
            except Exception as e:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"错误: {e}"}],
                        "isError": True,
                    },
                })

        # ── ping ─────────────────────────────────────────────
        elif method == "ping":
            send_response({"jsonrpc": "2.0", "id": req_id, "result": {}})

        else:
            send_error(req_id, -32601, f"Method not found: {method}")


if __name__ == "__main__":
    main()
