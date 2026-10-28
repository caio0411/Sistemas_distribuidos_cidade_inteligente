"""Poste de iluminação inteligente (fonte CONTROLÁVEL).

- Comandos via gRPC: ligar/desligar, intensidade (0-100 %), intervalo de envio, simular falha.
- Envia via UDP o consumo de energia (W), proporcional à intensidade.

Uso: python -m fontes.python.poste --id poste-01 --porta-grpc 40101
"""
import argparse
import random

from fontes.python.fonte_base import FonteBase, pb

POTENCIA_MAXIMA_W = 150.0


class Poste(FonteBase):
    tipo = pb.POSTE_ILUMINACAO
    controlavel = True
    parametros_suportados = {"intensidade"}

    def __init__(self, fonte_id, intervalo_envio_s, porta_grpc):
        super().__init__(fonte_id, intervalo_envio_s, porta_grpc)
        self.estado.intensidade = 80

    def gerar_medidas(self):
        with self.lock:
            intensidade = self.estado.intensidade
        consumo = POTENCIA_MAXIMA_W * intensidade / 100 + random.uniform(-3, 3)
        return [
            pb.Medida(grandeza="consumo", valor=max(consumo, 0), unidade="W"),
            pb.Medida(grandeza="intensidade", valor=intensidade, unidade="%"),
        ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Poste de iluminação")
    parser.add_argument("--id", default="poste-01")
    parser.add_argument("--porta-grpc", type=int, default=40101)
    parser.add_argument("--intervalo", type=int, default=5, help="intervalo de envio (s)")
    args = parser.parse_args()
    Poste(args.id, args.intervalo, args.porta_grpc).iniciar()
