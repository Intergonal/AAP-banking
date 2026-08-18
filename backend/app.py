from aap_api.server import build_app

app = build_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)