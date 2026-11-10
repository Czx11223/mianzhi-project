import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from .models import Question, Job, SiteContent
from .services.data import SEED_QUESTIONS, JOBS, question_row

SITE_KEY = "site"

def _content_digest(rows) -> str:
    """题库内容哈希：作为题库版本号。"""
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


# 题库版本 = 题库内容哈希：任何题目改动都会让版本变化，启动时自动整库替换，
# 免去手工维护版本号（v2 = 岗位族 + 岗位名绑定的强匹配题库）。
QUESTION_SEED_VERSION = _content_digest(SEED_QUESTIONS)
JOBS_META_VERSION = "2026-11-08.v2"
_VERSION_KEY = "seed_version"


def _get_versions(db: Session) -> dict:
    row = db.query(SiteContent).filter(SiteContent.key == _VERSION_KEY).first()
    if not row or not row.value:
        return {}
    try:
        data = json.loads(row.value)
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def _set_version(db: Session, kind: str, version: str, extra: dict | None = None) -> None:
    data = _get_versions(db)
    data[kind] = {"version": version, **(extra or {})}
    payload = json.dumps(data, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = db.query(SiteContent).filter(SiteContent.key == _VERSION_KEY).first()
    if row:
        row.value = payload
        row.updated_at = now
    else:
        db.add(SiteContent(key=_VERSION_KEY, value=payload, updated_at=now))
    db.commit()

# 站点文案默认值（后台「站点文案」模块的初始内容；编辑后写入 site_content 表）
DEFAULT_SITE_CONTENT = {
    "heroTitle": "模拟面试",
    "heroSubtitle": "选择岗位与面试模式，开启全真 AI 模拟面试，实时点评帮你快速提升。",
    "helpTitle": "帮助中心",
    "helpSubtitle": "面知 使用手册：从第一次模拟面试到能力持续提升的完整指引。",
    "faqs": [
        {"q": "面知 适合哪些人使用？", "a": "主要面向高校应届生，尤其是正在准备校招面试的同学。覆盖互联网、国企、外企、文职、制造业等多行业岗位题库。"},
        {"q": "语音答题需要什么环境？", "a": "语音答题依赖浏览器麦克风权限与语音识别能力。若环境不支持，可随时切换为文字答题，点评流程完全一致。"},
        {"q": "AI 点评的评分标准是什么？", "a": "从内容完整度、逻辑结构、表达流畅度、岗位匹配度、抗压表现五个维度综合评分，并给出 S/A/B/C/D 等级与结构化优化建议。"},
        {"q": "我的面试数据安全吗？", "a": "演示模式下数据保存在本地浏览器。接入后端后，面试记录与答题内容仅用于生成你的个人报告，可在设置中管理模型与数据。"},
        {"q": "如何导出面试报告？", "a": "在面试报告页点击「导出 PDF」，系统将生成包含总分、维度分析、逐题点评与优化建议的 PDF 报告，便于复盘与分享。"},
    ],
}


def seed_questions(db: Session):
    """题库灌入（版本化整库替换）。

    - 版本一致：仅补齐缺失题目（后台删除的题不会被复活）；
    - 版本变化（题库升级）：清空 questions 表后整库灌入新题库，
      确保与岗位强绑定的 v2 题库不会混入旧题；历史作答记录保存在 answers 表中不受影响。
    """
    installed = (_get_versions(db).get("questions") or {}).get("version", "")
    if installed == QUESTION_SEED_VERSION:
        exist = {q.id for q in db.query(Question).all()}
        added = 0
        for q in SEED_QUESTIONS:
            if q["id"] not in exist:
                db.add(Question(**question_row(q)))
                added += 1
        if added:
            db.commit()
        return

    db.query(Question).delete()
    for q in SEED_QUESTIONS:
        db.add(Question(**question_row(q)))
    db.commit()
    _set_version(db, "questions", QUESTION_SEED_VERSION, {"count": len(SEED_QUESTIONS)})


def seed_jobs(db: Session):
    """岗位灌入：新岗位按 id 补齐；题库升级时同步「题型/题量/时长/模式」等与抽题相关的元信息。

    说明：name / company 不覆盖，避免冲掉后台的改名；元信息同步保证岗位声明的题型
    与题库实际题型一致（否则抽题配额会落空）。
    """
    exist = {j.id: j for j in db.query(Job).all()}
    added = updated = 0
    for j in JOBS:
        types = json.dumps(j.get("question_types", []), ensure_ascii=False)
        if j["id"] not in exist:
            db.add(Job(
                id=j["id"],
                name=j["name"],
                company=j.get("company", ""),
                industry=j.get("industry", "互联网"),
                duration=j.get("duration", 20),
                question_types=types,
                answer_mode=j.get("answer_mode", "text"),
                mode=j.get("mode", "normal"),
                total_questions=j.get("total_questions", 8),
            ))
            added += 1
            continue
        row = exist[j["id"]]
        changed = (
            (row.question_types or "") != types
            or (row.total_questions or 0) != j.get("total_questions", 8)
            or (row.duration or 0) != j.get("duration", 20)
            or (row.mode or "") != j.get("mode", "normal")
            or (row.answer_mode or "") != j.get("answer_mode", "text")
        )
        if changed:
            row.question_types = types
            row.total_questions = j.get("total_questions", 8)
            row.duration = j.get("duration", 20)
            row.mode = j.get("mode", "normal")
            row.answer_mode = j.get("answer_mode", "text")
            updated += 1
    if added or updated:
        db.commit()
    if (_get_versions(db).get("jobs") or {}).get("version", "") != JOBS_META_VERSION:
        _set_version(db, "jobs", JOBS_META_VERSION, {"count": len(JOBS)})


def seed_site_content(db: Session):
    """站点文案：首次启动写入默认值，之后以 DB 为准（不覆盖后台编辑）。"""
    row = db.query(SiteContent).filter(SiteContent.key == SITE_KEY).first()
    if not row:
        db.add(SiteContent(
            key=SITE_KEY,
            value=json.dumps(DEFAULT_SITE_CONTENT, ensure_ascii=False),
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        db.commit()
