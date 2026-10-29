# Adiciona a pasta "gerado" (código do protoc) ao sys.path.
import os
import sys

_GERADO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gerado")
if _GERADO not in sys.path:
    sys.path.insert(0, _GERADO)
