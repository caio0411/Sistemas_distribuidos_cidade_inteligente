"""Sensor de ruído urbano (fonte NÃO CONTROLÁVEL que gera EVENTOS).

- Não tem servidor gRPC: só participa da descoberta e envia dados.
- Envia via UDP o nível sonoro (dB) periodicamente e, IMEDIATAMENTE,
  quando o ruído ultrapassa um limite fixo (ex.: buzina, obra, show).

Uso: python -m fontes.python.sensor_ruido --id ruido-01 --limite 80
"""
import argparse
import random

from fontes.python.fonte_base import FonteBase, pb


class SensorRuido(FonteBase):
    tipo = pb.SENSOR_RUIDO
    controlavel = False

    def __init__(self, fonte_id, intervalo_envio_s, limite_db):
        super().__init__(fonte_id, intervalo_envio_s)
        self.limite_db = limite_db
        self.acima_do_limite = False

    def gerar_medidas(self):
        ruido = random.gauss(62, 4)
        if random.random() < 0.04:
            ruido = random.uniform(82, 98)  # pico sonoro
        return [pb.Medida(grandeza="ruido", valor=ruido, unidade="dB")]

    def verificar_evento(self, medidas):
        acima = medidas[0].valor > self.limite_db
        # Gera evento apenas quando CRUZA o limite (evita enviar a cada segundo)
        evento = acima and not self.acima_do_limite
        self.acima_do_limite = acima
        if evento:
            self.log.warning("ALERTA: ruído %.0f dB acima do limite %.0f dB", medidas[0].valor, self.limite_db)
        return evento


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sensor de ruído")
    parser.add_argument("--id", default="ruido-01")
    parser.add_argument("--intervalo", type=int, default=5, help="intervalo de envio (s)")
    parser.add_argument("--limite", type=float, default=80, help="limite de ruído para alerta (dB)")
    args = parser.parse_args()
    SensorRuido(args.id, args.intervalo, args.limite).iniciar()
