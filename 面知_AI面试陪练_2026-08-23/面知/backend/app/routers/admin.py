"""后台管理接口：岗位 / 题目 / 站点文案 的增删改查。

设计要点：
- 岗位以 DB 为唯一来源（启动时由 seed_jobs 从 jobs.json 灌入），后台编辑即时反映到前台卡片与抽题。
- 题目复用现有 questions 表（与前台共用），后台编辑即时反映到面试抽题。
- 站点文案以键值对存于 site_content 表（value 为 JSON），前台首页/帮助页读取。

本模块为内部管理工具，默认不鉴权；如需上线请在前面加一层访问控制。
"""
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Job, Question, SiteContent
from ..schemas import JobConfig, JobIn, QuestionOut, QuestionIn, QuestionBatchIn
from ..services.data import job_to_dict, question_to_dict
from ..seed import DEFAULT_SITE_CONTENT, SITE_KEY

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _q_to_dict(q: Question) -> dict:
    return question_to_dict(q)


# ---------------------------------------------------------------- 概览
@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    questions = db.query(Question).all()
    industries: dict[str, int] = {}
    for j in jobs:
        industries[j.industry or "未分类"] = industries.get(j.industry or "未分类", 0) + 1
    return {
        "jobCount": len(jobs),
        "questionCount": len(questions),
        "industries": [{"name": k, "count": v} for k, v in sorted(industries.items(), key=lambda x: -x[1])],
        "pressureJobs": sum(1 for j in jobs if j.mode == "pressure"),
        "voiceJobs": sum(1 for j in jobs if j.answer_mode == "voice"),
    }


# ---------------------------------------------------------------- 岗位
@router.get("/jobs", response_model=list[JobConfig])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.company, Job.id).all()
    return [JobConfig(**job_to_dict(j)) for j in jobs]


@router.post("/jobs", response_model=JobConfig)
def create_job(payload: JobIn, db: Session = Depends(get_db)):
    jid = (payload.id or "").strip() or f"job-{uuid.uuid4().hex[:6]}"
    if db.query(Job).filter(Job.id == jid).first():
        raise HTTPException(409, f"岗位 id「{jid}」已存在")
    job = Job(
        id=jid,
        name=payload.name.strip(),
        company=payload.company.strip(),
        industry=payload.industry,
        duration=payload.duration,
        question_types=json.dumps(payload.question_types, ensure_ascii=False),
        answer_mode=payload.answer_mode,
        mode=payload.mode,
        total_questions=payload.total_questions,
    )
    db.add(job)
    db.commit()
    return JobConfig(**job_to_dict(job))


@router.put("/jobs/{job_id}", response_model=JobConfig)
def update_job(job_id: str, payload: JobIn, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "岗位不存在")
    job.name = payload.name.strip()
    job.company = payload.company.strip()
    job.industry = payload.industry
    job.duration = payload.duration
    job.question_types = json.dumps(payload.question_types, ensure_ascii=False)
    job.answer_mode = payload.answer_mode
    job.mode = payload.mode
    job.total_questions = payload.total_questions
    db.commit()
    return JobConfig(**job_to_dict(job))


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "岗位不存在")
    db.delete(job)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- 题目
@router.get("/questions", response_model=list[QuestionOut])
def list_questions(db: Session = Depends(get_db)):
    return [QuestionOut(**_q_to_dict(q)) for q in db.query(Question).all()]


@router.post("/questions/batch")
def batch_update_questions(payload: QuestionBatchIn, db: Session = Depends(get_db)):
    """批量调整题目归属：只改传入的字段，未传字段保持原值。

    改岗位族通常意味着要重新定位，因此支持 clearJobNames 一步清掉精确岗位名，
    避免出现「族已换、岗位名还是旧岗位」导致谁都抽不到的悬空题。
    """
    ids = [i.strip() for i in payload.ids if i and i.strip()]
    if not ids:
        raise HTTPException(400, "请至少选择一道题目")
    if payload.job_family is None and payload.industry is None \
            and payload.difficulty is None and not payload.clear_job_names:
        raise HTTPException(400, "没有需要修改的字段")

    rows = db.query(Question).filter(Question.id.in_(ids)).all()
    found = {r.id for r in rows}
    missing = [i for i in ids if i not in found]

    for q in rows:
        if payload.job_family is not None:
            q.job_family = payload.job_family.strip()
        if payload.industry is not None:
            q.industry = payload.industry.strip()
        if payload.difficulty is not None:
            q.difficulty = payload.difficulty.strip()
        if payload.clear_job_names:
            q.job_names = "[]"
    db.commit()
    return {"updated": len(rows), "missing": missing}


@router.post("/questions", response_model=QuestionOut)
def create_question(payload: QuestionIn, db: Session = Depends(get_db)):
    qid = (payload.id or "").strip() or f"q-{uuid.uuid4().hex[:8]}"
    if db.query(Question).filter(Question.id == qid).first():
        raise HTTPException(409, f"题目 id「{qid}」已存在")
    q = Question(
        id=qid,
        title=payload.title.strip(),
        type=payload.type,
        difficulty=payload.difficulty,
        industry=payload.industry,
        company=payload.company.strip(),
        reference_answer=payload.reference_answer,
        template=payload.template,
        job_family=payload.job_family,
        job_names=json.dumps(payload.job_names, ensure_ascii=False),
    )
    db.add(q)
    db.commit()
    return QuestionOut(**_q_to_dict(q))


@router.put("/questions/{qid}", response_model=QuestionOut)
def update_question(qid: str, payload: QuestionIn, db: Session = Depends(get_db)):
    q = db.query(Question).filter(Question.id == qid).first()
    if not q:
        raise HTTPException(404, "题目不存在")
    q.title = payload.title.strip()
    q.type = payload.type
    q.difficulty = payload.difficulty
    q.industry = payload.industry
    q.company = payload.company.strip()
    q.reference_answer = payload.reference_answer
    q.template = payload.template
    q.job_family = payload.job_family
    q.job_names = json.dumps(payload.job_names, ensure_ascii=False)
    db.commit()
    return QuestionOut(**_q_to_dict(q))


@router.delete("/questions/{qid}")
def delete_question(qid: str, db: Session = Depends(get_db)):
    q = db.query(Question).filter(Question.id == qid).first()
    if not q:
        raise HTTPException(404, "题目不存在")
    db.delete(q)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- 站点文案
@router.get("/content")
def get_content(db: Session = Depends(get_db)):
    row = db.query(SiteContent).filter(SiteContent.key == SITE_KEY).first()
    if not row:
        return DEFAULT_SITE_CONTENT
    try:
        data = json.loads(row.value or "{}")
    except (ValueError, TypeError):
        data = {}
    # 补齐缺失键，避免前端拿到不完整结构
    merged = dict(DEFAULT_SITE_CONTENT)
    merged.update(data)
    return merged


@router.put("/content")
def save_content(payload: dict, db: Session = Depends(get_db)):
    row = db.query(SiteContent).filter(SiteContent.key == SITE_KEY).first()
    if not row:
        row = SiteContent(key=SITE_KEY)
    row.value = json.dumps(payload, ensure_ascii=False)
    row.updated_at = _now()
    db.add(row)
    db.commit()
    return {"ok": True, "updatedAt": row.updated_at}
