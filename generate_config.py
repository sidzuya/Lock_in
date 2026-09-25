#!/usr/bin/env python3
"""
Генератор конфигурации LiteLLM Proxy и Pi Coding Agent на основе .env
Автоматически считывает все ключи OPENCODE_KEY_* и распределяет их по моделям.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from dotenv import dotenv_values

WORKSPACE_DIR = Path(__file__).resolve().parent
ENV_FILE = WORKSPACE_DIR / ".env"
CONFIG_FILE = WORKSPACE_DIR / "litellm_config.yaml"
PI_CONFIG_DIR = Path.home() / ".pi" / "agent"
PI_MODELS_FILE = PI_CONFIG_DIR / "models.json"

MODELS_SPEC = [
    {
        "id": "big-pickle",
        "alias": "litellm/big-pickle",
        "upstream_model": "openai/big-pickle",
        "name": "Big Pickle (OpenCode Unlimited)",
        "context_window": 128000,
        "max_tokens": 8192,
        "description": "Основной кодинг-агент (быстрый, точный кодинг)",
    },
    {
        "id": "deepseek-v4-flash-free",
        "alias": "litellm/deepseek-v4-flash-free",
        "upstream_model": "openai/deepseek-v4-flash-free",
        "name": "DeepSeek V4 Flash Free (OpenCode Unlimited)",
        "context_window": 64000,
        "max_tokens": 8192,
        "description": "Архитектура, проектирование и глубокое рассуждение",
    },
    {
        "id": "nemotron-3-super-free",
        "alias": "litellm/nemotron-3-super-free",
        "upstream_model": "openai/nemotron-3-super-free",
        "name": "Nemotron 3 Super Free (OpenCode Unlimited)",
        "context_window": 128000,
        "max_tokens": 8192,
        "description": "Большие документы, документация и массивный контекст",
    },
]


def load_keys():
    if not ENV_FILE.exists():
        print(f"[!] Файл .env не найден в {ENV_FILE}. Создайте его на основе .env.example.")
        return []

    env_vars = dotenv_values(ENV_FILE)
    keys = []
    for k, v in sorted(env_vars.items()):
        if k.startswith("OPENCODE_KEY_") and v:
            clean_v = v.strip().strip("'").strip('"')
            if clean_v and clean_v != "sk-" and len(clean_v) > 5:
                keys.append((k, clean_v))

    return keys


def generate_litellm_config(keys):
    model_list = []

    # Если ключей нет, используем заглушки для демонстрации
    active_keys = keys if keys else [("OPENCODE_KEY_DEMO", "sk-placeholder-add-keys-to-env")]

    for m in MODELS_SPEC:
        # Добавляем для каждого аккаунта запись модели (для id и для alias)
        for name_variant in [m["id"], m["alias"]]:
            for key_name, key_val in active_keys:
                model_list.append({
                    "model_name": name_variant,
                    "litellm_params": {
                        "model": m["upstream_model"],
                        "api_base": "https://opencode.ai/zen/v1",
                        "api_key": key_val,
                        "timeout": 120,
                    }
                })

    config = {
        "model_list": model_list,
        "litellm_settings": {
            "drop_params": True,
            "set_verbose": False,
        },
        "router_settings": {
            # simple-shuffle + cooldown обеспечивает мгновенное переключение при 429
            "routing_strategy": "simple-shuffle",
            "num_retries": max(5, len(active_keys) * 2),
            "allowed_fails": 1,
            "cooldown_time": 60,
            "retry_after": 5,
        }
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"[✓] Конфиг LiteLLM сгенерирован: {CONFIG_FILE}")
    print(f"    - Активных ключей OpenCode: {len(keys)}")
    print(f"    - Моделей в пуле: {len(MODELS_SPEC)}")
    if not keys:
        print("[!] ВНИМАНИЕ: В .env пока нет заполненных ключей OPENCODE_KEY_*. Вставьте их для работы!")


def configure_pi_agent(proxy_url="http://127.0.0.1:4000/v1"):
    PI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current_data = {}
    if PI_MODELS_FILE.exists():
        try:
            with open(PI_MODELS_FILE, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except Exception:
            current_data = {}

    providers = current_data.get("providers", {})

    models_config = []
    for m in MODELS_SPEC:
        models_config.append({
            "id": m["id"],
            "name": m["name"],
            "reasoning": False,
            "contextWindow": m["context_window"],
            "maxTokens": m["max_tokens"],
        })

    providers["opencode-proxy"] = {
        "baseUrl": proxy_url,
        "api": "openai-completions",
        "apiKey": "sk-litellm-dummy",
        "compat": {
            "supportsDeveloperRole": False,
            "supportsReasoningEffort": False
        },
        "models": models_config
    }

    current_data["providers"] = providers

    with open(PI_MODELS_FILE, "w", encoding="utf-8") as f:
        json.dump(current_data, f, indent=2, ensure_ascii=False)

    print(f"[✓] Pi Coding Agent настроен: {PI_MODELS_FILE}")
    print("    - Добавлен провайдер: opencode-proxy")
    print("    - Доступные модели: " + ", ".join(m["id"] for m in MODELS_SPEC))


def main():
    keys = load_keys()
    generate_litellm_config(keys)
    if "--setup-pi" in sys.argv or True:
        configure_pi_agent()


if __name__ == "__main__":
    main()
