# Conexão TCP com o Gateway (usada pelo cliente CLI e pelo Web).
import socket
import threading

from comum import config, framing
import cidade_pb2 as pb


class ClienteGateway:
    def __init__(self, host=config.HOST, porta=config.PORTA_TCP_CLIENTES):
        self.endereco = (host, porta)
        self.sock = None
        self.lock = threading.Lock()  # o cliente Web usa a mesma conexão em várias threads

    def _conectar(self):
        self.sock = socket.create_connection(self.endereco, timeout=10)

    def requisitar(self, requisicao):
        """Envia uma RequisicaoCliente e retorna a RespostaCliente (reconecta se preciso)."""
        with self.lock:
            for tentativa in range(2):
                try:
                    if self.sock is None:
                        self._conectar()
                    framing.enviar_mensagem(self.sock, requisicao)
                    return framing.receber_mensagem(self.sock, pb.RespostaCliente)
                except OSError:
                    self.sock = None
                    if tentativa == 1:
                        raise ConnectionError(f"Gateway indisponível em {self.endereco[0]}:{self.endereco[1]}")

    # ----- atalhos -----
    def listar_fontes(self):
        return self.requisitar(pb.RequisicaoCliente(listar=pb.ListarFontes())).lista.fontes

    def enviar_comando(self, fonte_id, acao, valor=0):
        cmd = pb.ComandoFonte(fonte_id=fonte_id, acao=acao, valor=valor)
        return self.requisitar(pb.RequisicaoCliente(comando=cmd)).comando

    def consultar(self, tipo, grandeza="", janela_minutos=60):
        consulta = pb.ConsultaAgregada(tipo=tipo, grandeza=grandeza, janela_minutos=janela_minutos)
        return self.requisitar(pb.RequisicaoCliente(consulta=consulta)).consulta

    def historico(self, fonte_id="", grandeza="", janela_minutos=60, limite=100):
        consulta = pb.ConsultaHistorico(fonte_id=fonte_id, grandeza=grandeza, janela_minutos=janela_minutos, limite=limite)
        return self.requisitar(pb.RequisicaoCliente(historico=consulta)).historico.pontos
