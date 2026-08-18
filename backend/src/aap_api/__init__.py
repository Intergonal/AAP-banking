from flask import Flask, jsonify
from flask_cors import CORS

from .routes import blueprints
from .schema import init_db
from .ticket_schema import init_tickets_db


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "aap-api"})

    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    init_db()
    init_tickets_db()

    return app