"""Envio/recebimento de mensagens Protobuf sobre TCP.

TCP é um fluxo de bytes (não tem "mensagens"), então cada mensagem é enviada
com um cabeçalho de 4 bytes (big-endian) indicando o seu tamanho:

    [ tamanho (4 bytes) ][ bytes da mensagem protobuf ]
"""
import struct


def enviar_mensagem(sock, mensagem):
    dados = mensagem.SerializeToString()
    sock.sendall(struct.pack(">I", len(dados)) + dados)


def _receber_exato(sock, n):
    buffer = b""
    while len(buffer) < n:
        parte = sock.recv(n - len(buffer))
        if not parte:
            raise ConnectionError("conexão fechada")
        buffer += parte
    return buffer


def receber_mensagem(sock, tipo_mensagem):
    (tamanho,) = struct.unpack(">I", _receber_exato(sock, 4))
    mensagem = tipo_mensagem()
    mensagem.ParseFromString(_receber_exato(sock, tamanho))
    return mensagem
