@echo off
REM Abre cada processo do sistema em uma janela separada.
REM Ordem: Gateway -> fontes -> clientes (qualquer ordem funciona, pois a
REM descoberta multicast e repetida a cada 10 s).
cd /d %~dp0..

REM Gera o codigo Python a partir dos .proto (garante que esta atualizado)
call scripts\gerar_protos.bat
if errorlevel 1 (
    echo Erro ao gerar os protos. Verifique os arquivos .proto.
    pause
    exit /b 1
)

start "Gateway"                cmd /k python -m gateway.main
timeout /t 2 /nobreak >nul

REM Fontes controlaveis (Python + gRPC)
start "Poste 01"               cmd /k python -m fontes.python.poste --id poste-01 --porta-grpc 40101
start "Poste 02"               cmd /k python -m fontes.python.poste --id poste-02 --porta-grpc 40102
start "Sensor de Ar 01"        cmd /k python -m fontes.python.sensor_ar --id ar-01 --porta-grpc 40201 --limiar 700
start "Semaforo 01"            cmd /k python -m fontes.python.semaforo --id semaforo-01 --porta-grpc 40301 --ciclo 60

REM Fontes nao controlaveis (Python e Node.js)
start "Ruido 01"               cmd /k python -m fontes.python.sensor_ruido --id ruido-01 --limite 80
start "Estacao 01 (Node.js)"   cmd /k node fontes\node\estacao.js --id estacao-01 --intervalo 5
start "Estacao 02 (Node.js)"   cmd /k node fontes\node\estacao.js --id estacao-02 --intervalo 5
start "Trafego 01 (Node.js)"   cmd /k node fontes\node\contador_trafego.js --id trafego-01 --intervalo 5

timeout /t 2 /nobreak >nul
start "Dashboard Web"          cmd /k python -m cliente.web.app
start "Cliente CLI"            cmd /k python -m cliente.cli
