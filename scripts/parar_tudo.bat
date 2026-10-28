@echo off
REM Fecha todas as janelas abertas pelo iniciar_tudo.bat (e os processos dentro delas).
for %%J in ("Gateway" "Poste" "Sensor de Ar" "Semaforo" "Ruido" "Estacao" "Trafego" "Dashboard Web" "Cliente CLI") do (
    taskkill /FI "WINDOWTITLE eq %%~J*" /T /F >nul 2>&1
)
echo Todos os processos foram encerrados.
