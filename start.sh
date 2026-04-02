#!/bin/bash
# Inicia API y frontend en segundo plano.
# Los PID se guardan en logs/api.pid y logs/frontend.pid.
# Logs en logs/api.log y logs/frontend.log.

cd "$(dirname "$0")"
mkdir -p logs

# Comprobar si ya hay procesos activos
if [ -f logs/api.pid ] && kill -0 "$(cat logs/api.pid)" 2>/dev/null; then
    echo "[WARN] La API ya esta en marcha (PID $(cat logs/api.pid)). Usa restart.sh para reiniciar."
    exit 1
fi
if [ -f logs/frontend.pid ] && kill -0 "$(cat logs/frontend.pid)" 2>/dev/null; then
    echo "[WARN] El frontend ya esta en marcha (PID $(cat logs/frontend.pid)). Usa restart.sh para reiniciar."
    exit 1
fi

nohup bash run_api.sh > logs/api.log 2>&1 &
echo $! > logs/api.pid
echo "[OK] API iniciada (PID $!) — logs en logs/api.log"

nohup bash run_frontend.sh > logs/frontend.log 2>&1 &
echo $! > logs/frontend.pid
echo "[OK] Frontend iniciado (PID $!) — logs en logs/frontend.log"

echo ""
echo "  API:       http://localhost:8000"
echo "  Dashboard: http://localhost:3000"

# Indicar si VNC estara disponible
if command -v x11vnc &>/dev/null && command -v websockify &>/dev/null; then
    echo "  VNC:       ws://localhost:6080 (panel Chrome remoto activo)"
else
    echo "  VNC:       no disponible (instala x11vnc + websockify para panel Chrome remoto)"
fi
