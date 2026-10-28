"""Gateway central do sistema Cidade Inteligente.

Uso: python -m gateway.main
"""
import logging

from gateway.banco import Banco
from gateway.controle_grpc import ControleGRPC
from gateway.descoberta import Descoberta
from gateway.receptor_udp import ReceptorUDP
from gateway.registro import RegistroFontes
from gateway.servidor_tcp import ServidorTCP


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
    registro = RegistroFontes()
    banco = Banco()
    controle = ControleGRPC(registro)

    ReceptorUDP(registro, banco).iniciar()   # leituras UDP
    Descoberta(registro).iniciar()           # descoberta multicast
    controle.iniciar()                       # monitor de falhas (gRPC / timeout)
    try:
        ServidorTCP(registro, banco, controle).executar()  # clientes TCP (bloqueante)
    except KeyboardInterrupt:
        logging.getLogger("gateway").info("Encerrando Gateway")


if __name__ == "__main__":
    main()
