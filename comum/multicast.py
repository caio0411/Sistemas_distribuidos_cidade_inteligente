# Sockets UDP multicast (descoberta).
import socket
import struct

from comum import config


def criar_socket_receptor_multicast():
    """Socket que escuta o grupo multicast (usado pelas fontes)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Permite que várias fontes na mesma máquina escutem a mesma porta
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", config.PORTA_MULTICAST))
    mreq = struct.pack("4s4s", socket.inet_aton(config.GRUPO_MULTICAST), socket.inet_aton("0.0.0.0"))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return sock


def configurar_envio_multicast(sock):
    """Configura um socket UDP para enviar ao grupo multicast (usado pelo Gateway)."""
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
