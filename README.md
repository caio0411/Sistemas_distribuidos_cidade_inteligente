# Cidade Inteligente: Sistema Distribuído de Monitoramento e Controle

Trabalho 1 da disciplina de Sistemas Distribuídos (Distribuição de Processos e Dados).

Um **Gateway urbano** descobre as fontes de dados da cidade (postes, semáforos, sensores de qualidade do ar,
sensores de ruído, estações meteorológicas e contadores de tráfego), recebe suas leituras, armazena o histórico
e permite que **Clientes** (terminal ou dashboard web) consultem o estado das fontes, enviem comandos e executem
consultas analíticas agregadas.

## Arquitetura

```
                      ┌───────────── UDP multicast 224.1.1.1:40000 (descoberta) ─────────────┐
                      │                                                                        │
  ┌──────────────┐    │     ┌──────────────────────────────┐   gRPC (comandos)   ┌────────────┴────────────┐
  │ Cliente CLI  │─TCP─────►│           GATEWAY            │────────────────────►│ Controláveis (Python)   │
  └──────────────┘  :40002  │  descoberta │ receptor UDP   │                     │  Poste, Sensor de Ar,   │
  ┌──────────────┐          │  monitor    │ servidor TCP   │◄──── UDP :40001 ────│  Semáforo               │
  │ Dashboard Web│─TCP─────►│  consultas  │ SQLite         │      (leituras)     │ Contínuas               │
  └──────────────┘          └──────────────────────────────┘                     │  Ruído (Python),        │
   (Flask + Chart.js)                                                            │  Estação, Tráfego (Node)│
                                                                                 └─────────────────────────┘
```

| Comunicação | Tecnologia | Mensagens (Protobuf) |
|---|---|---|
| Descoberta Gateway -> fontes | UDP multicast `224.1.1.1:40000` | `RequisicaoDescoberta` |
| Resposta fonte -> Gateway | UDP unicast `:40003` | `AnuncioFonte` (tipo, IP, porta gRPC, estado inicial) |
| Leituras fonte -> Gateway | UDP `:40001` | `Leitura` (lista de `Medida` + flag `evento`) |
| Comandos Gateway -> fonte | gRPC (serviço `ControleFonte`) | `ValorBool` / `ValorInt` / `ValorDouble` → `RespostaControle` |
| Cliente <-> Gateway | TCP `:40002` (4 bytes de tamanho + mensagem) | `RequisicaoCliente` → `RespostaCliente` |

As mensagens estão definidas em [`proto/cidade.proto`](proto/cidade.proto) e o serviço gRPC em
[`proto/controle.proto`](proto/controle.proto).

## Fontes de dados

| Fonte | Linguagem | Tipo | Envia (UDP) | Comandos (gRPC) |
|---|---|---|---|---|
| Poste de iluminação | Python | Controlável | consumo (W), intensidade (%) | ligar/desligar, intensidade, intervalo, simular falha |
| Sensor de qualidade do ar | Python | Controlável + evento | CO₂ (ppm); envio imediato ao ultrapassar o limiar | limiar de alerta, intervalo, ligar/desligar, simular falha |
| Semáforo | Python | Controlável | fila de veículos, tempo de ciclo (s) | tempo de ciclo, intervalo, ligar/desligar, simular falha |
| Sensor de ruído | Python | Não controlável + evento | ruído (dB); envio imediato acima de 80 dB | — |
| Estação meteorológica | Node.js | Não controlável | temperatura (°C), umidade (%) | — |
| Contador de tráfego | Node.js | Não controlável | veículos por minuto | — |

## Consultas agregadas

1. Média de temperatura na última hora
2. Desvio padrão de CO₂ nas últimas 24 h
3. Fonte com maior variação (máx − mín) de temperatura
4. Quantidade de alertas (CO₂ e ruído) por fonte
5. Pico de consumo de energia dos postes
6. Pico de ruído nas últimas 24 h
7. Média do fluxo de veículos na última hora
8. Média da fila nos semáforos na última hora
9. Média de umidade na última hora

As leituras são persistidas em SQLite (`dados/leituras.db`), e o cliente também pode consultar o **histórico** de uma fonte.

## Detecção de falhas

O Gateway verifica todas as fontes a cada 3 s:
- **Controláveis:** chamada gRPC `ObterEstado` (heartbeat). Falhou → `OFFLINE`; falha simulada → `FALHA`; desligada → `DESLIGADA`.
- **Não controláveis:** mais de 3 intervalos sem enviar leitura → `OFFLINE`.

A descoberta multicast é repetida a cada 10 s, então fontes que sobem depois do Gateway, ou que reiniciam, são encontradas automaticamente.

## Estrutura de pastas

```
proto/            cidade.proto (mensagens) e controle.proto (serviço gRPC)
gerado/           código Python gerado pelo protoc
comum/            config.py (portas/endereços), framing.py (TCP), multicast.py
gateway/          main.py, descoberta.py, receptor_udp.py, controle_grpc.py,
                  servidor_tcp.py, consultas.py, registro.py, banco.py
fontes/python/    fonte_base.py, poste.py, sensor_ar.py, semaforo.py, sensor_ruido.py
fontes/node/      fonte_base.js, estacao.js, contador_trafego.js
cliente/          conexao.py (TCP), cli.py (terminal), web/ (dashboard Flask)
scripts/          gerar_protos.bat, iniciar_tudo.bat, parar_tudo.bat
```

## Como executar

Requisitos: Python 3.10+ e Node.js 18+.

### 1. Instalar as dependências

```bash
pip install -r requirements.txt
```

```bash
cd fontes/node && npm install
```

### 2. Subir tudo de uma vez (Windows)

```bash
scripts\iniciar_tudo.bat
```

O script gera o código dos `.proto` e abre cada processo em uma janela: o Gateway, 8 fontes
(2 postes, 1 sensor de ar, 1 semáforo, 1 sensor de ruído, 2 estações e 1 contador de tráfego),
o cliente CLI e o dashboard web em **http://localhost:8080**.

Para encerrar todos os processos:

```bash
scripts\parar_tudo.bat
```

### Ou subir cada processo manualmente (a partir da raiz do projeto)

```bash
python -m grpc_tools.protoc -I proto --python_out=gerado --grpc_python_out=gerado proto/cidade.proto proto/controle.proto
python -m gateway.main
python -m fontes.python.poste --id poste-01 --porta-grpc 40101
python -m fontes.python.poste --id poste-02 --porta-grpc 40102
python -m fontes.python.sensor_ar --id ar-01 --porta-grpc 40201 --limiar 700
python -m fontes.python.semaforo --id semaforo-01 --porta-grpc 40301 --ciclo 60
python -m fontes.python.sensor_ruido --id ruido-01 --limite 80
node fontes/node/estacao.js --id estacao-01 --intervalo 5
node fontes/node/estacao.js --id estacao-02 --intervalo 5
node fontes/node/contador_trafego.js --id trafego-01 --intervalo 5
python -m cliente.cli
python -m cliente.web.app
```

Para rodar em várias máquinas, defina `SD_HOST` com o IP de cada uma (ex.: `set SD_HOST=192.168.0.10`).

## Tecnologias

- **Python 3:** `grpcio`, `protobuf`, `socket`, `socketserver`, `sqlite3`, `Flask`
- **Node.js:** `dgram`, `protobufjs`
- **Protocol Buffers 3** e **gRPC**
- **Chart.js** no dashboard web
