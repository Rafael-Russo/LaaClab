"""A guarda de camadas também roda sob pytest, para que ninguém
mergeie uma violação sem ver."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))


def test_nenhuma_violacao_de_camada():
    from verificar_camadas import violacoes

    achados = violacoes()
    assert achados == [], "Violações de camada:\n" + "\n".join(achados)
