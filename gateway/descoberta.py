# Descoberta via UDP multicast: envia RequisicaoDescoberta e recebe AnuncioFonte.
import logging
import socket
import threading
import time

from comum import config, multicast
import cidade_pb2 as pb

log = logging.getLogger("gateway")


class Descoberta:
    def __init__(self, registro):
        self.registro = registro
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.bind(("", config.PORTA_DESCOBERTA))
        multicast.configurar_envio_multicast(self.sock)

    def enviar_requisicao(self):
        req = pb.RequisicaoDescoberta(
            gateway_ip=config.HOST,
            porta_descoberta=config.PORTA_DESCOBERTA,
            porta_dados_udp=config.PORTA_DADOS_UDP,
        )
        self.sock.sendto(req.SerializeToString(), (config.GRUPO_MULTICAST, config.PORTA_MULTICAST))

    def _loop_envio(self):
        log.info("Descoberta multicast em %s:%d", config.GRUPO_MULTICAST, config.PORTA_MULTICAST)
        while True:
            self.enviar_requisicao()
            time.sleep(config.INTERVALO_DESCOBERTA_S)

    def _loop_anuncios(self):
        while True:
            try:
                dados, _ = self.sock.recvfrom(4096)
            except ConnectionResetError:
                continue  # Windows: erro ICMP de pacote anterior, pode ignorar
            anuncio = pb.AnuncioFonte()
            anuncio.ParseFromString(dados)
            if self.registro.registrar(anuncio):
                porta = f"gRPC {anuncio.ip}:{anuncio.porta_grpc}" if anuncio.controlavel else anuncio.ip
                log.info("Nova fonte: %s (%s) [%s]", anuncio.id, pb.TipoFonte.Name(anuncio.tipo), porta)

    def iniciar(self):
        threading.Thread(target=self._loop_anuncios, daemon=True).start()
        threading.Thread(target=self._loop_envio, daemon=True).start()
