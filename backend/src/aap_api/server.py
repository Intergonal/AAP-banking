from flask import jsonify

from . import create_app
from .db import check_connection


def build_app():
    app = create_app()

    @app.get("/api/health/db")
    def health_db():
        try:
            version = check_connection()
            return jsonify({"status": "ok", "database": version})
        except Exception as exc:
            return jsonify({"status": "error", "error": str(exc)}), 500

    return app


def main():
    build_app().run(debug=True, port=5000)