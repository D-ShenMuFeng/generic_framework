# db.py
import pymysql
from pymysql.cursors import DictCursor
from config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
from services.response import BusinessException
def get_db_conn():
    """底层创建连接，仅供 get_db 内部调用，业务禁止直接使用"""
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset="utf8mb4",
            autocommit=True
        )
    except pymysql.MySQLError as e:
        # 数据库连接失败，抛出业务异常，由全局异常处理器统一返回JSON
        raise BusinessException(0, f"数据库连接失败：{str(e)}") from e

    cursor = conn.cursor(DictCursor)
    return conn, cursor


def get_db():
    """【业务唯一依赖入口】请求生命周期自动创建&释放连接"""
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        yield cursor
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
