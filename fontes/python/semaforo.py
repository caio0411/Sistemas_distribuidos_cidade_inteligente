# Semáforo (controlável): envia a fila de veículos; comando de tempo de ciclo.
import argparse
import random

from fontes.python.fonte_base import FonteBase, pb

CHEGADA_MEDIA = 0.6  # veículos que chegam por segundo
VAZAO_VERDE = 1.5    # veículos que passam por segundo no verde


class Semaforo(FonteBase):
    tipo = pb.SEMAFORO
    controlavel = True
    parametros_suportados = {"tempo_ciclo"}

    def __init__(self, fonte_id, intervalo_envio_s, porta_grpc, tempo_ciclo):
        super().__init__(fonte_id, intervalo_envio_s, porta_grpc)
        self.estado.tempo_ciclo_s = tempo_ciclo
        self.segundo_do_ciclo = 0
        self.fila = 0.0

    def gerar_medidas(self):
        # Chamado a cada segundo: avança a simulação um passo
        with self.lock:
            ciclo = self.estado.tempo_ciclo_s
        self.segundo_do_ciclo = (self.segundo_do_ciclo + 1) % ciclo
        verde = self.segundo_do_ciclo < ciclo / 2
        self.fila += random.uniform(0, 2 * CHEGADA_MEDIA)
        if verde:
            self.fila = max(self.fila - VAZAO_VERDE, 0)
        return [
            pb.Medida(grandeza="fila", valor=round(self.fila), unidade="veículos"),
            pb.Medida(grandeza="tempo_ciclo", valor=ciclo, unidade="s"),
        ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semáforo")
    parser.add_argument("--id", default="semaforo-01")
    parser.add_argument("--porta-grpc", type=int, default=40301)
    parser.add_argument("--intervalo", type=int, default=5, help="intervalo de envio (s)")
    parser.add_argument("--ciclo", type=int, default=60, help="tempo de ciclo verde+vermelho (s)")
    args = parser.parse_args()
    Semaforo(args.id, args.intervalo, args.porta_grpc, args.ciclo).iniciar()
