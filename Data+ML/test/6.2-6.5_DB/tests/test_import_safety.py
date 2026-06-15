import subprocess
import sys


# test_package_import_has_no_database_or_network_output:
# 验证 clearpath_db 包级导入不会产生任何数据库连接或网络输出
# 使用 subprocess 在独立进程中执行 import，捕获 stdout/stderr
# 断言：导入过程无任何输出（无 print、无连接日志、无网络请求）
def test_package_import_has_no_database_or_network_output():
    completed = subprocess.run(
        [sys.executable, "-c", "import clearpath_db"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == ""
    assert completed.stderr == ""
