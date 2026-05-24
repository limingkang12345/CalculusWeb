# -*- coding: utf-8 -*-
"""
PythonAnyWhere WSGI 配置文件
放置于项目根目录下，PythonAnyWhere 会自动加载此文件。
"""
import sys
import os

# 将项目目录添加到 Python 路径
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from app import app as application

# 可选：在生产环境下关闭调试模式
application.debug = False
