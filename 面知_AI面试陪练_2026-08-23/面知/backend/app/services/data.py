"""岗位配置与种子题库数据。

数据源：app/seed_data/{jobs,questions}.json（由 backend/tools/generate_seed.py 生成，
支持用 tools/import_jobs.py 按 CSV 幂等合并扩充）。

岗位在启动时灌入 DB（jobs 表），此后以 DB 为唯一来源，便于后台在线编辑。
"""
import json
import os
from typing import List, Dict

from sqlalchemy.orm import Session

from ..models import Job
from .taxonomy import resolve_family

_SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed_data")


def _load(name: str) -> List[Dict]:
    path = os.path.join(_SEED_DIR, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


JOBS: List[Dict] = _load("jobs.json")
SEED_QUESTIONS: List[Dict] = _load("questions.json")


def job_to_dict(job: Job) -> Dict:
    """ORM Job → 契约字典（camelCase 由 pydantic 别名统一处理，这里保持字段原名）。"""
    try:
        types = json.loads(job.question_types or "[]")
    except (ValueError, TypeError):
        types = []
    return {
        "id": job.id,
        "name": job.name,
        "company": job.company or "",
        "industry": job.industry or "互联网",
        "duration": job.duration or 20,
        "question_types": types,
        "answer_mode": job.answer_mode or "text",
        "mode": job.mode or "normal",
        "total_questions": job.total_questions or 8,
        # 岗位族：前端 mock 模式据此按族抽题，与后端 pick_questions 逻辑保持一致
        "job_family": resolve_family(job.name),
    }


def get_jobs(db: Session) -> List[Job]:
    return db.query(Job).order_by(Job.company, Job.id).all()


def get_job(db: Session, job_id: str) -> Job | None:
    if not job_id:
        return None
    return db.query(Job).filter(Job.id == job_id).first()


def get_jobs_by_company(company: str) -> List[Dict]:
    return [j for j in JOBS if j["company"] == company]


def parse_job_names(raw) -> List[str]:
    """题目 job_names 字段（JSON 数组字符串）→ 岗位名列表，容错解析。"""
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if str(x).strip()]
    try:
        value = json.loads(raw or "[]")
        if isinstance(value, list):
            return [str(x) for x in value if str(x).strip()]
    except (ValueError, TypeError):
        pass
    return []


def question_row(seed: Dict) -> Dict:
    """种子题目 → 可直接入库的字段字典。

    job_names 在 JSON 里是数组，而 questions 表是 TEXT 列，
    入库前必须序列化为 JSON 字符串（否则 SQLite 绑定 list 会报错）。
    """
    data = dict(seed)
    names = data.get("job_names", [])
    data["job_names"] = json.dumps(names if isinstance(names, list) else [], ensure_ascii=False)
    return data


def question_to_dict(q) -> Dict:
    """题目 ORM/字典 → 契约字典（供 QuestionOut 统一构造，避免多处字段漂移）。"""
    return {
        "id": q.id,
        "title": q.title,
        "type": q.type or "行为面试 STAR",
        "difficulty": q.difficulty or "中等",
        "industry": q.industry or "互联网",
        "company": q.company or "",
        "reference_answer": q.reference_answer or "",
        "template": q.template or "",
        "job_family": getattr(q, "job_family", "") or "",
        "job_names": parse_job_names(getattr(q, "job_names", "")),
    }
