#!/usr/bin/env python3
"""
Скрипт валидации ключей OpenCode.
Проверяет каждый ключ из .env на валидность через эндпоинт авторизации OpenCode.
"""

import sys
import json
import urllib.request
import urllib.error
from dotenv import dotenv_values
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent
ENV_FILE = WORKSPACE_DIR / ".env"

OPENCODE_MODELS_URL = "https://opencode.ai/zen/v1/models"


def test_key(key_name, api_key):
    masked = f"{api_key[:10]}...{api_key[-6:]}" if len(api_key) > 16 else api_key
    print(f"[*] Проверка {key_name} ({masked}): ", end="", flush=True)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "opencode/1.18.31",
    }

    req = urllib.request.Request(OPENCODE_MODELS_URL, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models_count = len(data.get("data", []))
                print(f"✅ АКТИВЕН И ВАЛИДЕН! (Доступно моделей: {models_count})")
                return True
            else:
                print(f"⚠️  Статус {resp.status}")
                return False
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"❌ ОШИБКА АВТОРИЗАЦИИ (Код {e.code}): Неверный API-ключ или аккаунт заблокирован.")
        elif e.code == 429:
            print(f"⚠️  ЛИМИТ ЗАПРОСОВ (Код 429): Аккаунт на кулдауне.")
        else:
            print(f"❌ ОШИБКА (Код {e.code}): {e.reason}")
        return False
    except Exception as e:
        print(f"❌ ОШИБКА СЕТИ: {e}")
        return False


def main():
    if not ENV_FILE.exists():
        print(f"[!] Файл .env не найден в {ENV_FILE}. Создайте его и укажите ключи.")
        sys.exit(1)

    env_vars = dotenv_values(ENV_FILE)
    keys = []
    for k, v in sorted(env_vars.items()):
        if k.startswith("OPENCODE_KEY_") and v:
            clean_v = v.strip().strip("'").strip('"')
            if clean_v and clean_v != "sk-" and len(clean_v) > 5:
                keys.append((k, clean_v))

    if not keys:
        print("[!] В файле .env не найдено активных ключей OPENCODE_KEY_*.")
        sys.exit(1)

    print(f"=== Проверка {len(keys)} аккаунтов OpenCode ===")
    working = 0
    for name, key in keys:
        if test_key(name, key):
            working += 1

    print("---------------------------------------------")
    print(f"Итог: {working} из {len(keys)} ключей активны и готовы к вайбкодингу.")
    if working >= 2:
        print("🎉 Ротация готова: при исчерпании лимитов на одном ключе LiteLLM автоматически переключит на другие!")
    elif working == 1:
        print("ℹ️  Работает 1 ключ. Рекомендуется добавить еще хотя бы 2 для реального безлимита.")


if __name__ == "__main__":
    main()
