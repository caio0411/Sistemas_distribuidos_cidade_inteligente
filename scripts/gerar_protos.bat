@echo off
REM Gera o codigo Python dos .proto na pasta "gerado" (o Node.js le os .proto direto).
cd /d %~dp0..
if not exist gerado mkdir gerado
python -m grpc_tools.protoc -I proto --python_out=gerado --grpc_python_out=gerado proto/cidade.proto proto/controle.proto
echo Codigo gerado em .\gerado
