from fastapi import APIRouter, UploadFile, File
from ..services.asr import transcribe

router = APIRouter(prefix="/api", tags=["asr"])


@router.post("/asr")
async def speech_to_text(audio: UploadFile = File(...)):
    data = await audio.read()
    fmt = audio.filename.split(".")[-1] if audio.filename else "webm"
    text, is_mock = transcribe(data, fmt=fmt)
    return {"text": text, "engine": "mock" if is_mock else "whisper"}
