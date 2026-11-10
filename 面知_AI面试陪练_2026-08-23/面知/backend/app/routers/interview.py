import json
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Interview, Question, Answer
from ..services.data import get_job, get_jobs, SEED_QUESTIONS, parse_job_names, question_row
from ..services.analysis import grade_from_score
from ..services.taxonomy import resolve_family
from ..services.auth import get_current_user
from ..schemas import QuestionOut, StartInterviewOut, InterviewFinishIn

router = APIRouter(prefix="/api/interview", tags=["interview"])

# 开场自我介绍只认中文「自我介绍」题干：英文自我介绍（Please introduce yourself）
# 属于英文面试题，不应被强制置顶为开场题。
_INTRO_KEYS = ("自我介绍",)


def _is_intro(q) -> bool:
    title = (q.title or "").lower()
    return any(k in title for k in _INTRO_KEYS)


def _wanted_types(job) -> list:
    try:
        value = json.loads(job.question_types or "[]")
        return [str(t) for t in value if str(t).strip()] if isinstance(value, list) else []
    except (ValueError, TypeError):
        return []


def _buckets(questions, job):
    """把题库按「岗位专属 / 同企业 / 岗位族 / 通用」分桶。

    岗位专属：题目 job_names 含当前岗位名（如「Java开发工程师」的 Spring 事务题）；
    同企业：题目 company 与当前岗位企业一致（企业真题，如字节的后端企业题）；
    岗位族：题目 job_family 与当前岗位族一致（如所有后端岗共用后端族题）；
    通用：题目无 job_family（自我介绍、职业规划、抗压等全岗位可用题）。

    企业题只对同企业岗位开放：避免出现「字节跳动的面试抽到阿里巴巴双 11」这类串味。
    """
    family = resolve_family(job.name)
    company = (job.company or "").strip()
    own, corp, fam, common = [], [], [], []
    for q in questions:
        q_company = (getattr(q, "company", "") or "").strip()
        if q_company and q_company != company:
            continue
        names = parse_job_names(getattr(q, "job_names", ""))
        q_family = (getattr(q, "job_family", "") or "").strip()
        if not q_family:
            common.append(q)
        elif job.name in names:
            own.append(q)
        elif names:
            # 有 job_names 但不含当前岗位 → 该题属于其他岗位的专属题，不外溢
            continue
        elif q_family == family:
            # 企业题同样必须族匹配：否则字节前端会抽到字节的算法/产品企业题
            if q_company:
                corp.append(q)
            else:
                fam.append(q)
    return family, own, corp, fam, common


