"""应用配置 —— T08 涉及。"""

# 外部 API 的 SLA 为 3 秒，5 秒有余量
TIMEOUT = 5

# 数据库连接
DATABASE_URL = "postgresql://testuser:testpass@localhost:5432/testdb"

# 缓存配置
CACHE_TTL = 300  # 秒
