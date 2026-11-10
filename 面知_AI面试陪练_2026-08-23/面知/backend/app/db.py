import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# backend 根目录（app/ 的上一级）；相对路径一律以此为基准，
# 避免从不同工作目录启动时把 data/mianzhi.db 分裂成多份。
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(BACKEND_ROOT, p)


# 无服务器部署（阿里云 FC 等）：代码包只读，SQLite 必须落在可写目录。
# 配置 MIANZHI_DB_SEED=代码包内种子库、MIANZHI_DB_PATH=/tmp/mianzhi.db 后，
# 每次冷启动从种子库复制一份，实例内可正常读写，实例回收即恢复初始数据。
if settings.db_seed:
    _seed = _resolve(settings.db_seed)
    _target = _resolve(settings.db_path)
    if not os.path.exists(_target) and os.path.exists(_seed):
        os.makedirs(os.path.dirname(_target), exist_ok=True)
        shutil.copyfile(_seed, _target)

_db_path = _resolve(settings.db_path)

db_dir = os.path.dirname(_db_path)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    f"sqlite:///{_db_path}",
    connect_args={"check_same_thread": False},
    future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # 延迟导入避免循环依赖
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """SQLite 轻量迁移：为旧库补列（新库 create_all 已含，此处幂等）。"""
    from sqlalchemy import text
    with engine.begin() as conn:
        q_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(questions)")).fetchall()]
        if "company" not in q_cols:
            conn.execute(text("ALTER TABLE questions ADD COLUMN company VARCHAR(100) DEFAULT ''"))
        if "job_family" not in q_cols:
            conn.execute(text("ALTER TABLE questions ADD COLUMN job_family VARCHAR(50) DEFAULT ''"))
        if "job_names" not in q_cols:
            conn.execute(text("ALTER TABLE questions ADD COLUMN job_names TEXT DEFAULT '[]'"))
        a_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(answers)")).fetchall()]
        if "question_id" not in a_cols:
            conn.execute(text("ALTER TABLE answers ADD COLUMN question_id VARCHAR(36) DEFAULT ''"))
        if "user_id" not in a_cols:
            conn.execute(text("ALTER TABLE answers ADD COLUMN user_id VARCHAR(36) DEFAULT ''"))

        i_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(interviews)")).fetchall()]
        if "user_id" not in i_cols:
            conn.execute(text("ALTER TABLE interviews ADD COLUMN user_id VARCHAR(36) DEFAULT ''"))
