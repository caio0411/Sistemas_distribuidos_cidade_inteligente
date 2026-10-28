"""Cliente Web (dashboard) — pontuação extra.

O navegador não consegue abrir sockets TCP diretamente, então este servidor
Flask funciona como uma "ponte": ele é um Cliente TCP do Gateway (mesmo
protocolo Protobuf do cliente CLI) e expõe uma API HTTP/JSON para a página.

    Navegador --HTTP/JSON--> Flask (app.py) --TCP/Protobuf--> Gateway

Uso: python -m cliente.web.app   (abre em http://localhost:8080)
"""
from flask import Flask, jsonify, request

from cliente.conexao import ClienteGateway
import cidade_pb2 as pb

app = Flask(__name__, static_folder="static")
gateway = ClienteGateway()


def fonte_para_dict(f):
    return {
        "id": f.id,
        "tipo": pb.TipoFonte.Name(f.tipo),
        "ip": f.ip,
        "porta_grpc": f.porta_grpc,
        "controlavel": f.controlavel,
        "status": pb.StatusFonte.Name(f.status),
        "estado": {
            "ligado": f.estado.ligado,
            "intervalo_envio_s": f.estado.intervalo_envio_s,
            "limiar_alerta": f.estado.limiar_alerta,
            "intensidade": f.estado.intensidade,
            "em_falha": f.estado.em_falha,
            "tempo_ciclo_s": f.estado.tempo_ciclo_s,
        },
        "ultima_leitura_ms": f.ultima_leitura_ms,
        "medidas": [{"grandeza": m.grandeza, "valor": m.valor, "unidade": m.unidade} for m in f.ultimas_medidas],
    }


@app.errorhandler(ConnectionError)
def gateway_indisponivel(erro):
    return jsonify({"erro": str(erro)}), 503


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/fontes")
def fontes():
    return jsonify([fonte_para_dict(f) for f in sorted(gateway.listar_fontes(), key=lambda f: f.id)])


@app.route("/api/comando", methods=["POST"])
def comando():
    dados = request.get_json()
    r = gateway.enviar_comando(dados["fonte_id"], pb.AcaoComando.Value(dados["acao"]), float(dados.get("valor", 0)))
    return jsonify({"sucesso": r.sucesso, "mensagem": r.mensagem})


@app.route("/api/consulta")
def consulta():
    r = gateway.consultar(
        pb.TipoConsulta.Value(request.args["tipo"]),
        request.args.get("grandeza", ""),
        int(request.args.get("janela", 60)),
    )
    itens = [{"rotulo": i.rotulo, "valor": i.valor, "amostras": i.amostras} for i in r.itens]
    return jsonify({"descricao": r.descricao, "unidade": r.unidade, "itens": itens})


@app.route("/api/historico")
def historico():
    pontos = gateway.historico(
        fonte_id=request.args.get("fonte_id", ""),
        grandeza=request.args.get("grandeza", ""),
        janela_minutos=int(request.args.get("janela", 15)),
        limite=int(request.args.get("limite", 500)),
    )
    return jsonify([
        {"fonte_id": p.fonte_id, "valor": p.valor, "ts": p.timestamp_ms, "evento": p.evento} for p in pontos
    ])


if __name__ == "__main__":
    print("Dashboard em http://localhost:8080")
    app.run(host="0.0.0.0", port=8080, threaded=True)
