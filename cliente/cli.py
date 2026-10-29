# Cliente de linha de comando.
from datetime import datetime

from cliente.conexao import ClienteGateway
import cidade_pb2 as pb

NOMES_TIPO = {
    pb.POSTE_ILUMINACAO: "Poste de iluminação",
    pb.SENSOR_AR: "Sensor de qualidade do ar",
    pb.ESTACAO_METEOROLOGICA: "Estação meteorológica",
    pb.SEMAFORO: "Semáforo",
    pb.CONTADOR_TRAFEGO: "Contador de tráfego",
    pb.SENSOR_RUIDO: "Sensor de ruído",
}

# Consultas agregadas oferecidas no menu: (descrição, tipo, grandeza, janela em minutos)
CONSULTAS = [
    ("Média de temperatura na última hora", pb.MEDIA, "temperatura", 60),
    ("Desvio padrão de CO2 nas últimas 24 h", pb.DESVIO_PADRAO, "co2", 24 * 60),
    ("Fonte com maior variação de temperatura na última hora", pb.MAIOR_VARIACAO, "temperatura", 60),
    ("Quantidade de alertas (CO2 e ruído) por fonte nas últimas 24 h", pb.CONTAGEM_ALERTAS, "", 24 * 60),
    ("Pico de consumo de energia dos postes nas últimas 24 h", pb.PICO, "consumo", 24 * 60),
    ("Pico de ruído nas últimas 24 h", pb.PICO, "ruido", 24 * 60),
    ("Média do fluxo de veículos na última hora", pb.MEDIA, "veiculos", 60),
    ("Média da fila nos semáforos na última hora", pb.MEDIA, "fila", 60),
    ("Média de umidade na última hora", pb.MEDIA, "umidade", 60),
]


def formatar_fonte(f):
    estado = f.estado
    detalhes = [f"ligado={'sim' if estado.ligado else 'não'}", f"intervalo={estado.intervalo_envio_s}s"]
    if f.tipo == pb.POSTE_ILUMINACAO:
        detalhes.append(f"intensidade={estado.intensidade}%")
    if f.tipo == pb.SENSOR_AR:
        detalhes.append(f"limiar={estado.limiar_alerta:.0f}ppm")
    if f.tipo == pb.SEMAFORO:
        detalhes.append(f"ciclo={estado.tempo_ciclo_s}s")
    medidas = ", ".join(f"{m.grandeza}={m.valor:.1f}{m.unidade}" for m in f.ultimas_medidas) or "-"
    endereco = f"{f.ip}:{f.porta_grpc}" if f.controlavel else f.ip
    return (
        f"  [{pb.StatusFonte.Name(f.status):9}] {f.id:12} {NOMES_TIPO.get(f.tipo, '?')} ({endereco})\n"
        f"              {'controlável' if f.controlavel else 'não controlável'} | {' | '.join(detalhes)}\n"
        f"              última leitura: {medidas}"
    )


def listar(cliente):
    fontes = cliente.listar_fontes()
    if not fontes:
        print("Nenhuma fonte descoberta ainda.")
    for f in sorted(fontes, key=lambda x: x.id):
        print(formatar_fonte(f))


def escolher_fonte(cliente, somente_controlaveis=True):
    fontes = [f for f in cliente.listar_fontes() if f.controlavel or not somente_controlaveis]
    if not fontes:
        print("Nenhuma fonte controlável disponível.")
        return None
    for i, f in enumerate(sorted(fontes, key=lambda x: x.id), 1):
        print(f"  {i}. {f.id} ({NOMES_TIPO.get(f.tipo)}) [{pb.StatusFonte.Name(f.status)}]")
    opcao = input("Número da fonte: ").strip()
    if not opcao.isdigit() or not 1 <= int(opcao) <= len(fontes):
        print("Opção inválida.")
        return None
    return sorted(fontes, key=lambda x: x.id)[int(opcao) - 1].id


def comando(cliente, acao, pedir_valor=None):
    fonte_id = escolher_fonte(cliente)
    if fonte_id is None:
        return
    valor = 0
    if pedir_valor:
        try:
            valor = float(input(pedir_valor))
        except ValueError:
            print("Valor inválido.")
            return
    r = cliente.enviar_comando(fonte_id, acao, valor)
    print(("OK: " if r.sucesso else "ERRO: ") + r.mensagem)


def consultas(cliente):
    for i, (descricao, *_rest) in enumerate(CONSULTAS, 1):
        print(f"  {i}. {descricao}")
    opcao = input("Consulta: ").strip()
    if not opcao.isdigit() or not 1 <= int(opcao) <= len(CONSULTAS):
        print("Opção inválida.")
        return
    _, tipo, grandeza, janela = CONSULTAS[int(opcao) - 1]
    r = cliente.consultar(tipo, grandeza, janela)
    print(f"\n{r.descricao}")
    for item in r.itens:
        print(f"  {item.rotulo:12} {item.valor:10.2f} {r.unidade:6} ({item.amostras} amostras)")
    if not r.itens:
        print("  (sem dados)")


def historico(cliente):
    fonte_id = escolher_fonte(cliente, somente_controlaveis=False)
    if fonte_id is None:
        return
    pontos = cliente.historico(fonte_id=fonte_id, janela_minutos=24 * 60, limite=20)
    print(f"\nÚltimas {len(pontos)} leituras de {fonte_id}:")
    for p in pontos:
        hora = datetime.fromtimestamp(p.timestamp_ms / 1000).strftime("%d/%m %H:%M:%S")
        print(f"  {hora}  {p.grandeza:12} {p.valor:10.2f}{'  <- EVENTO' if p.evento else ''}")


def alternar_ligado(cliente):
    print("  1. Ligar\n  2. Desligar")
    acao = pb.LIGAR if input("Opção: ").strip() == "1" else pb.DESLIGAR
    comando(cliente, acao)


def falha(cliente):
    print("  1. Simular falha\n  2. Recuperar da falha")
    acao = pb.SIMULAR_FALHA if input("Opção: ").strip() == "1" else pb.RECUPERAR_FALHA
    comando(cliente, acao)


MENU = [
    ("Listar fontes e estados", listar),
    ("Ligar / desligar fonte", alternar_ligado),
    ("Alterar frequência de envio", lambda c: comando(c, pb.DEFINIR_INTERVALO, "Novo intervalo (s): ")),
    ("Alterar limiar de alerta (sensor de ar)", lambda c: comando(c, pb.DEFINIR_LIMIAR, "Novo limiar (ppm): ")),
    ("Alterar intensidade (poste)", lambda c: comando(c, pb.DEFINIR_INTENSIDADE, "Nova intensidade (0-100): ")),
    ("Alterar tempo de ciclo (semáforo)", lambda c: comando(c, pb.DEFINIR_TEMPO_CICLO, "Novo tempo de ciclo (10-300 s): ")),
    ("Simular / recuperar falha", falha),
    ("Consultas agregadas", consultas),
    ("Histórico de leituras de uma fonte", historico),
]


def main():
    cliente = ClienteGateway()
    print("=== Cidade Inteligente - Cliente ===")
    while True:
        print()
        for i, (descricao, _) in enumerate(MENU, 1):
            print(f"{i}. {descricao}")
        print("0. Sair")
        opcao = input("> ").strip()
        if opcao == "0":
            break
        if not opcao.isdigit() or not 1 <= int(opcao) <= len(MENU):
            continue
        print()
        try:
            MENU[int(opcao) - 1][1](cliente)
        except ConnectionError as erro:
            print(f"ERRO: {erro}")


if __name__ == "__main__":
    main()