def pick_questions(questions, job, rng=None):
    """按「岗位专属 → 同企业 → 岗位族 → 通用」优先级抽题，并保证题型配额与岗位声明一致。

    配额策略：
    1. 岗位专属题优先，最多占一半名额，按声明题型各取一道；
    2. 同企业的企业真题补齐尚未覆盖的声明题型；
    3. 岗位族题继续补题型，并把专业题补到总题量的 75%；
    4. 通用题补齐剩余名额（自我介绍 / 职业规划 / 抗压等），仍不足则全量兜底；
    5. 中文自我介绍题强制置顶（面试惯例开场）。
    """
    rng = rng or random
    target = max(1, int(job.total_questions or 8))
    if not questions:
        return []

    family, own, corp, fam, common = _buckets(questions, job)
    wanted = _wanted_types(job)
    picked, seen = [], set()
    own_ids = {q.id for q in own}

    def draw(pool, qtype=None):
        if len(picked) >= target:
            return False
        cands = [q for q in pool if q.id not in seen and (qtype is None or (q.type or "") == qtype)]
        if not cands:  # 该题型在池中不存在时退化为不限题型，避免声明题型落空导致抽不满
            cands = [q for q in pool if q.id not in seen]
        if not cands:
            return False
        q = rng.choice(cands)
        seen.add(q.id)
        picked.append(q)
        return True

    # 1) 岗位专属题：按声明题型各取一道，最多占一半名额
    own_cap = min(len(own), max(1, target // 2)) if own else 0
    for qtype in wanted:
        if len([q for q in picked if q.id in own_ids]) >= own_cap:
            break
        draw(own, qtype)
    while len([q for q in picked if q.id in own_ids]) < own_cap and len(picked) < target:
        if not draw(own):
            break

    # 2) 同企业真题：补声明题型（缺什么补什么）
    for qtype in wanted:
        if qtype in {q.type for q in picked}:
            continue
        draw(corp, qtype)

    # 3) 岗位族题：继续补声明题型
    for qtype in wanted:
        if qtype in {q.type for q in picked}:
            continue
        draw(fam, qtype)

    # 4) 专业题补到总题量的 75%（企业题优先于族题），其余交给通用题
    floor = min(target, max(len(picked), int(target * 0.75)))
    while len(picked) < floor:
        if not (draw(corp) or draw(fam)):
            break

    # 4) 通用题补足
    while len(picked) < target:
        if not draw(common):
            break

    # 5) 极端兜底：题库被后台裁剪到很少时，从全量题库补齐
    if len(picked) < target:
        for q in questions:
            if len(picked) >= target:
                break
            if q.id not in seen:
                seen.add(q.id)
                picked.append(q)

    # 6) 自我介绍题置顶（若未被抽中，替换末位，保证总量不变）
    intro = next((q for q in questions if _is_intro(q)), None)
    if intro:
        if intro.id not in seen:
            if len(picked) >= target and picked:
                dropped = picked.pop()
                seen.discard(dropped.id)
            picked.append(intro)
            seen.add(intro.id)
        picked.sort(key=lambda q: 0 if _is_intro(q) else 1)

    return picked[:target]


@router.post("/start", response_model=StartInterviewOut)
def start_interview(
    # Query alias：前端传 jobId（camelCase），query 参数不做别名转换，必须显式声明
    job_id: str = Query("", alias="jobId"),
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user),
):
    job = get_job(db, job_id)
    if not job:
        all_jobs = get_jobs(db)
        job = all_jobs[0] if all_jobs else None
    if not job:
        raise HTTPException(400, "暂无可用岗位配置，请先在后台添加岗位")
    interview = Interview(
        id=str(uuid.uuid4()),
        user_id=current_user or "",
        job_name=job.name,
        mode=job.mode,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    qs = db.query(Question).all()
    if not qs:
        qs = [Question(**question_row(s)) for s in SEED_QUESTIONS]

    picked = pick_questions(qs, job)
    questions = [QuestionOut(**{
        "id": q.id, "title": q.title, "type": q.type, "difficulty": q.difficulty,
        "industry": q.industry, "company": q.company,
        "reference_answer": q.reference_answer, "template": q.template,
        "job_family": getattr(q, "job_family", "") or "",
        "job_names": parse_job_names(getattr(q, "job_names", "")),
    }) for q in picked]
    return StartInterviewOut(
        interview_id=interview.id, job_name=job.name, mode=job.mode, questions=questions,
    )


@router.post("/{interview_id}/finish")
def finish_interview(interview_id: str, payload: InterviewFinishIn, db: Session = Depends(get_db)):
    """结束面试：上报实际练习时长（秒），并结算总分与评级（基于已保存作答），
    保证报告「用时/得分」与看板「练习总时长/记录」数据一致。"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(404, "面试会话不存在")
    interview.duration_sec = max(0, payload.duration_sec)
    answers = db.query(Answer).filter(Answer.interview_id == interview_id).all()
    if answers:
        avg = round(sum(a.score for a in answers) / len(answers))
        interview.total_score = avg
        interview.grade = grade_from_score(avg)
    db.commit()
    return {"ok": True, "durationSec": interview.duration_sec, "totalScore": interview.total_score}
