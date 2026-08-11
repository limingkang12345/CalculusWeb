"""Flask 应用工厂。"""
import os
from flask import Flask, render_template

from .api import api

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(_ROOT, "templates"),
        static_folder=os.path.join(_ROOT, "static"),
        static_url_path="/static",
    )
    app.secret_key = "calculus-calculator-web-2026"
    app.register_blueprint(api)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/blockly")
    def blockly_editor():
        return render_template("blockly.html")

    return app


app = create_app()
