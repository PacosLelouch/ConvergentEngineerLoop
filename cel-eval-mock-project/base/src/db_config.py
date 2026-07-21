"""数据库配置模块 —— T07 涉及。

main 分支端口正确（5432）。
T07 测试分支此处端口错误（5433），导致连接失败。
"""

DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "testdb",
    "user": "testuser",
    "password": "testpass",
}
