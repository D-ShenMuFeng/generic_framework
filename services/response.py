# genericframework\services\response.py
from fastapi import Request
from fastapi.responses import JSONResponse
from requests import Request


def resp_success(msg: str, data=None):
    return JSONResponse(
        status_code=200,
        content={"code": 1, "msg": msg, "data": data}
    )

from fastapi.responses import JSONResponse
from log_util import Error  # 导入你全局的Error日志对象


class BusinessException(Exception):
    """自定义业务异常"""
    def __init__(self, code: int, msg: str, data=None):
        self.code = code
        self.msg = msg
        self.data = data

        Error.error(f"[BusinessException] code:{self.code} msg:{self.msg})")

        super().__init__(self.msg)


# ---------------- 原有快捷响应函数（保留，兼容老代码） ----------------
def resp_success(msg: str, data=None):
    return JSONResponse(
        status_code=200,
        content={"code": 1, "msg": msg, "data": data}
    )


def resp_fail(msg: str):
    return JSONResponse(
        status_code=200,
        content={"code": 0, "msg": msg, "data": None}
    )


def resp_401(msg: str):
    return JSONResponse(
        status_code=401,
        content={"code": 401, "msg": msg, "data": None}
    )

async def business_exception_handler(request: Request, exc: BusinessException):
    """拦截业务异常，统一输出标准JSON"""
    return JSONResponse(
        status_code=200,
        content={
            "code": exc.code,
            "msg": exc.msg,
            "data": exc.data
        }
    )

