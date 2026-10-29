# Recebe as leituras (Leitura) enviadas pelas fontes via UDP.
import logging
import socket
import threading

from comum import config
import cidade_pb2 as pb

log = logging.getLogger("gateway")


class ReceptorUDP:
    def __init__(self, registro, banco):
        self.registro = registro
        self.banco = banco
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", config.PORTA_DADOS_UDP))

    def _loop(self):
        log.info("Recebendo leituras UDP na porta %d", config.PORTA_DADOS_UDP)
        while True:
            try:
                dados, _ = self.sock.recvfrom(4096)
            except ConnectionResetError:
                continue
            leitura = pb.Leitura()
            leitura.ParseFromString(dados)
            if not self.registro.registrar_leitura(leitura):
                continue  # ignora fontes ainda não descobertas
            self.banco.salvar_leitura(leitura, pb.TipoFonte.Name(leitura.tipo))
            if leitura.evento:
                texto = ", ".join(f"{m.grandeza}={m.valor:.1f}{m.unidade}" for m in leitura.medidas)
                log.warning("EVENTO de %s: %s", leitura.fonte_id, texto)

    def iniciar(self):
        threading.Thread(target=self._loop, daemon=True).start()
