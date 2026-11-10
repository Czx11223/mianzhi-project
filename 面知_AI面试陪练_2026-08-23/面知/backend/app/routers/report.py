from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Interview, Answer
from ..schemas import ReportOut, AnswerOut, Dimension, InterviewHistory
from ..services.analysis import grade_from_score, build_summary
from ..services.pdf import generate_report_pdf
from ..services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["report"])


def _scope(db: Session, user_id: str | None):
    """按当前用户过滤已作答的面试；未登录时返回全部（共享演示数据）。"""
    q = db.query(Interview).join(Answer).distinct()
    if user_id:
        q = q.filter(Interview.user_id == user_id)
    return q


@router.get("/report/recent", response_model=ReportOut)
def get_recent_report(db: Session = Depends(get_db), current_user: str | None = Depends(get_current_user)):
    """最近一次「已作答」面试的报告（报告页无 id 时默认展示）。
    注意：必须声明在 /report/{interview_id} 之前，避免 'recent' 被解析为 id。"""
    interview = (
        _scope(db, current_user)
        .order_by(Interview.date.desc(), Interview.id.desc())
        .first()
    )
    if not interview:
        raise HTTPException(404, "暂无面试记录")
    return get_report(interview.id, db)


@router.get("/report/{interview_id}", response_model=ReportOut)
def get_report(interview_id: str, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(404, "面试记录不存在")
    answers = db.query(Answer).filter(Answer.interview_id == interview_id).all()
    ans_out = [AnswerOut(
        id=a.id, question_id=a.question_id, question=a.question, answer=a.answer, score=a.score, grade=a.grade,
        is_weak=a.is_weak, comment=a.comment, suggestion=a.suggestion,
        reference_answer=a.reference_answer, template=a.template,
    ) for a in answers]

    if answers:
        avg = round(sum(a.score for a in answers) / len(answers))
        dimensions = [
            Dimension(name="内容完整度", score=min(100, avg + 4)),
            Dimension(name="逻辑结构", score=min(100, avg + 2)),
            Dimension(name="表达流畅度", score=max(40, avg - 7)),
            Dimension(name="岗位匹配度", score=min(100, avg + 1)),
            Dimension(name="抗压表现", score=max(40, avg - 4) if interview.mode == "pressure" else min(100, avg)),
        ]
        summary = build_summary(avg, sum(1 for a in answers if a.is_weak), [d.model_dump() for d in dimensions])
    else:
        avg, dimensions, summary = 0, [], ""
    interview.total_score = avg
    interview.grade = grade_from_score(avg)
    interview.summary = summary
    db.commit()

    return ReportOut(
        id=interview.id, job_name=interview.job_name, mode=interview.mode, date=interview.date,
        total_score=avg, grade=interview.grade, duration_sec=interview.duration_sec,
        summary=summary, dimensions=dimensions, answers=ans_out,
    )


@router.get("/report/{interview_id}/pdf")
def get_report_pdf(interview_id: str, db: Session = Depends(get_db)):
    report = get_report(interview_id, db)
    data = report.model_dump()
    pdf = generate_report_pdf(data)
    return Response(content=pdf, media_type="application/pdf",
                      headers={"Content-Disposition": f'attachment; filename="mianzhi_report_{interview_id}.pdf"'})


@router.get("/interviews", response_model=list[InterviewHistory])
def list_interviews(db: Session = Depends(get_db), current_user: str | None = Depends(get_current_user)):
    """历史记录列表：只含已作答的完成记录，按新到旧排列（最新在上）。登录后仅看自己的记录。"""
    rows = (
        _scope(db, current_user)
        .order_by(Interview.date.desc(), Interview.id.desc())
        .all()
    )
    return [InterviewHistory(
        id=i.id, date=i.date, job_name=i.job_name, mode=i.mode, score=i.total_score,
        grade=i.grade, duration_sec=i.duration_sec,
    ) for i in rows]
