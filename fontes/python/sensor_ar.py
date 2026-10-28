"""Sensor de qualidade do ar (fonte CONTROLÁVEL que gera EVENTOS).

- Comandos via gRPC: limiar de alerta (ppm), intervalo de envio, ligar/desligar, simular falha.
- Envia via UDP a concentração de CO2 (ppm) periodicamente e, IMEDIATAMENTE,
  quando o valor ultrapassa o limiar de alerta.

Uso: python -m fontes.python.sensor_ar --id ar-01 --porta-grpc 40201
"""
import argparse
import random

from fontes.python.fonte_base import FonteBase, pb


class SensorAr(FonteBase):
    tipo = pb.SENSOR_AR
    controlavel = True
    parametros_suportados = {"limiar"}

    def __init__(self, fonte_id, intervalo_envio_s, porta_grpc, limiar):
        super().__init__(fonte_id, intervalo_envio_s, porta_grpc)
        self.estado.limiar_alerta = limiar
        self.co2 = 450.0
        self.acima_do_limiar = False

    def gerar_medidas(self):
        # Passeio aleatório em torno de 450 ppm, com picos ocasionais (ex.: trânsito intenso)
        self.co2 += random.uniform(-15, 15) + (450 - self.co2) * 0.05
        if random.random() < 0.03:
            self.co2 += random.uniform(200, 400)
        self.co2 = max(self.co2, 350)
        return [pb.Medida(grandeza="co2", valor=self.co2, unidade="ppm")]

    def verificar_evento(self, medidas):
        with self.lock:
            limiar = self.estado.limiar_alerta
        acima = medidas[0].valor > limiar
        # Gera evento apenas quando CRUZA o limiar (evita enviar a cada segundo)
        evento = acima and not self.acima_do_limiar
        self.acima_do_limiar = acima
        if evento:
            self.log.warning("ALERTA: CO2 %.0f ppm acima do limiar %.0f ppm", medidas[0].valor, limiar)
        return evento


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sensor de qualidade do ar")
    parser.add_argument("--id", default="ar-01")
    parser.add_argument("--porta-grpc", type=int, default=40201)
    parser.add_argument("--intervalo", type=int, default=5, help="intervalo de envio (s)")
    parser.add_argument("--limiar", type=float, default=700, help="limiar de alerta de CO2 (ppm)")
    args = parser.parse_args()
    SensorAr(args.id, args.intervalo, args.porta_grpc, args.limiar).iniciar()
