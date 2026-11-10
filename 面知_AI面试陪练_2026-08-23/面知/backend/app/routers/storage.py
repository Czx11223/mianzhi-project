"""本地文件存储（替代云服务的 Storage 模块）。

提供语音作答等文件的上传与访问。文件落在可写目录（默认 /tmp/mianzhi_storage，
可通过 MIANZHI_STORAGE_DIR 覆盖）。注意：无服务器实例的本地磁盘在回收后会清空，
属于「只读演示版」的本地等价实现；若需长期留存应接入对象存储。
"""
import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Response

router = APIRouter(prefix="/api/storage", tags=["storage"])

STORAGE_DIR = os.getenv("MIANZHI_STORAGE_DIR") or "/tmp/mianzhi_storage"
_ALLOWED = {".webm", ".ogg", ".mp3", ".wav", ".m4a", ".mp4", ".aac", ".flac"}
_MAX_BYTES = 15 * 1024 * 1024  # 15MB


def _safe_ext(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in _ALLOWED else ".webm"


@router.post("/audio")
async def upload_audio(audio: UploadFile = File(...)):
    data = await audio.read()
    if not data:
        raise HTTPException(400, "空文件")
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, "文件过大（上限 15MB）")
    os.makedirs(STORAGE_DIR, exist_ok=True)
    fid = uuid.uuid4().hex
    ext = _safe_ext(audio.filename)
    path = os.path.join(STORAGE_DIR, f"{fid}{ext}")
    with open(path, "wb") as f:
        f.write(data)
    return {"id": fid + ext, "url": f"/api/storage/audio/{fid}{ext}", "size": len(data)}


@router.get("/audio/{file_id}")
def get_audio(file_id: str):
    # 防目录穿越：仅允许文件名本身，禁止路径分隔符
    if "/" in file_id or "\\" in file_id or ".." in file_id:
        raise HTTPException(400, "非法文件名")
    path = os.path.join(STORAGE_DIR, file_id)
    if not os.path.isfile(path):
        raise HTTPException(404, "文件不存在")
    with open(path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="audio/webm")
