"""Servidor TCP que atende os Clientes (CLI e Web).

Cada conexão é atendida por uma thread. O cliente envia RequisicaoCliente e
recebe RespostaCliente, ambas em Protobuf com prefixo de tamanho (ver comum/framing.py).
"""
import logging
import socketserver

from comum import config, framing
import cidade_pb2 as pb
from gateway import consultas

log = logging.getLogger("gateway")


def processar(req, registro, banco, controle):
    tipo = req.WhichOneof("tipo")
    if tipo == "listar":
        return pb.RespostaCliente(lista=pb.ListaFontes(fontes=registro.listar()))
    if tipo == "comando":
        return pb.RespostaCliente(comando=controle.executar_comando(req.comando))
    if tipo == "consulta":
        return pb.RespostaCliente(consulta=consultas.executar_consulta(banco, req.consulta))
    if tipo == "historico":
        return pb.RespostaCliente(historico=consultas.executar_historico(banco, req.historico))
    return pb.RespostaCliente(erro="Requisição inválida")


class ServidorTCP:
    def __init__(self, registro, banco, controle):
        dependencias = (registro, banco, controle)

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                log.info("Cliente conectado: %s:%d", *self.client_address)
                try:
                    while True:
                        req = framing.receber_mensagem(self.request, pb.RequisicaoCliente)
                        framing.enviar_mensagem(self.request, processar(req, *dependencias))
                except (ConnectionError, OSError):
                    log.info("Cliente desconectado: %s:%d", *self.client_address)

        socketserver.ThreadingTCPServer.allow_reuse_address = True
        self.servidor = socketserver.ThreadingTCPServer(("", config.PORTA_TCP_CLIENTES), Handler)
        self.servidor.daemon_threads = True

    def executar(self):
        log.info("Aguardando clientes TCP na porta %d", config.PORTA_TCP_CLIENTES)
        self.servidor.serve_forever()
