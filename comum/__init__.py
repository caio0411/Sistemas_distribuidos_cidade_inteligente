# Coloca a pasta "gerado" (código gerado pelo protoc) no sys.path,
# para que "import cidade_pb2" funcione em qualquer módulo do projeto.
import os
import sys

_GERADO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gerado")
if _GERADO not in sys.path:
    sys.path.insert(0, _GERADO)
