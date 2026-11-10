from contextlib import asynccontextmanager
import json
import os

from dotenv import load_dotenv

# 加载 backend/.env（若存在），使 os.getenv 能读到 MIANZHI_* 配置（ASR/LLM 等）
# __file__ = backend/app/main.py -> 两次 dirname 得到 backend 根目录
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))

# 生产配置（WorkBuddy 应用发布等单端口部署场景）：普通 JSON，不依赖 .env 是否被打包。
# 只填充「当前尚未设置」的键，因此本地 .env 始终优先。
_RT_PATH = os.path.join(_BACKEND_ROOT, "app", "runtime_settings.json")
if os.path.exists(_RT_PATH):
    try:
        with open(_RT_PATH, "r", encoding="utf-8") as _f:
            for _k, _v in json.load(_f).items():
                if _v not in (None, "") and _k not in os.environ:
                    os.environ[_k] = str(_v)
    except Exception:
        pass

# 单端口全栈部署时，前端构建产物放在 backend/webapp/；本地开发没有该目录即自动跳过。
_WEBAPP_DIR = os.path.join(_BACKEND_ROOT, "webapp")
_HAS_WEBAPP = os.path.isdir(_WEBAPP_DIR)

_INSTANCE_ID = __import__("uuid").uuid4().hex[:8]

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .config import settings
from .db import init_db, SessionLocal, get_db
from .seed import seed_questions, seed_jobs, seed_site_content, DEFAULT_SITE_CONTENT, SITE_KEY
from .models import SiteContent
from .routers import questions, interview, answers, report, growth, qa, asr, user, admin, storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_questions(db)
        seed_jobs(db)
        seed_site_content(db)
    finally:
        db.close()
    yield


app = FastAPI(title="面知 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (questions.router, interview.router, answers.router, report.router,
          growth.router, qa.router, asr.router, user.router, admin.router, storage.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    # instance 每次进程启动变化：多副本部署时可用于判断请求是否落在同一实例
    return {"status": "ok", "instance": _INSTANCE_ID}


@app.get("/api/content", tags=["content"])
def site_content(db: Session = Depends(get_db)):
    """公开：站点文案（首页 hero / 帮助中心 FAQ），后台「站点文案」编辑后即时生效。"""
    row = db.query(SiteContent).filter(SiteContent.key == SITE_KEY).first()
    if not row:
        return DEFAULT_SITE_CONTENT
    try:
        data = json.loads(row.value or "{}")
    except (ValueError, TypeError):
        data = {}
    merged = dict(DEFAULT_SITE_CONTENT)
    merged.update(data)
    return merged


# ---------- 根路径落地页（自包含 HTML，极简蓝调） ----------

ROOT_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>面知 API · AI 面试陪练后端服务</title>
<link rel="icon" type="image/svg+xml" href="/favicon.ico">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", "Microsoft YaHei", sans-serif;
    background: #F5F5F7; color: #1D1D1F; min-height: 100vh;
    display: flex; align-items: center; justify-content: center; padding: 40px 20px;
  }
  .card {
    background: #FFFFFF; border-radius: 18px; padding: 48px 52px;
    max-width: 560px; width: 100%; border: 1px solid rgba(0,0,0,.06);
  }
  .badge {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 13px; font-weight: 600; color: #34C759;
    background: rgba(52,199,89,.1); border-radius: 999px; padding: 6px 14px; margin-bottom: 20px;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #34C759; }
  h1 { font-size: 30px; font-weight: 600; letter-spacing: -.5px; margin-bottom: 6px; }
  .sub { font-size: 15px; color: #6E6E73; margin-bottom: 28px; }
  .meta { border-top: 1px solid rgba(0,0,0,.06); padding-top: 20px; margin-bottom: 24px; }
  .row { display: flex; justify-content: space-between; gap: 16px; font-size: 14px; padding: 7px 0; }
  .row .k { color: #6E6E73; flex: 0 0 auto; }
  .row .v { font-weight: 600; text-align: right; overflow-wrap: anywhere; }
  /* 长文本改为上下结构，避免两端对齐折行产生孤字 */
  .row.long { display: block; }
  .row.long .v { display: block; text-align: left; margin-top: 6px; line-height: 1.6; }
  .links { display: flex; gap: 12px; flex-wrap: wrap; }
  a.btn {
    flex: 1; min-width: 200px; text-align: center; text-decoration: none;
    font-size: 15px; font-weight: 600; padding: 13px 20px; border-radius: 12px;
    transition: opacity .15s ease;
  }
  a.btn:hover { opacity: .85; }
  a.primary { background: #007AFF; color: #FFFFFF; }
  a.ghost { background: rgba(0,122,255,.08); color: #007AFF; }
  .foot { margin-top: 24px; font-size: 12px; color: #6E6E73; text-align: center; }
</style>
</head>
<body>
  <div class="card">
    <div class="badge"><span class="dot"></span>服务运行中</div>
    <h1>面知 API</h1>
    <p class="sub">AI 面试陪练 · 后端服务（FastAPI + SQLite）</p>
    <div class="meta">
      <div class="row"><span class="k">版本</span><span class="v">1.0.0</span></div>
      <div class="row"><span class="k">框架</span><span class="v">FastAPI / Uvicorn</span></div>
      <div class="row"><span class="k">数据库</span><span class="v">SQLite（已初始化并灌入题库种子）</span></div>
      <div class="row long"><span class="k">接口规模</span><span class="v">10 个路由模块 · questions / interview / answers / report / growth / qa / asr / user / admin / storage</span></div>
    </div>
    <div class="links">
      <a class="btn primary" href="__WEB_URL__/admin">后台管理控制台</a>
      <a class="btn ghost" href="/docs">接口文档 Swagger UI</a>
    </div>
    <p class="foot">前台 __WEB_URL__/ · 后台 __WEB_URL__/admin · 接口文档 /docs</p>
  </div>
</body>
</html>"""

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#007AFF"/>
  <text x="32" y="43" font-family="-apple-system,'PingFang SC','Microsoft YaHei',sans-serif"
        font-size="34" font-weight="700" fill="#FFFFFF" text-anchor="middle">面</text>
</svg>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    # 单端口全栈部署：直接把前端首页作为站点入口
    webapp_index = os.path.join(_WEBAPP_DIR, "index.html")
    if _HAS_WEBAPP and os.path.isfile(webapp_index):
        return FileResponse(webapp_index)
    web = (settings.web_url or "http://127.0.0.1:5173").rstrip("/")
    return ROOT_HTML.replace("__WEB_URL__", web)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


# ---------- 前端静态资源托管（必须有 webapp/ 目录才启用） ----------
if _HAS_WEBAPP:
    _ASSETS_DIR = os.path.join(_WEBAPP_DIR, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        """Vue Router history 模式：非 API、非真实文件的路径一律回 index.html。

        必须是最后一个路由——FastAPI 按注册顺序匹配，先注册的接口不会被它吞掉。
        """
        # 未命中的接口保持 404 JSON，避免前端 fetch 拿到 HTML 后解析报错
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        index_file = os.path.join(_WEBAPP_DIR, "index.html")
        if not os.path.isfile(index_file):
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        # 命中真实静态文件就直接返回（图标、robots.txt 等），并做目录穿越防护
        root_abs = os.path.abspath(_WEBAPP_DIR)
        candidate = os.path.abspath(os.path.join(_WEBAPP_DIR, full_path))
        if candidate.startswith(root_abs + os.sep) and os.path.isfile(candidate):
            return FileResponse(candidate)

        return FileResponse(index_file)
