# Base das fontes Python: descoberta multicast, envio UDP de leituras e servidor gRPC.
import logging
import socket
import threading
import time
from concurrent import futures

from comum import config, multicast  # noqa: F401  (comum ajusta o sys.path)
import cidade_pb2 as pb
import controle_pb2 as ctrl
import controle_pb2_grpc as ctrl_grpc
import grpc


class FonteBase:
    tipo = pb.TIPO_DESCONHECIDO
    controlavel = False
    # Parâmetros que a fonte aceita alterar via gRPC (além de ligar/intervalo/falha)
    parametros_suportados = set()

    def __init__(self, fonte_id, intervalo_envio_s=5, porta_grpc=0):
        self.id = fonte_id
        self.porta_grpc = porta_grpc if self.controlavel else 0
        self.estado = pb.EstadoFonte(ligado=True, intervalo_envio_s=intervalo_envio_s)
        self.lock = threading.Lock()
        self.endereco_gateway = None  # (ip, porta_udp), conhecido após a descoberta
        self.sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.log = logging.getLogger(fonte_id)

    # ----- a ser implementado pelas subclasses -----
    def gerar_medidas(self):
        """Retorna uma lista de pb.Medida com a leitura atual."""
        raise NotImplementedError

    def verificar_evento(self, medidas):
        """Retorna True se a leitura deve ser enviada imediatamente."""
        return False

    # ----- descoberta (multicast) -----
    def _escutar_descoberta(self):
        sock = multicast.criar_socket_receptor_multicast()
        self.log.info("Aguardando descoberta em %s:%d", config.GRUPO_MULTICAST, config.PORTA_MULTICAST)
        while True:
            dados, _ = sock.recvfrom(1024)
            req = pb.RequisicaoDescoberta()
            req.ParseFromString(dados)
            novo = self.endereco_gateway != (req.gateway_ip, req.porta_dados_udp)
            self.endereco_gateway = (req.gateway_ip, req.porta_dados_udp)
            with self.lock:
                anuncio = pb.AnuncioFonte(
                    id=self.id,
                    tipo=self.tipo,
                    ip=config.HOST,
                    porta_grpc=self.porta_grpc,
                    controlavel=self.controlavel,
                    intervalo_envio_s=self.estado.intervalo_envio_s,
                    estado_inicial=self.estado,
                )
            self.sock_udp.sendto(anuncio.SerializeToString(), (req.gateway_ip, req.porta_descoberta))
            if novo:
                self.log.info("Descoberta pelo Gateway %s -> anúncio enviado", req.gateway_ip)

    # ----- envio de leituras (UDP) -----
    def _enviar_leitura(self, medidas, evento):
        leitura = pb.Leitura(
            fonte_id=self.id,
            tipo=self.tipo,
            timestamp_ms=int(time.time() * 1000),
            medidas=medidas,
            evento=evento,
        )
        self.sock_udp.sendto(leitura.SerializeToString(), self.endereco_gateway)
        texto = ", ".join(f"{m.grandeza}={m.valor:.1f}{m.unidade}" for m in medidas)
        self.log.info("%s %s", "EVENTO ->" if evento else "Leitura ->", texto)

    def _loop_leituras(self):
        ultimo_envio = 0.0
        while True:
            time.sleep(1)
            with self.lock:
                ativo = self.estado.ligado and not self.estado.em_falha
                intervalo = self.estado.intervalo_envio_s
            if not ativo or self.endereco_gateway is None:
                continue
            medidas = self.gerar_medidas()
            evento = self.verificar_evento(medidas)
            if evento or time.time() - ultimo_envio >= intervalo:
                self._enviar_leitura(medidas, evento)
                ultimo_envio = time.time()

    # ----- gRPC -----
    def _iniciar_grpc(self):
        servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        ctrl_grpc.add_ControleFonteServicer_to_server(ControleServicer(self), servidor)
        servidor.add_insecure_port(f"0.0.0.0:{self.porta_grpc}")
        servidor.start()
        self.log.info("Servidor gRPC ouvindo na porta %d", self.porta_grpc)
        return servidor

    def iniciar(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
        self.log.info("Iniciando fonte (tipo=%s, controlável=%s)", pb.TipoFonte.Name(self.tipo), self.controlavel)
        if self.controlavel:
            self._servidor_grpc = self._iniciar_grpc()
        threading.Thread(target=self._escutar_descoberta, daemon=True).start()
        try:
            self._loop_leituras()
        except KeyboardInterrupt:
            self.log.info("Encerrando fonte")


class ControleServicer(ctrl_grpc.ControleFonteServicer):
    """Implementação do serviço gRPC ControleFonte (definido em controle.proto)."""

    def __init__(self, fonte):
        self.fonte = fonte

    def _resposta(self, mensagem, sucesso=True):
        self.fonte.log.info("[gRPC] %s", mensagem)
        with self.fonte.lock:
            estado = pb.EstadoFonte()
            estado.CopyFrom(self.fonte.estado)
        return ctrl.RespostaControle(sucesso=sucesso, mensagem=mensagem, estado=estado)

    def ObterEstado(self, request, context):
        with self.fonte.lock:
            estado = pb.EstadoFonte()
            estado.CopyFrom(self.fonte.estado)
        return ctrl.RespostaControle(sucesso=True, mensagem="ok", estado=estado)

    def DefinirLigado(self, request, context):
        with self.fonte.lock:
            self.fonte.estado.ligado = request.valor
        return self._resposta("Fonte " + ("LIGADA" if request.valor else "DESLIGADA"))

    def DefinirIntervalo(self, request, context):
        if request.valor < 1:
            return self._resposta("Intervalo deve ser >= 1 s", sucesso=False)
        with self.fonte.lock:
            self.fonte.estado.intervalo_envio_s = request.valor
        return self._resposta(f"Intervalo de envio alterado para {request.valor} s")

    def DefinirLimiar(self, request, context):
        if "limiar" not in self.fonte.parametros_suportados:
            return self._resposta("Esta fonte não possui limiar de alerta", sucesso=False)
        with self.fonte.lock:
            self.fonte.estado.limiar_alerta = request.valor
        return self._resposta(f"Limiar de alerta alterado para {request.valor:.0f}")

    def DefinirIntensidade(self, request, context):
        if "intensidade" not in self.fonte.parametros_suportados:
            return self._resposta("Esta fonte não possui intensidade", sucesso=False)
        if not 0 <= request.valor <= 100:
            return self._resposta("Intensidade deve estar entre 0 e 100", sucesso=False)
        with self.fonte.lock:
            self.fonte.estado.intensidade = request.valor
        return self._resposta(f"Intensidade alterada para {request.valor}%")

    def DefinirTempoCiclo(self, request, context):
        if "tempo_ciclo" not in self.fonte.parametros_suportados:
            return self._resposta("Esta fonte não possui tempo de ciclo", sucesso=False)
        if not 10 <= request.valor <= 300:
            return self._resposta("Tempo de ciclo deve estar entre 10 e 300 s", sucesso=False)
        with self.fonte.lock:
            self.fonte.estado.tempo_ciclo_s = request.valor
        return self._resposta(f"Tempo de ciclo alterado para {request.valor} s")

    def SimularFalha(self, request, context):
        with self.fonte.lock:
            self.fonte.estado.em_falha = request.valor
        return self._resposta("FALHA SIMULADA (parou de enviar dados)" if request.valor else "Falha removida")
