# log_util.py
import logging
import gc
import time
import os
import psutil
from logging.handlers import RotatingFileHandler

from typing import Callable, AsyncIterator
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ====================== 配置常量 ======================
# 单次请求内存暴涨阈值 MB
SINGLE_UP_THRESHOLD = 300
# 相比进程启动总内存溢出阈值 MB
TOTAL_OVER_THRESHOLD = 500
# 请求、响应日志文本最大记录字符（需求改为200）
MAX_CONTENT_LOG = 200
# ======================================================

# 全局内存监控基准与告警阈值
BASE_PROCESS_MEM = None
LAST_REQUEST_MEM = 0


def get_memory_info():
    """
    self_rss_mb：当前服务进程占用物理内存(MB)
    sys_total_mb：整机总内存(MB)
    sys_used_mb：整机已使用内存(MB)
    sys_avail_mb：整机可用剩余内存(MB)
    sys_usage_pct：整机内存使用率(%)
    """
    pid = os.getpid()
    proc = psutil.Process(pid)
    self_rss_mb = round(proc.memory_info().rss / 1024 / 1024, 2)

    vm = psutil.virtual_memory()
    sys_total_mb = round(vm.total / 1024 / 1024, 2)
    sys_used_mb = round(vm.used / 1024 / 1024, 2)
    sys_avail_mb = round(vm.available / 1024 / 1024, 2)
    sys_usage_pct = vm.percent

    return {
        "self_rss_mb": self_rss_mb,
        "sys_total_mb": sys_total_mb,
        "sys_used_mb": sys_used_mb,
        "sys_avail_mb": sys_avail_mb,
        "sys_usage_pct": sys_usage_pct
    }


# 自定义日志时间格式化器
class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(record.created))


# 全局根日志配置
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()

log_format = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)d: %(message)s"
formatter = CustomFormatter(log_format)

temp_path = "./log"
os.makedirs(temp_path, exist_ok=True)

# 滚动文件日志：单文件最大500MB，最多保留5个归档日志
file_handler = RotatingFileHandler(
    filename="log/app.log",
    maxBytes=1024 * 1024 * 500,
    backupCount=5,
    encoding="utf-8"
)
stream_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)

# 业务日志对象
Info = logging.getLogger("info")
Error = logging.getLogger("error")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        body_raw = await request.body()

        # 修复request.body只能读取一次问题
        async def receive():
            return {"type": "http.request", "body": body_raw}
        request._receive = receive

        query_str = str(request.query_params)
        req_body = body_raw.decode("utf-8", errors="replace")
        ctype = request.headers.get("content-type", "")

        # 文件/流式上传直接屏蔽请求体记录，防止超大日志
        if "multipart/form-data" in ctype or "stream" in ctype:
            req_body = "[二进制文件/上传，不记录]"

        full_req = f"Query: {query_str}\nBody: {req_body}" if query_str else req_body
        # 截断至200字符
        if len(full_req) > MAX_CONTENT_LOG:
            full_req = full_req[:MAX_CONTENT_LOG] + "..."

        # 执行接口业务逻辑
        resp: Response = await call_next(request)

        # 【建议】不要每次请求强制gc.collect()，频繁调用会造成CPU抖动，可按需移至告警分支内
        # gc.collect()
        mem_info = get_memory_info()

        # 初始化进程启动基准内存
        global BASE_PROCESS_MEM, LAST_REQUEST_MEM
        if BASE_PROCESS_MEM is None:
            BASE_PROCESS_MEM = mem_info["self_rss_mb"]
            LAST_REQUEST_MEM = mem_info["self_rss_mb"]

        current_mem = mem_info["self_rss_mb"]
        single_grow = round(current_mem - LAST_REQUEST_MEM, 2)
        total_grow = round(current_mem - BASE_PROCESS_MEM, 2)
        LAST_REQUEST_MEM = current_mem

        # ===================== 重点改造：流式响应判断 =====================
        resp_body = ""
        # 判断是否为流式传输：chunked编码 / SSE / stream类型响应，禁止全量消费body_iterator
        is_stream_response = (
                "chunked" in resp.headers.get("transfer-encoding", "")
                or "text/event-stream" in resp.headers.get("content-type", "")
                or "stream" in resp.headers.get("content-type", "")
        )

        if is_stream_response:
            resp_body = "[流式响应，禁止完整读取包体，避免连接卡死]"
        else:
            # 非流式响应才读取body
            body_bytes = b""
            try:
                async for chunk in resp.body_iterator:
                    body_bytes += chunk
                resp_body = body_bytes.decode("utf-8", errors="replace")
                # 截断200字符
                if len(resp_body) > MAX_CONTENT_LOG:
                    resp_body = resp_body[:MAX_CONTENT_LOG] + "..."

                async def new_body_iter() -> AsyncIterator[bytes]:
                    yield body_bytes
                resp.body_iterator = new_body_iter()
            except Exception as e:
                resp_body = f"[响应读取异常: {str(e)}]"
        # =================================================================

        cost_ms = (time.time() - start) * 1000
        ip = request.client.host if request.client else ""
        method = request.method
        path = request.url.path
        status = resp.status_code

        # 组装日志内容
        log_msg = (
            "\n===================================\n"
            f"IP: {ip} | {method} {path} | 状态: {status} | 耗时: {cost_ms}ms\n"
            f"【进程内存】当前:{current_mem} MB | 启动基准:{BASE_PROCESS_MEM} MB | 本次变动:{single_grow} MB | 累计超基准:{total_grow} MB\n"
            f"【整机内存】总:{mem_info['sys_total_mb']} MB 已用:{mem_info['sys_used_mb']} MB 剩余:{mem_info['sys_avail_mb']} MB 使用率:{mem_info['sys_usage_pct']}%\n"
            f"请求: {full_req}\n"
            f"响应: {resp_body}\n"
            "===================================\n"
        )
        Info.info(log_msg)

        # 内存阈值告警
        alert_msg = []
        if single_grow > SINGLE_UP_THRESHOLD:
            alert_msg.append(f"单次内存暴涨超过{SINGLE_UP_THRESHOLD}MB")
        if total_grow > TOTAL_OVER_THRESHOLD:
            alert_msg.append(f"进程总内存超出启动基准{TOTAL_OVER_THRESHOLD}MB，疑似内存泄漏")

        if alert_msg:
            # 出现内存暴涨时再主动触发垃圾回收（可选开启）
            # gc.collect()
            Error.warning(
                f"【内存告警】IP:{ip} {method} {path} 告警：{'；'.join(alert_msg)} "
                f"当前内存:{current_mem}MB 基准:{BASE_PROCESS_MEM}MB"
            )

        return resp