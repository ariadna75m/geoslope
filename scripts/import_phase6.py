"""Importación inicial idempotente; rechaza conjuntos diferentes o alterados."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gsreview.application.container import Container

if __name__ == "__main__":
    c = Container()
    c.reviews.import_initial()
    print("Resultados de Fase 6 verificados; 48 episodios disponibles.")
