"""Web 版设置管理 —— 基于文件系统的简单存储。"""
import os
import json
import uuid

# 数据目录：存放各会话的状态文件
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def get_data_dir():
    """返回数据目录路径，确保目录存在。"""
    os.makedirs(_DATA_DIR, exist_ok=True)
    return _DATA_DIR


def get_session_file(session_id):
    """返回指定会话的状态文件路径。"""
    return os.path.join(get_data_dir(), f"session_{session_id}.json")


def new_session_id():
    """生成新的会话 ID。"""
    return uuid.uuid4().hex[:16]


def read_session(session_id):
    """读取会话状态，文件不存在时返回空字典。"""
    path = get_session_file(session_id)
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def write_session(session_id, data):
    """写入会话状态。"""
    path = get_session_file(session_id)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def delete_session(session_id):
    """删除会话文件。"""
    path = get_session_file(session_id)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
