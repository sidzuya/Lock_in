#!/usr/bin/env bash
# ==============================================================================
# Быстрый запуск Pi Coding Agent через наш LiteLLM Proxy
# ==============================================================================

# Проверяем, запущен ли LiteLLM Proxy на порту 4000
PORT=4000
if ! nc -z 127.0.0.1 $PORT 2>/dev/null; then
    echo "[!] LiteLLM Proxy не запущен на порту $PORT!"
    echo "[*] Запустите прокси в соседнем терминале командой: ./start-proxy.sh"
    echo ""
    read -p "Хотите запустить прокси прямо сейчас в фоновом режиме? (y/n): " choice
    if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
        echo "[*] Запускаю ./start-proxy.sh в фоне..."
        nohup ./start-proxy.sh > proxy.log 2>&1 &
        sleep 3
    else
        exit 1
    fi
fi

# Запуск Pi CLI с нашим провайдером и выбранной моделью (по умолчанию big-pickle)
MODEL="${1:-big-pickle}"
shift || true

echo "[*] Запуск Pi Coding Agent (Модель: $MODEL)..."
echo "[*] Для смены модели внутри сессии введите: /model"
echo ""

exec pi --provider opencode-proxy --model "$MODEL" "$@"
