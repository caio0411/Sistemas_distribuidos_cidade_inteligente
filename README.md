# Cidade Inteligente: Sistema Distribuído de Monitoramento e Controle

Trabalho 1 de Sistemas Distribuídos. Domínio escolhido: **Cidade Inteligente**.

Um **Gateway urbano** central descobre as fontes de dados da cidade (postes, semáforos, sensores de ar,
sensores de ruído, estações meteorológicas e contadores de tráfego), recebe as leituras, guarda tudo em um banco e permite que **Clientes**
(terminal ou dashboard web) consultem o estado das fontes, enviem comandos e façam consultas analíticas.

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
| Descoberta Gateway → fontes | UDP multicast `224.1.1.1:40000` | `RequisicaoDescoberta` |
| Resposta fonte → Gateway | UDP unicast `:40003` | `AnuncioFonte` (tipo, IP, porta gRPC, estado inicial) |
| Leituras fonte → Gateway | UDP `:40001` | `Leitura` (lista de `Medida` + flag `evento`) |
| Comandos Gateway → fonte | gRPC (serviço `ControleFonte`) | `ValorBool` / `ValorInt` / `ValorDouble` → `RespostaControle` |
| Cliente ↔ Gateway | TCP `:40002` (4 bytes de tamanho + mensagem) | `RequisicaoCliente` → `RespostaCliente` |

## Fontes de dados

| Fonte | Linguagem | Tipo | Envia (UDP) | Comandos (gRPC) |
|---|---|---|---|---|
| Poste de iluminação | Python | Controlável | consumo (W), intensidade (%) | ligar/desligar, intensidade, intervalo, simular falha |
| Sensor de qualidade do ar | Python | Controlável + **evento** | CO₂ (ppm); envia **na hora** ao ultrapassar o limiar | limiar de alerta, intervalo, ligar/desligar, simular falha |
| Semáforo | Python | Controlável | fila de veículos, tempo de ciclo (s) | tempo de ciclo, ligar/desligar, intervalo, simular falha |
| Sensor de ruído | Python | Não controlável + **evento** | ruído (dB); envia **na hora** ao passar de 80 dB | — |
| Estação meteorológica | **Node.js** | Não controlável | temperatura (°C), umidade (%) | — |
| Contador de tráfego | **Node.js** | Não controlável | veículos por minuto | — |

O `iniciar_tudo.bat` sobe 8 fontes: 2 postes, 1 sensor de ar, 1 semáforo, 1 sensor de ruído, 2 estações e 1 contador de tráfego.

## Consultas agregadas (no Cliente)

1. Média de temperatura na última hora
2. Desvio padrão de CO₂ nas últimas 24 h
3. Fonte com maior variação (máx − mín) de temperatura
4. Quantidade de alertas (CO₂ e ruído) por fonte
5. Pico de consumo de energia dos postes
6. Pico de ruído nas últimas 24 h
7. Média do fluxo de veículos na última hora
8. Média da fila nos semáforos na última hora
9. Média de umidade na última hora

Também há a consulta de **histórico** de leituras de uma fonte (persistência em SQLite).

## Detecção de falhas

O Gateway verifica todas as fontes a cada 3 s:
- **Controláveis:** chama `ObterEstado` via gRPC (funciona como heartbeat). Se a chamada falhar, a fonte vira `OFFLINE`; se estiver em falha simulada, `FALHA`; se estiver desligada, `DESLIGADA`.
- **Não controláveis:** se ficar mais de 3 intervalos sem enviar leitura, vira `OFFLINE`.

A descoberta multicast é repetida a cada 10 s. Assim, fontes que sobem depois do Gateway, ou que reiniciam, são encontradas automaticamente.

## Estrutura de pastas

```
proto/            cidade.proto (mensagens) e controle.proto (serviço gRPC)
gerado/           código Python gerado pelo protoc (não editar)
comum/            config.py (portas/endereços), framing.py (TCP), multicast.py
gateway/          main.py, descoberta.py, receptor_udp.py, controle_grpc.py,
                  servidor_tcp.py, consultas.py, registro.py, banco.py
fontes/python/    fonte_base.py, poste.py, sensor_ar.py, semaforo.py, sensor_ruido.py
fontes/node/      fonte_base.js, estacao.js, contador_trafego.js
cliente/          conexao.py (TCP), cli.py (terminal), web/ (dashboard Flask)
scripts/          gerar_protos.bat, iniciar_tudo.bat, parar_tudo.bat
```

## Como executar

### 1. Instalar as dependências (só na primeira vez)

```bash
pip install -r requirements.txt
```

```bash
cd fontes/node && npm install
```

### 2. Gerar o código dos `.proto` (o `iniciar_tudo.bat` já faz isso automaticamente)

```bash
scripts\gerar_protos.bat
```

### 3. Subir tudo de uma vez (Windows)

```bash
scripts\iniciar_tudo.bat
```

Cada processo abre em uma janela. O dashboard fica em **http://localhost:8080**.

Para fechar todas as janelas de uma vez:

```bash
scripts\parar_tudo.bat
```

### Ou subir cada processo manualmente (sempre a partir da raiz do projeto)

```bash
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

## Roteiro sugerido para o vídeo (até 7 min)

1. **(0:00)** Mostrar a estrutura do projeto e os arquivos `.proto`.
2. **(1:00)** Subir o Gateway e depois as fontes. Mostrar no log do Gateway "Nova fonte: …" (descoberta multicast).
3. **(2:00)** Abrir o Cliente CLI e escolher a opção 1 (listar fontes e estados).
4. **(2:30)** Enviar comandos: desligar `poste-02`, mudar a intensidade do `poste-01` para 30% e o tempo de ciclo do `semaforo-01` para 120 s (a fila cresce). Mostrar no log da fonte o `[gRPC]` recebido.
5. **(3:30)** Baixar o limiar do `ar-01` para 400 ppm. A fonte envia um **EVENTO** imediato, que aparece em vermelho no gráfico do dashboard. Os picos do sensor de ruído também geram eventos.
6. **(4:15)** Executar as consultas agregadas e o histórico.
7. **(5:00)** **Falha:** usar "Simular falha" no `poste-01` (status `FALHA`) e depois **fechar a janela** da estação Node.js (status `OFFLINE` em ~15 s). Reabrir a estação e mostrar que ela é redescoberta.
8. **(6:00)** Mostrar o dashboard web (tabela, gráficos e comandos).

## Pontuação extra implementada

- ✅ **Mais de uma linguagem:** Gateway, clientes e 4 tipos de fonte em Python; estação meteorológica e contador de tráfego em Node.js (`protobufjs`).
- ✅ **Persistência:** SQLite (`dados/leituras.db`), com consultas de histórico no Cliente.
- ✅ **Cliente gráfico:** dashboard web com séries temporais (Flask + Chart.js).
- ❌ Fonte real (ESP/Raspberry Pi Pico): não implementada, pois exige hardware.

## Tecnologias

Python 3 (`grpcio`, `protobuf`, `socket`, `socketserver`, `sqlite3`, `Flask`), Node.js (`dgram`, `protobufjs`), Protocol Buffers 3, gRPC e Chart.js.
