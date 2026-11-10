"""大模型服务。

调用优先级（均走 OpenAI 兼容 /chat/completions）：
  1) DeepSeek：配置 MIANZHI_API_KEY 时优先使用（settings.api_key / base_url / model_name）。
  2) 硅基流动：未配 DeepSeek 但配置了 MIANZHI_OPENAI_API_KEY 时，
     复用与 ASR 同源的硅基流动端点调用真实大模型（settings.llm_model）。
  3) 均缺失 / 调用失败时：降级为本地 mock 点评，保证主流程不破。

无论哪条链路，最终都返回统一结构：
  {score, grade, comment, suggestion, dimensions:[{name,score}]}
"""
import os
import re
import json
from typing import Dict, List, Optional

from ..config import settings


def _grade_from_score(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 75:
        return "B"
    if score >= 65:
        return "C"
    return "D"


def _mock_comment(question: str, answer: str, mode: str) -> Dict:
    chars = len(re.sub(r"\s", "", answer))
    fillers = len(re.findall(r"然后|那个|就是说|嗯|其实", answer))
    score = max(40, min(95, 55 + chars // 10 - fillers * 3))
    grade = _grade_from_score(score)
    if grade in ("S", "A"):
        comment = "回答结构清晰，要点完整，与岗位匹配度高。"
    elif grade == "B":
        comment = "整体尚可，但部分要点展开不足，建议补充量化结果。"
    else:
        comment = "回答偏简略，缺少结构化组织，建议用 STAR 法重新梳理。"
    return {
        "score": score,
        "grade": grade,
        "comment": comment,
        "suggestion": "使用 STAR 结构，先给结论再展开，并补充可量化的成果数据。",
        "dimensions": [
            {"name": "内容完整度", "score": min(100, score + 4)},
            {"name": "逻辑结构", "score": min(100, score + 2)},
            {"name": "表达流畅度", "score": max(40, score - 7)},
            {"name": "岗位匹配度", "score": min(100, score + 1)},
            {"name": "抗压表现", "score": max(40, score - 4) if mode == "pressure" else min(100, score)},
        ],
    }


def _openai_chat(
    system_prompt: str,
    user_prompt: str,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
) -> Optional[str]:
    """调用 OpenAI 兼容 /chat/completions，返回文本；任何异常返回 None（由调用方降级）。"""
    try:
        from openai import OpenAI
        import httpx

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(trust_env=False, timeout=30.0),
            max_retries=1,
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception:
        return None


def _resolve_llm() -> Optional[Dict]:
    """解析可用的 LLM 配置；无可用密钥时返回 None（走 mock）。

    优先级：DeepSeek(MIANZHI_API_KEY) > 硅基流动(MIANZHI_OPENAI_API_KEY，与 ASR 同源) > mock。
    """
    if settings.api_key:
        return {
            "model": settings.model_name,
            "api_key": settings.api_key,
            "base_url": settings.base_url,
        }
    sk = os.getenv("MIANZHI_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if sk:
        base = (
            os.getenv("MIANZHI_OPENAI_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        return {"model": settings.llm_model, "api_key": sk, "base_url": base}
    return None


def comment(question: str, answer: str, mode: str = "normal") -> Dict:
    """返回 AI 点评结果（真实大模型或 mock 兜底）。"""
    llm = _resolve_llm()
    if not llm:
        return _mock_comment(question, answer, mode)

    try:
        prompt = (
            "你是一位严格的校招面试考官。请对候选人的回答评分(0-100)并给出点评与优化建议，"
            "以及五个维度(内容完整度/逻辑结构/表达流畅度/岗位匹配度/抗压表现)的分值。\n"
            f"面试题目：{question}\n候选人回答：{answer}\n"
            "请严格只输出一个 JSON 对象，不要包含任何解释文字，格式："
            '{"score": 数字, "grade": "A/B/C/D", "comment": "点评", '
            '"suggestion": "优化建议", "dimensions": [{"name": "维度名", "score": 数字}]}'
        )
        content = _openai_chat(
            "你是严厉的校招面试考官，只输出结构化 JSON 评分结果。",
            prompt,
            llm["model"],
            llm["api_key"],
            llm["base_url"],
            settings.temperature,
            settings.max_tokens,
        )
        if not content:
            return _mock_comment(question, answer, mode)
        # 容错：模型可能夹带 markdown 代码块或多余文字
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        data = json.loads(cleaned)
        data["grade"] = data.get("grade") or _grade_from_score(int(data.get("score", 60)))
        # 维度缺失时按总分推算，保证结构完整
        if not data.get("dimensions"):
            s = int(data.get("score", 60))
            data["dimensions"] = [
                {"name": "内容完整度", "score": min(100, s + 4)},
                {"name": "逻辑结构", "score": min(100, s + 2)},
                {"name": "表达流畅度", "score": max(40, s - 7)},
                {"name": "岗位匹配度", "score": min(100, s + 1)},
                {"name": "抗压表现", "score": max(40, s - 4) if mode == "pressure" else min(100, s)},
            ]
        return data
    except Exception:
        return _mock_comment(question, answer, mode)


def answer_question(question: str) -> str:
    """AI 答疑（面试疑问辅导）。"""
    llm = _resolve_llm()
    if not llm:
        return (
            f"关于「{question}」：建议使用 STAR 结构（情境-任务-行动-结果）组织回答，"
            "先抛结论再展开细节，并保持与岗位 JD 的强关联。可在模拟面试中针对性练习。"
        )
    content = _openai_chat(
        "你是面试教练，回答简洁专业，使用中文。",
        f"作为面试教练，简洁回答下面的问题：{question}",
        llm["model"],
        llm["api_key"],
        llm["base_url"],
        settings.temperature,
        800,
    )
    return content or f"关于「{question}」：建议使用 STAR 结构组织回答，先给结论再展开细节。"
