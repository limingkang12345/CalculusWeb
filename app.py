"""微积分计算器 · Flask Web 版启动入口。

本地运行方式：
    pip install -r requirements.txt
    python app.py
然后浏览器打开 http://127.0.0.1:5000

部署到 PythonAnywhere 时无需运行本文件（由 wsgi.py 提供 WSGI 应用）。
"""
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.server import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    threading.Timer(
        1.0, lambda: webbrowser.open("http://127.0.0.1:%d" % port)
    ).start()
    app.run(host="0.0.0.0" if os.environ.get("HOST") else "127.0.0.1",
            port=port, debug=debug)
