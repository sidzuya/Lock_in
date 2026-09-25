#!/usr/bin/env bash
# ==============================================================================
# Настройка Hermes Agent для работы с нашим LiteLLM Proxy
# ==============================================================================

set -e

HERMES_DIR="$HOME/.hermes"
mkdir -p "$HERMES_DIR"

echo "[*] Настройка Hermes Agent..."

# Настройка .env для Hermes
HERMES_ENV="$HERMES_DIR/.env"
if [ ! -f "$HERMES_ENV" ]; then
    touch "$HERMES_ENV"
fi

# Обновляем или добавляем OPENAI_BASE_URL и OPENAI_API_KEY
sed -i '' '/^OPENAI_BASE_URL=/d' "$HERMES_ENV" 2>/dev/null || true
sed -i '' '/^OPENAI_API_KEY=/d' "$HERMES_ENV" 2>/dev/null || true

echo "OPENAI_BASE_URL=http://127.0.0.1:4000/v1" >> "$HERMES_ENV"
echo "OPENAI_API_KEY=sk-litellm-proxy" >> "$HERMES_ENV"

echo "[✓] Hermes Agent .env обновлен: $HERMES_ENV"
echo "    - OPENAI_BASE_URL: http://127.0.0.1:4000/v1"
echo "    - OPENAI_API_KEY: sk-litellm-proxy"
echo ""
echo "[*] Если вы используете hermes CLI, выберите модель:"
echo "    hermes model -> выберите OpenAI-совместимую модель (например, big-pickle)"
