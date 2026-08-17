from flask import jsonify

from aap_api import create_app
from aap_api.db import check_connection

app = create_app()


@app.get("/api/health/db")
def health_db():
    try:
        version = check_connection()
        return jsonify({"status": "ok", "database": version})
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)