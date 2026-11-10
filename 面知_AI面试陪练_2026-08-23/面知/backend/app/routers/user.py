from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..schemas import ModelSettings
from ..config import settings
from ..db import get_db
from ..models import User
from ..services.auth import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    create_token,
    hash_password,
    require_user,
    verify_password,
)

router = APIRouter(prefix="/api/user", tags=["user"])

# 演示环境用内存存储；生产环境应持久化到数据库或加密配置
_store = ModelSettings(
    model_name=settings.model_name,
    api_key=settings.api_key,
    base_url=settings.base_url,
    temperature=settings.temperature,
    max_tokens=settings.max_tokens,
)


class RegisterIn(BaseModel):
    username: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str


class AuthOut(BaseModel):
    token: str
    user: UserOut


def _issue(response: Response, user: User) -> AuthOut:
    """签发令牌：响应体返回 token，同时写入 Cookie。

    Cookie 是托管/分享网关下的可靠通道（Authorization 头可能被网关剥离）。
    """
    token = create_token(user.id)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        path="/",
        samesite="lax",
    )
    return AuthOut(token=token, user=UserOut(id=user.id, username=user.username))


@router.post("/register", response_model=AuthOut)
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    username = (payload.username or "").strip()
    if len(username) < 2 or len(username) > 30:
        raise HTTPException(400, "用户名需为 2-30 个字符")
    if len(payload.password or "") < 6:
        raise HTTPException(400, "密码至少 6 位")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, "该用户名已被注册")
    salt, hashed = hash_password(payload.password)
    user = User(id=__import__("uuid").uuid4().hex, username=username,
                password_salt=salt, password_hash=hashed)
    db.add(user)
    db.commit()
    return _issue(response, user)


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == (payload.username or "").strip()).first()
    if not user or not verify_password(payload.password or "", user.password_salt, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return _issue(response, user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user_id: str = Depends(require_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    return UserOut(id=user.id, username=user.username)


@router.get("/settings", response_model=ModelSettings)
def get_settings():
    return _store


@router.put("/settings")
def save_settings(payload: ModelSettings):
    global _store
    _store = payload
    return {"ok": True}
