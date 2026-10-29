// Base das fontes Node.js: descoberta multicast e envio periódico de leituras via UDP.

const dgram = require("dgram");
const path = require("path");
const protobuf = require("protobufjs");

const GRUPO_MULTICAST = "224.1.1.1";
const PORTA_MULTICAST = 40000;
const HOST = process.env.SD_HOST || "127.0.0.1";

// Argumentos de linha de comando simples: --nome valor
function argumento(nome, padrao) {
  const i = process.argv.indexOf(`--${nome}`);
  return i >= 0 ? process.argv[i + 1] : padrao;
}

// tipo: nome do enum TipoFonte (ex.: "ESTACAO_METEOROLOGICA")
// gerarMedidas: função que retorna [{ grandeza, valor, unidade }, ...]
async function iniciarFonte({ id, tipo, intervaloS, gerarMedidas }) {
  const log = (msg) => console.log(`${new Date().toLocaleTimeString("pt-BR")} [${id}] ${msg}`);

  const root = await protobuf.load(path.join(__dirname, "..", "..", "proto", "cidade.proto"));
  const RequisicaoDescoberta = root.lookupType("cidade.RequisicaoDescoberta");
  const AnuncioFonte = root.lookupType("cidade.AnuncioFonte");
  const Leitura = root.lookupType("cidade.Leitura");
  const TipoFonte = root.lookupEnum("cidade.TipoFonte").values;

  const socketEnvio = dgram.createSocket("udp4");
  let gateway = null; // { ip, porta } conhecido após a descoberta

  // ----- Descoberta (multicast) -----
  const socketMulticast = dgram.createSocket({ type: "udp4", reuseAddr: true });
  socketMulticast.on("message", (dados) => {
    const req = RequisicaoDescoberta.decode(dados);
    const novo = !gateway || gateway.ip !== req.gatewayIp || gateway.porta !== req.portaDadosUdp;
    gateway = { ip: req.gatewayIp, porta: req.portaDadosUdp };

    const anuncio = AnuncioFonte.create({
      id,
      tipo: TipoFonte[tipo],
      ip: HOST,
      portaGrpc: 0, // não controlável: não tem servidor gRPC
      controlavel: false,
      intervaloEnvioS: intervaloS,
      estadoInicial: { ligado: true, intervaloEnvioS: intervaloS },
    });
    socketEnvio.send(AnuncioFonte.encode(anuncio).finish(), req.portaDescoberta, req.gatewayIp);
    if (novo) log(`Descoberta pelo Gateway ${req.gatewayIp} -> anúncio enviado`);
  });
  socketMulticast.bind(PORTA_MULTICAST, () => {
    socketMulticast.addMembership(GRUPO_MULTICAST);
    log(`Aguardando descoberta em ${GRUPO_MULTICAST}:${PORTA_MULTICAST}`);
  });

  // ----- Envio periódico de leituras (UDP) -----
  setInterval(() => {
    if (!gateway) return;
    const medidas = gerarMedidas();
    const leitura = Leitura.create({ fonteId: id, tipo: TipoFonte[tipo], timestampMs: Date.now(), medidas, evento: false });
    socketEnvio.send(Leitura.encode(leitura).finish(), gateway.porta, gateway.ip);
    log(`Leitura -> ${medidas.map((m) => `${m.grandeza}=${m.valor.toFixed(1)}${m.unidade}`).join(", ")}`);
  }, intervaloS * 1000);

  log(`Iniciando fonte (tipo=${tipo}, controlável=false)`);
}

module.exports = { iniciarFonte, argumento };
