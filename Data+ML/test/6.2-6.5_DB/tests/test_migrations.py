from clearpath_db.migrations import migration_is_applied


# Cursor: 模拟数据库游标的 Mock 类
# 捕获 execute() 的 SQL 和参数，供测试断言验证
# 实现 __enter__/__exit__ 以支持 with 语句
class Cursor:
    def __init__(self, count):
        self.count = count
        self.query = None
        self.params = None

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchone(self):
        return (self.count,)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


# Connection: 模拟数据库连接的 Mock 类
# 返回 Cursor 实例，不连接真实数据库
class Connection:
    def __init__(self, count):
        self.cursor_instance = Cursor(count)

    def cursor(self):
        return self.cursor_instance


# test_column_migration_is_detected_from_information_schema:
# 验证迁移检测逻辑：通过查询 information_schema.COLUMNS 判断列是否存在
# Mock Connection 返回 count=1（表示列存在），断言：
#   1. 函数返回 True（迁移已应用）
#   2. 执行的 SQL 包含 information_schema.COLUMNS
#   3. 查询参数正确传递了 table 和 column 名称
def test_column_migration_is_detected_from_information_schema():
    connection = Connection(1)
    migration = {
        "kind": "column",
        "table": "venues",
        "column": "district",
    }

    assert migration_is_applied(connection, migration)
    assert "information_schema.COLUMNS" in connection.cursor_instance.query
    assert connection.cursor_instance.params[-2:] == ("venues", "district")
