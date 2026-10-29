# Endereços e portas de todos os processos (SD_HOST = IP anunciado pela máquina).
import os

# IP que cada processo anuncia para os outros
HOST = os.environ.get("SD_HOST", "127.0.0.1")

# Descoberta (UDP multicast)
GRUPO_MULTICAST = "224.1.1.1"
PORTA_MULTICAST = 40000
INTERVALO_DESCOBERTA_S = 10  # Gateway repete a descoberta periodicamente

# Gateway
PORTA_DADOS_UDP = 40001   # recebe as leituras das fontes
PORTA_TCP_CLIENTES = 40002  # atende os clientes (CLI e Web)
PORTA_DESCOBERTA = 40003  # recebe os anúncios das fontes

# Monitoramento de falhas
INTERVALO_MONITOR_S = 3
TIMEOUT_GRPC_S = 2

# Banco de dados (persistência)
CAMINHO_BANCO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados", "leituras.db")
