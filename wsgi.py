"""Ponto de entrada. Em produção usa waitress (o alvo é Windows)."""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    if os.getenv("FLASK_ENV", "development").lower() == "production":
        from waitress import serve

        serve(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
    else:
        app.run(debug=True, port=5000)
