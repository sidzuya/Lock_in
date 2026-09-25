#!/usr/bin/env bash
# ==============================================================================
# Скрипт запуска OpenCode Unlimited Proxy
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Проверка наличия venv
if [ ! -d "venv" ]; then
    echo "[!] Виртуальное окружение venv не найдено. Создаю..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install fastapi uvicorn httpx python-dotenv pyyaml
fi

# Проверка наличия .env
if [ ! -f ".env" ]; then
    echo "[!] Файл .env не найден. Создаю копию из .env.example..."
    cp .env.example .env
    echo "[!] Пожалуйста, вставьте ваши API-ключи от OpenCode в файл .env и перезапустите скрипт."
    exit 1
fi

# Автоматическая настройка моделей для Pi Coding Agent (~/.pi/agent/models.json)
if [ -f "generate_config.py" ]; then
    ./venv/bin/python generate_config.py --setup-pi >/dev/null 2>&1 || true
fi

# Порт
PORT=4000
if grep -q "PROXY_PORT=" .env; then
    PORT=$(grep "^PROXY_PORT=" .env | cut -d '=' -f2 | tr -d ' "')
fi

# Завершаем старый процесс на этом порту, если он есть
PID_EXISTING=$(lsof -ti :$PORT || true)
if [ -n "$PID_EXISTING" ]; then
    echo "[*] Завершаю старый процесс на порту $PORT (PID: $PID_EXISTING)..."
    kill -9 $PID_EXISTING 2>/dev/null || true
    sleep 1
fi

echo ""
echo "======================================================================"
echo " 🚀 Запуск OpenCode Unlimited Smart Proxy на http://127.0.0.1:${PORT}"
echo " 🛡️ Обход 403 FreeTierError: ВКЛЮЧЁН (официальные сигнатуры OpenCode)"
echo " 🔄 Авто-ротация и кулдаун ключей при 429: АКТИВИРОВАНЫ"
echo " 🥒 Модель по умолчанию: big-pickle"
echo "======================================================================"
echo ""

exec ./venv/bin/python proxy.py "$PORT"
