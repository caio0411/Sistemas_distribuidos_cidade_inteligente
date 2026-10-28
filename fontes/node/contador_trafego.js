// Contador de tráfego (fonte NÃO CONTROLÁVEL) — Node.js.
// Envia periodicamente o fluxo de veículos por minuto ao Gateway via UDP.
//
// Uso: node contador_trafego.js --id trafego-01 --intervalo 5

const { iniciarFonte, argumento } = require("./fonte_base");

const id = argumento("id", "trafego-01");
const intervaloS = parseInt(argumento("intervalo", "5"), 10);
let t = 0;

iniciarFonte({
  id,
  tipo: "CONTADOR_TRAFEGO",
  intervaloS,
  gerarMedidas: () => {
    t += 1;
    // Fluxo oscila entre "horário de pico" e "horário calmo" + variação aleatória
    const veiculos = Math.max(0, 30 + 15 * Math.sin(t / 8) + (Math.random() - 0.5) * 10);
    return [{ grandeza: "veiculos", valor: Math.round(veiculos), unidade: "veíc/min" }];
  },
}).catch((erro) => {
  console.error(erro);
  process.exit(1);
});
