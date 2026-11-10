from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .db import Base


class Job(Base):
    """岗位配置（后台可编辑，前台「模拟面试」卡片与抽题逻辑共用）。"""

    __tablename__ = "jobs"
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    company = Column(String(100), default="")  # 所属企业，用于抽题企业优先匹配
    industry = Column(String(50), default="互联网")
    duration = Column(Integer, default=20)  # 面试时长(分钟)
    question_types = Column(Text, default="[]")  # JSON 数组字符串
    answer_mode = Column(String(20), default="text")  # text | voice
    mode = Column(String(20), default="normal")  # normal | pressure
    total_questions = Column(Integer, default=8)


class SiteContent(Base):
    """站点文案（键值对，value 存 JSON），后台编辑后前台即时读取。"""

    __tablename__ = "site_content"
    key = Column(String(64), primary_key=True)
    value = Column(Text, default="{}")
    updated_at = Column(String(30), default="")


class Question(Base):
    __tablename__ = "questions"
    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=False)
    type = Column(String(50), default="行为面试 STAR")
    difficulty = Column(String(20), default="中等")
    industry = Column(String(50), default="互联网")
    company = Column(String(100), default="")  # 题目来源企业（如 字节跳动/腾讯/华为），校招通用题为空
    reference_answer = Column(Text, default="")
    template = Column(String(300), default="STAR：情境 → 任务 → 行动 → 结果")
    # 岗位族与精确岗位名绑定（v2 题库）：抽题优先级 岗位名 → 岗位族 → 通用
    job_family = Column(String(50), default="")
    job_names = Column(Text, default="[]")  # JSON 数组字符串，空数组表示该族内通用


class User(Base):
    """注册用户（本地认证，替代云服务的 Auth 模块）。密码以 pbkdf2 加盐哈希存储，不存明文。"""

    __tablename__ = "users"
    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_salt = Column(String(64), default="")
    password_hash = Column(String(128), default="")
    created_at = Column(String(30), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class Interview(Base):
    __tablename__ = "interviews"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, default="")  # 归属用户；空串=匿名/共享演示数据
    job_name = Column(String(100), nullable=False)
    mode = Column(String(20), default="normal")  # normal | pressure
    date = Column(String(30), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    total_score = Column(Integer, default=0)
    grade = Column(String(2), default="C")
    duration_sec = Column(Integer, default=0)
    summary = Column(Text, default="")
    answers = relationship("Answer", back_populates="interview", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"
    id = Column(String(36), primary_key=True)
    interview_id = Column(String(36), ForeignKey("interviews.id"))
    user_id = Column(String(36), index=True, default="")  # 冗余存储，便于按用户快速检索
    question_id = Column(String(36), default="")  # 关联题目 id，用于同题自动保存 upsert
    question = Column(Text, default="")
    answer = Column(Text, default="")
    score = Column(Integer, default=0)
    grade = Column(String(2), default="C")
    is_weak = Column(Boolean, default=False)
    comment = Column(Text, default="")
    suggestion = Column(Text, default="")
    reference_answer = Column(Text, default="")
    template = Column(String(300), default="")
    interview = relationship("Interview", back_populates="answers")
