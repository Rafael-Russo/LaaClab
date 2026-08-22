"""Arquivos servidos diretamente, fora da API."""
from pathlib import Path

from flask import Blueprint, send_from_directory

PASTA_MIDIA = Path(__file__).resolve().parents[2] / "media"


def criar_blueprint_midia() -> Blueprint:
    """Serve `/media/`. Sem esta rota, capa local some sem erro nenhum:
    o `onerror` do JS remove a imagem e mostra o gradiente."""
    bp = Blueprint("midia", __name__)

    @bp.get("/media/<path:caminho>")
    def midia(caminho):
        return send_from_directory(PASTA_MIDIA, caminho)

    return bp
