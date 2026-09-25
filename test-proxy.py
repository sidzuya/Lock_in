#!/usr/bin/env python3
"""
Скрипт тестирования локального LiteLLM Proxy.
Отправляет запросы к моделям через http://127.0.0.1:4000/v1.
"""

import sys
import json
import urllib.request
import urllib.error

PROXY_URL = "http://127.0.0.1:4000/v1/chat/completions"
MODELS_TO_TEST = ["big-pickle", "deepseek-v4-flash-free", "nemotron-3-super-free"]


def test_model(model_name):
    print(f"[*] Запрос к модели '{model_name}': ", end="", flush=True)

    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Скажи одним словом: работает?"}
        ],
        "max_tokens": 10
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-dummy"
    }

    req = urllib.request.Request(
        PROXY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            answer = data["choices"][0]["message"]["content"].strip()
            print(f"✅ УСПЕХ! Ответ: \"{answer}\"")
            return True
    except urllib.error.URLError as e:
        if "Connection refused" in str(e):
            print("❌ LiteLLM Proxy не запущен на http://127.0.0.1:4000. Запустите: ./start-proxy.sh")
        else:
            print(f"❌ Ошибка соединения: {e}")
        return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"❌ HTTP {e.code}: {body[:200]}")
        return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False


def main():
    print("=== Тестирование LiteLLM Proxy ===")
    success_count = 0
    for model in MODELS_TO_TEST:
        if test_model(model):
            success_count += 1

    print("---------------------------------------------")
    if success_count == len(MODELS_TO_TEST):
        print("🚀 Все модели отвечают идеально через ротацию ключей!")
    else:
        print(f"Готово: {success_count}/{len(MODELS_TO_TEST)} моделей ответили.")


if __name__ == "__main__":
    main()
