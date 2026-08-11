"""PythonAnywhere WSGI 入口。

在 PythonAnywhere 的 Web 选项卡中，将 WSGI 配置文件路径指向本文件即可：
    /home/<你的用户名>/<项目路径>/wsgi.py

PythonAnywhere 会自动把项目根目录加入 sys.path，因此这里只需导入应用。
"""
import os
import sys

# 将项目根目录加入模块搜索路径（确保在任意工作目录下均可导入 webapp）
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from webapp.server import app  # noqa: E402  (Flask 应用实例)

if __name__ == "__main__":
    app.run()
