"""Registro (em memória) das fontes descobertas e do seu estado."""
import logging
import threading
import time

from comum import config  # noqa: F401  (ajusta o sys.path)
import cidade_pb2 as pb

log = logging.getLogger("gateway")


def agora_ms():
    return int(time.time() * 1000)


class RegistroFontes:
    def __init__(self):
        self.lock = threading.Lock()
        self.fontes = {}           # id -> pb.InfoFonte
        self.ultimo_contato = {}   # id -> timestamp (ms) do último anúncio/leitura
        self.intervalos = {}       # id -> intervalo de envio (s), usado no timeout

    def registrar(self, anuncio):
        """Adiciona/atualiza uma fonte a partir de um AnuncioFonte. Retorna True se for nova."""
        with self.lock:
            nova = anuncio.id not in self.fontes
            info = self.fontes.get(anuncio.id) or pb.InfoFonte(id=anuncio.id)
            info.tipo = anuncio.tipo
            info.ip = anuncio.ip
            info.porta_grpc = anuncio.porta_grpc
            info.controlavel = anuncio.controlavel
            if nova:
                info.estado.CopyFrom(anuncio.estado_inicial)
                info.status = pb.ONLINE
            self.fontes[anuncio.id] = info
            self.intervalos[anuncio.id] = anuncio.intervalo_envio_s or 5
            self.ultimo_contato[anuncio.id] = agora_ms()
        return nova

    def registrar_leitura(self, leitura):
        with self.lock:
            info = self.fontes.get(leitura.fonte_id)
            if info is None:
                return False  # fonte ainda não descoberta
            info.ultima_leitura_ms = leitura.timestamp_ms
            # Atualiza as últimas medidas, mantendo as grandezas já conhecidas
            atuais = {m.grandeza: m for m in info.ultimas_medidas}
            for m in leitura.medidas:
                atuais[m.grandeza] = m
            del info.ultimas_medidas[:]
            info.ultimas_medidas.extend(atuais.values())
            self.ultimo_contato[leitura.fonte_id] = agora_ms()
            return True

    def atualizar_estado(self, fonte_id, estado=None, status=None):
        with self.lock:
            info = self.fontes.get(fonte_id)
            if info is None:
                return
            if estado is not None:
                info.estado.CopyFrom(estado)
                self.intervalos[fonte_id] = estado.intervalo_envio_s or self.intervalos.get(fonte_id, 5)
            if status is not None and status != info.status:
                log.info("Fonte %s: %s -> %s", fonte_id, pb.StatusFonte.Name(info.status), pb.StatusFonte.Name(status))
                info.status = status

    def obter(self, fonte_id):
        with self.lock:
            info = self.fontes.get(fonte_id)
            return pb.InfoFonte.FromString(info.SerializeToString()) if info else None

    def listar(self):
        with self.lock:
            return [pb.InfoFonte.FromString(i.SerializeToString()) for i in self.fontes.values()]

    def segundos_sem_contato(self, fonte_id):
        with self.lock:
            return (agora_ms() - self.ultimo_contato.get(fonte_id, 0)) / 1000, self.intervalos.get(fonte_id, 5)
