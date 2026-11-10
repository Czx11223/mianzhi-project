from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Question
from ..services.data import SEED_QUESTIONS, get_jobs, job_to_dict, question_to_dict, question_row
from ..schemas import QuestionOut, JobConfig

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("/jobs", response_model=list[JobConfig])
def list_jobs(db: Session = Depends(get_db)):
    return [JobConfig(**job_to_dict(j)) for j in get_jobs(db)]


@router.get("", response_model=list[QuestionOut])
def list_questions(industry: str = "", job_family: str = "", db: Session = Depends(get_db)):
    """题库列表：支持按行业、岗位族过滤（后台维护与调试用）。"""
    q = db.query(Question)
    if industry:
        q = q.filter(Question.industry == industry)
    if job_family:
        q = q.filter(Question.job_family == job_family)
    items = q.all()
    if not items:  # 数据库为空时回退到种子数据
        items = [Question(**question_row(s)) for s in SEED_QUESTIONS]
    return [QuestionOut(**question_to_dict(i)) for i in items]
