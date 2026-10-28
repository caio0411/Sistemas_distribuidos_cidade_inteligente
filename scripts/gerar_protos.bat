@echo off
REM Gera o codigo Python a partir dos arquivos .proto (saida na pasta "gerado").
REM A fonte em Node.js carrega os .proto diretamente em tempo de execucao (protobufjs).
cd /d %~dp0..
if not exist gerado mkdir gerado
python -m grpc_tools.protoc -I proto --python_out=gerado --grpc_python_out=gerado proto/cidade.proto proto/controle.proto
echo Codigo gerado em .\gerado
