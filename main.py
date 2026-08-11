# main.py
from fastapi import FastAPI
from services.response import BusinessException, business_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from services.AuthMiddleware import (AuthMiddleware)
from log_util import RequestLogMiddleware
# from router.login import router as login_router
# from router.letscooking import router as common_router

ACCESS_TOKEN_EXPIRE_MINUTES = 360

app = FastAPI(title="LetCooking 点菜后端", version="1.0")

# ========== 第一步：CORS必须最先注册 ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 第二步：再注册其他业务中间件 ==========
# 全局鉴权中间件
app.add_middleware(AuthMiddleware)
# 全局请求日志
app.add_middleware(RequestLogMiddleware)
# 注册业务异常捕获
app.add_exception_handler(BusinessException, business_exception_handler)

# 挂载路由
# app.include_router(login_router)
# app.include_router(common_router)

# 启动命令
# uvicorn main:app --host 0.0.0.0 --port 8000
# git新建 分支
# git checkout --orphan V1.0.0
# 终止
# netstat -ano | findstr :8000
# taskkill /F /PID XXXX
