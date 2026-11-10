"""语音识别服务。

优先调用 OpenAI Whisper (whisper-1) 进行真实语音转文字；
当未配置 API Key 或调用失败时，自动降级为模拟转写，保证语音答题链路始终可演示。

环境变量（读取顺序）：
  MIANZHI_OPENAI_API_KEY / OPENAI_API_KEY       —— 必填，否则降级模拟
  MIANZHI_OPENAI_BASE_URL  / OPENAI_BASE_URL    —— 可选，兼容 OpenAI 格式的中转/私有部署
"""
import logging
import os
import tempfile

logger = logging.getLogger("asr")

MOCK_TEXT = "我觉得这个岗位挺好的，然后我学过相关技术，然后做过类似项目，就是说比较有经验。"

# 浏览器 MediaRecorder 常见输出格式 -> 文件后缀（OpenAI 据此推断音频编码）
_SUFFIX_MAP = {
    "webm": ".webm",
    "ogg": ".ogg",
    "mp4": ".mp4",
    "m4a": ".m4a",
    "mp3": ".mp3",
    "wav": ".wav",
    "aac": ".aac",
    "flac": ".flac",
}


def _suffix(fmt: str) -> str:
    fmt = (fmt or "").lower().strip().lstrip(".")
    return _SUFFIX_MAP.get(fmt, ".webm")


def transcribe(audio_bytes: bytes, fmt: str = "webm") -> tuple[str, bool]:
    """语音转文字。

    返回 (转写文本, 是否模拟结果)。
    - 配置了 OpenAI Key 且调用成功 -> (真实文本, False)
    - 未配置 Key / 网络异常 / 返回空 -> (模拟文本, True)
    """
    api_key = os.getenv("MIANZHI_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.info("ASR: 未配置 OPENAI_API_KEY / MIANZHI_OPENAI_API_KEY，使用模拟转写")
        return MOCK_TEXT, True

    tmp_path = None
    try:
        import httpx
        from openai import OpenAI

        base_url = os.getenv("MIANZHI_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL") or None
        # 显式设置超时与重试，避免网络异常时请求长时间挂起；
        # trust_env=False 直连（国内中转/硅基流动可直连，TUN 模式 VPN 也不受影响）
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(trust_env=False, timeout=30.0),
            max_retries=1,
        )

        suffix = _suffix(fmt)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        with open(tmp_path, "rb") as af:
            # 模型可配置：默认 OpenAI whisper-1；国内 OpenAI 兼容服务可设 MIANZHI_ASR_MODEL
            model = os.getenv("MIANZHI_ASR_MODEL") or "whisper-1"
            resp = client.audio.transcriptions.create(model=model, file=af)
        text = (resp.text or "").strip()
        if not text:
            logger.warning("ASR: Whisper 返回空文本，降级为模拟转写")
            return MOCK_TEXT, True
        return text, False
    except Exception as e:
        logger.warning("ASR: Whisper 调用失败，降级为模拟转写：%s", e)
        return MOCK_TEXT, True
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
