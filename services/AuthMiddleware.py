# genericframework\services\AuthMiddleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import jwt
from config import JWT_SECRET, JWT_ALGORITHM
from log_util import Error
from services.response import resp_401

# 无需鉴权的接口白名单
# 无需携带token、直接放行的接口路径白名单
WHITE_LIST = [
    "/api/common/login",
    "/api/common/register",
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # 白名单路径直接放行
        if path in WHITE_LIST:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # 修复：不要取 .body，直接返回 Response 对象
            return resp_401("请先登录")

        token = auth_header.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.state.user = payload
        except jwt.ExpiredSignatureError:
            return resp_401("登录已过期，请重新登录")
        except Exception:
            return resp_401("Token无效")

        response = await call_next(request)
        return response


from fastapi import Depends, security
from fastapi.security import HTTPAuthorizationCredentials

import time
import jwt
from datetime import timedelta
from typing import Optional
from pydantic import BaseModel
from services.response import resp_401
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_SECONDS

# ===================== 请求结构体定义 =====================
# 登录入参
class LoginReq(BaseModel):
    username: str
    password: str

# 注册入参
class RegisterReq(BaseModel):
    username: str
    password: str

# ===================== 工具函数：生成JWT令牌 =====================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = int(time.time()) + expires_delta.total_seconds()
    else:
        expire = int(time.time()) + JWT_EXPIRE_SECONDS
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


# ===================== JWT 全局鉴权依赖 =====================
def jwt_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    if not credentials:
        raise resp_401("请先登录")
    token_str = credentials.credentials
    try:
        payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise resp_401("登录已过期，请重新登录")
    except Exception as e:
        Error.error(f"Token解析异常: {str(e)}")
        raise resp_401("Token无效，请重新登录")

# 快捷依赖：直接获取当前登录用户ID
def get_login_uid(user_info: dict = Depends(jwt_auth)) -> int:
    return int(user_info["userId"])

# 快捷依赖：获取完整登录用户信息
def get_login_userinfo(user_info: dict = Depends(jwt_auth)) -> dict:
    return user_info