# config.py
import pymysql

# ========== JWT 配置 ==========
JWT_SECRET = "suijizhanghaomimayongyujwtjiance_23134134213"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 6 * 3600  # 6小时过期

# ========== MySQL 配置 ==========
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASS = "密码"
DB_NAME = "数据库名"