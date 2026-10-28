"""Consultas analíticas agregadas sobre as leituras persistidas."""
import statistics
from collections import defaultdict

from comum import config  # noqa: F401  (ajusta o sys.path)
import cidade_pb2 as pb
from gateway.registro import agora_ms


def _agrupar_por_fonte(linhas):
    grupos = defaultdict(list)
    for fonte_id, valor, _ in linhas:
        grupos[fonte_id].append(valor)
    return grupos


def executar_consulta(banco, consulta):
    janela = consulta.janela_minutos or 60
    desde = agora_ms() - janela * 60 * 1000
    grandeza = consulta.grandeza
    texto_janela = f"nos últimos {janela} min"
    resultado = pb.ResultadoConsulta()

    if consulta.tipo == pb.CONTAGEM_ALERTAS:
        resultado.descricao = f"Quantidade de alertas (eventos) por fonte {texto_janela}"
        resultado.unidade = "alertas"
        for fonte_id, qtd in banco.contar_eventos(desde):
            resultado.itens.add(rotulo=fonte_id, valor=qtd, amostras=qtd)
        return resultado

    linhas = banco.buscar_valores(grandeza, desde)
    resultado.unidade = linhas[0][2] if linhas else ""
    if not linhas:
        resultado.descricao = f"Sem leituras de '{grandeza}' {texto_janela}"
        return resultado
    valores = [v for _, v, _ in linhas]
    grupos = _agrupar_por_fonte(linhas)

    if consulta.tipo == pb.MEDIA:
        resultado.descricao = f"Média de {grandeza} {texto_janela}"
        resultado.itens.add(rotulo="geral", valor=statistics.mean(valores), amostras=len(valores))
        for fonte_id, vs in grupos.items():
            resultado.itens.add(rotulo=fonte_id, valor=statistics.mean(vs), amostras=len(vs))

    elif consulta.tipo == pb.DESVIO_PADRAO:
        resultado.descricao = f"Desvio padrão de {grandeza} {texto_janela}"
        resultado.itens.add(rotulo="geral", valor=statistics.pstdev(valores), amostras=len(valores))
        for fonte_id, vs in grupos.items():
            resultado.itens.add(rotulo=fonte_id, valor=statistics.pstdev(vs), amostras=len(vs))

    elif consulta.tipo == pb.MAIOR_VARIACAO:
        resultado.descricao = f"Fontes ordenadas pela variação (máx - mín) de {grandeza} {texto_janela}"
        variacoes = sorted(((max(vs) - min(vs), fonte_id, len(vs)) for fonte_id, vs in grupos.items()), reverse=True)
        for variacao, fonte_id, n in variacoes:
            resultado.itens.add(rotulo=fonte_id, valor=variacao, amostras=n)

    elif consulta.tipo == pb.PICO:
        resultado.descricao = f"Pico (maior valor) de {grandeza} {texto_janela}"
        fonte_id, valor, _ = max(linhas, key=lambda linha: linha[1])
        resultado.itens.add(rotulo=fonte_id, valor=valor, amostras=len(valores))

    else:
        resultado.descricao = "Tipo de consulta desconhecido"
    return resultado


def executar_historico(banco, consulta):
    janela = consulta.janela_minutos or 60
    limite = consulta.limite or 100
    desde = agora_ms() - janela * 60 * 1000
    resultado = pb.ResultadoHistorico()
    for fonte_id, grandeza, valor, ts, evento in banco.historico(consulta.fonte_id, consulta.grandeza, desde, limite):
        resultado.pontos.add(fonte_id=fonte_id, grandeza=grandeza, valor=valor, timestamp_ms=ts, evento=bool(evento))
    return resultado
