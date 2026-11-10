"""本地用户认证（替代云服务的 Auth 模块）。

实现目标与云服务一致：注册 / 登录 / 会话凭证 / 当前用户识别。
出于降低部署依赖的考虑，这里不引入 passlib / pyjwt：
  - 密码哈希：标准库 hashlib.pbkdf2_hmac（每用户独立盐）
  - 会话令牌：HMAC-SHA256 签名的不透明 token（base64url(json payload) + 签名）

令牌含 user_id 与过期时间，服务端用 MIANZHI_JWT_SECRET 校验签名，避免伪造。
"""
import os
import hashlib
import hmac
import json
import base64
import time
import uuid

from fastapi import Depends, HTTPException, Header, Request

_SECRET = (os.getenv("MIANZHI_JWT_SECRET") or "mianzhi-dev-secret-change-me").encode("utf-8")
_TOKEN_TTL = 60 * 60 * 24 * 30  # 30 天

# 令牌同时通过 Cookie 下发：部分托管/分享网关会剥离 Authorization 头，
# Cookie 是同域自动携带的，作为最可靠的回落通道。
COOKIE_NAME = "mz_token"
COOKIE_MAX_AGE = _TOKEN_TTL


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def hash_password(password: str) -> tuple[str, str]:
    """返回 (salt_hex, hash_hex)。"""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex(), dk.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def create_token(user_id: str) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + _TOKEN_TTL}
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(_SECRET, body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_token(token: str) -> str | None:
    """校验令牌，返回 user_id；失败返回 None。"""
    try:
        body, sig = token.rsplit(".", 1)
        expect = hmac.new(_SECRET, body.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None
        payload = json.loads(_b64url_decode(body))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload.get("uid")
    except Exception:
        return None


def _candidate_tokens(request: Request | None, authorization: str | None) -> list[str]:
    """按可靠性排序收集候选令牌：Authorization 头 → Cookie → 查询参数。

    托管平台的分享网关可能剥离自定义头，因此不能只依赖 Authorization；
    浏览器里也可能残留过期令牌，所以候选是「全部尝试」而不是只取第一个。
    """
    tokens: list[str] = []
    if authorization and authorization.startswith("Bearer "):
        tokens.append(authorization[len("Bearer "):].strip())
    if request is not None:
        c = request.cookies.get(COOKIE_NAME)
        if c:
            tokens.append(c.strip())
        q = request.query_params.get("token")
        if q:
            tokens.append(q.strip())
    return [t for t in tokens if t]


def get_current_user(request: Request, authorization: str | None = Header(default=None)) -> str | None:
    """可选认证：返回当前用户 id；无/无效令牌返回 None（保持向后兼容的共享演示数据）。"""
    for token in _candidate_tokens(request, authorization):
        uid = verify_token(token)
        if uid:
            return uid
    return None


def require_user(request: Request, authorization: str | None = Header(default=None)) -> str:
    """强制认证：无效令牌返回 401。用于 /user/me 等必须登录的接口。"""
    uid = get_current_user(request, authorization)
    if not uid:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return uid
