# Cliente gRPC das fontes: executa comandos e monitora se cada fonte está viva.
import logging
import threading
import time

import grpc

from comum import config
import cidade_pb2 as pb
import controle_pb2 as ctrl
import controle_pb2_grpc as ctrl_grpc

log = logging.getLogger("gateway")


class ControleGRPC:
    def __init__(self, registro):
        self.registro = registro
        self.stubs = {}  # "ip:porta" -> stub gRPC

    def _stub(self, info):
        endereco = f"{info.ip}:{info.porta_grpc}"
        if endereco not in self.stubs:
            self.stubs[endereco] = ctrl_grpc.ControleFonteStub(grpc.insecure_channel(endereco))
        return self.stubs[endereco]

    @staticmethod
    def _status_de(estado):
        if estado.em_falha:
            return pb.FALHA
        if not estado.ligado:
            return pb.DESLIGADA
        return pb.ONLINE

    def executar_comando(self, comando):
        info = self.registro.obter(comando.fonte_id)
        if info is None:
            return pb.ResultadoComando(sucesso=False, mensagem=f"Fonte '{comando.fonte_id}' não encontrada")
        if not info.controlavel:
            return pb.ResultadoComando(sucesso=False, mensagem=f"Fonte '{comando.fonte_id}' não é controlável")

        stub = self._stub(info)
        t = config.TIMEOUT_GRPC_S
        # Traduz o comando recebido do cliente (TCP) na chamada gRPC correspondente
        chamadas = {
            pb.LIGAR: lambda: stub.DefinirLigado(ctrl.ValorBool(valor=True), timeout=t),
            pb.DESLIGAR: lambda: stub.DefinirLigado(ctrl.ValorBool(valor=False), timeout=t),
            pb.DEFINIR_INTERVALO: lambda: stub.DefinirIntervalo(ctrl.ValorInt(valor=int(comando.valor)), timeout=t),
            pb.DEFINIR_LIMIAR: lambda: stub.DefinirLimiar(ctrl.ValorDouble(valor=comando.valor), timeout=t),
            pb.DEFINIR_INTENSIDADE: lambda: stub.DefinirIntensidade(ctrl.ValorInt(valor=int(comando.valor)), timeout=t),
            pb.DEFINIR_TEMPO_CICLO: lambda: stub.DefinirTempoCiclo(ctrl.ValorInt(valor=int(comando.valor)), timeout=t),
            pb.SIMULAR_FALHA: lambda: stub.SimularFalha(ctrl.ValorBool(valor=True), timeout=t),
            pb.RECUPERAR_FALHA: lambda: stub.SimularFalha(ctrl.ValorBool(valor=False), timeout=t),
        }
        if comando.acao not in chamadas:
            return pb.ResultadoComando(sucesso=False, mensagem="Ação desconhecida")

        log.info("Comando gRPC -> %s: %s %s", comando.fonte_id, pb.AcaoComando.Name(comando.acao),
                 comando.valor if comando.valor else "")
        try:
            resposta = chamadas[comando.acao]()
        except grpc.RpcError as erro:
            self.registro.atualizar_estado(comando.fonte_id, status=pb.OFFLINE)
            return pb.ResultadoComando(sucesso=False, mensagem=f"Fonte inacessível ({erro.code().name})")

        self.registro.atualizar_estado(comando.fonte_id, estado=resposta.estado, status=self._status_de(resposta.estado))
        return pb.ResultadoComando(sucesso=resposta.sucesso, mensagem=resposta.mensagem, estado=resposta.estado)

    # Detecção de falhas: controláveis via heartbeat gRPC; contínuas pelo tempo sem leitura
    def _verificar(self, info):
        if info.controlavel:
            try:
                resposta = self._stub(info).ObterEstado(ctrl.Vazio(), timeout=config.TIMEOUT_GRPC_S)
                self.registro.atualizar_estado(info.id, estado=resposta.estado, status=self._status_de(resposta.estado))
            except grpc.RpcError:
                self.registro.atualizar_estado(info.id, status=pb.OFFLINE)
        else:
            segundos, intervalo = self.registro.segundos_sem_contato(info.id)
            limite = 3 * intervalo + 2  # tolera perder até ~3 leituras
            self.registro.atualizar_estado(info.id, status=pb.OFFLINE if segundos > limite else pb.ONLINE)

    def _loop_monitor(self):
        while True:
            time.sleep(config.INTERVALO_MONITOR_S)
            for info in self.registro.listar():
                self._verificar(info)

    def iniciar(self):
        threading.Thread(target=self._loop_monitor, daemon=True).start()
