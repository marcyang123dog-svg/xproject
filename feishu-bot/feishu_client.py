"""
飞书 API 客户端 - 封装所有飞书 Open API 调用
"""
import os
import json
import time
import requests
from typing import Optional

FEISHU_BASE = "https://open.feishu.cn/open-apis"

_token_cache = {"token": None, "expire_at": 0}


def get_tenant_access_token() -> str:
    """获取 tenant_access_token，带缓存"""
    if time.time() < _token_cache["expire_at"] - 60:
        return _token_cache["token"]

    resp = requests.post(
        f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
        json={
            "app_id": os.environ["FEISHU_APP_ID"],
            "app_secret": os.environ["FEISHU_APP_SECRET"],
        },
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["tenant_access_token"]
    _token_cache["expire_at"] = time.time() + data["expire"]
    return _token_cache["token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {get_tenant_access_token()}"}


# ─── 消息 ────────────────────────────────────────────────

def send_text_message(receive_id: str, text: str,
                      receive_id_type: str = "open_id") -> dict:
    """发送文本消息"""
    resp = requests.post(
        f"{FEISHU_BASE}/im/v1/messages",
        headers=_headers(),
        params={"receive_id_type": receive_id_type},
        json={
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
    )
    resp.raise_for_status()
    return resp.json()


def send_rich_text_message(receive_id: str, title: str, content: list,
                           receive_id_type: str = "open_id") -> dict:
    """发送富文本消息"""
    resp = requests.post(
        f"{FEISHU_BASE}/im/v1/messages",
        headers=_headers(),
        params={"receive_id_type": receive_id_type},
        json={
            "receive_id": receive_id,
            "msg_type": "post",
            "content": json.dumps({
                "zh_cn": {"title": title, "content": content}
            }),
        },
    )
    resp.raise_for_status()
    return resp.json()


def reply_message(message_id: str, text: str) -> dict:
    """回复某条消息"""
    resp = requests.post(
        f"{FEISHU_BASE}/im/v1/messages/{message_id}/reply",
        headers=_headers(),
        json={"msg_type": "text", "content": json.dumps({"text": text})},
    )
    resp.raise_for_status()
    return resp.json()


def get_chat_history(chat_id: str, page_size: int = 20) -> dict:
    """获取群聊历史消息"""
    resp = requests.get(
        f"{FEISHU_BASE}/im/v1/messages",
        headers=_headers(),
        params={"container_id_type": "chat", "container_id": chat_id,
                "page_size": page_size},
    )
    resp.raise_for_status()
    return resp.json()


# ─── 飞书文档 (Docx) ──────────────────────────────────────

def create_document(title: str, folder_token: Optional[str] = None) -> dict:
    """创建飞书文档，返回 {document_id, url}"""
    payload = {"title": title}
    if folder_token:
        payload["folder_token"] = folder_token

    resp = requests.post(
        f"{FEISHU_BASE}/docx/v1/documents",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()
    doc_id = data["data"]["document"]["document_id"]
    return {
        "document_id": doc_id,
        "url": f"https://feishu.cn/docx/{doc_id}",
        "raw": data,
    }


def get_document_info(document_id: str) -> dict:
    """获取文档信息"""
    resp = requests.get(
        f"{FEISHU_BASE}/docx/v1/documents/{document_id}",
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json()


def append_text_to_document(document_id: str, text: str) -> dict:
    """向文档末尾追加段落文本"""
    # 先获取文档 root block id
    doc_resp = requests.get(
        f"{FEISHU_BASE}/docx/v1/documents/{document_id}",
        headers=_headers(),
    )
    doc_resp.raise_for_status()
    root_block_id = doc_resp.json()["data"]["document"]["body"]["block_id"]

    # 追加段落
    resp = requests.post(
        f"{FEISHU_BASE}/docx/v1/documents/{document_id}/blocks/{root_block_id}/children",
        headers=_headers(),
        json={
            "children": [
                {
                    "block_type": 2,  # paragraph
                    "paragraph": {
                        "elements": [
                            {"type": "text_run", "text_run": {"content": text}}
                        ]
                    },
                }
            ],
            "index": -1,  # 末尾
        },
    )
    resp.raise_for_status()
    return resp.json()


# ─── 云文档（旧版 sheet/wiki）─────────────────────────────

def list_drive_files(folder_token: Optional[str] = None) -> dict:
    """列出云空间文件"""
    params = {}
    if folder_token:
        params["folder_token"] = folder_token
    resp = requests.get(
        f"{FEISHU_BASE}/drive/v1/files",
        headers=_headers(),
        params=params,
    )
    resp.raise_for_status()
    return resp.json()
