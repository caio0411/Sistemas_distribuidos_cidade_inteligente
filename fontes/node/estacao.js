// Estação meteorológica (fonte NÃO CONTROLÁVEL) — Node.js.
// Envia periodicamente temperatura (°C) e umidade (%) ao Gateway via UDP.
//
// Uso: node estacao.js --id estacao-01 --intervalo 5

const { iniciarFonte, argumento } = require("./fonte_base");

const id = argumento("id", "estacao-01");
const intervaloS = parseInt(argumento("intervalo", "5"), 10);

// Cada estação tem um microclima um pouco diferente (deslocamento aleatório)
const deslocamento = (Math.random() - 0.5) * 6;
let t = 0;

iniciarFonte({
  id,
  tipo: "ESTACAO_METEOROLOGICA",
  intervaloS,
  gerarMedidas: () => {
    t += 1;
    // Temperatura oscila suavemente ao longo do "dia" + ruído
    const temperatura = 25 + deslocamento + 4 * Math.sin(t / 10) + (Math.random() - 0.5);
    const umidade = 60 - deslocamento - 10 * Math.sin(t / 10) + (Math.random() - 0.5) * 2;
    return [
      { grandeza: "temperatura", valor: temperatura, unidade: "°C" },
      { grandeza: "umidade", valor: umidade, unidade: "%" },
    ];
  },
}).catch((erro) => {
  console.error(erro);
  process.exit(1);
});
