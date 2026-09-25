#!/usr/bin/env python3
"""
Высокопроизводительный умный прокси-адаптер для OpenCode.
- Автоматически ротирует все API-ключи из .env при исчерпании лимитов (429).
- Генерирует каноничные ID сессий и сообщений через официальный алгоритм OpenCode (tU).
- Инжектирует официальный User-Agent и полный набор инструментов OpenCode.
- Обеспечивает 100% обход ошибки 403 FreeTierError.
- Полностью прозрачный SSE-стриминг для Pi Coding Agent и Hermes Agent.
"""

import os
import sys
import json
import time
import random
import asyncio
from pathlib import Path
from typing import List, Dict

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import dotenv_values

WORKSPACE_DIR = Path(__file__).resolve().parent
ENV_FILE = WORKSPACE_DIR / ".env"
TOOLS_FILE = WORKSPACE_DIR / "opencode_tools.json"

# Загрузка инструментов OpenCode
OPENCODE_TOOLS = []
if TOOLS_FILE.exists():
    try:
        with open(TOOLS_FILE, "r", encoding="utf-8") as f:
            OPENCODE_TOOLS = json.load(f)
    except Exception as e:
        print(f"[!] Ошибка загрузки {TOOLS_FILE}: {e}")

# Чтение ключей
def get_opencode_keys() -> List[str]:
    if not ENV_FILE.exists():
        return []
    env_vars = dotenv_values(ENV_FILE)
    keys = []
    for k, v in sorted(env_vars.items()):
        if k.startswith("OPENCODE_KEY_") and v:
            clean_v = v.strip().strip("'").strip('"')
            if clean_v and clean_v != "sk-" and len(clean_v) > 5:
                keys.append(clean_v)
    return keys

KEYS = get_opencode_keys()
KEY_COOLDOWNS: Dict[str, float] = {}

def get_next_key() -> str:
    now = time.time()
    available = [k for k in KEYS if KEY_COOLDOWNS.get(k, 0) <= now]
    if not available:
        return min(KEYS, key=lambda k: KEY_COOLDOWNS.get(k, 0))
    return random.choice(available)

def mark_key_cooldown(key: str, seconds: int = 60):
    KEY_COOLDOWNS[key] = time.time() + seconds
    masked = f"{key[:8]}...{key[-4:]}"
    print(f"[⚠️ 429/Кулдаун] Ключ {masked} временно отправлен отдыхать на {seconds} сек.")

# Каноничный генератор OpenCode ID (алгоритм tU из бинарника opencode)
_counter = 0
_last_ts = 0

def tU(descending: bool) -> str:
    global _counter, _last_ts
    Y = int(time.time() * 1000)
    if Y != _last_ts:
        _last_ts = Y
        _counter = 0
    _counter += 1
    val = (Y * 0x1000) + _counter
    if descending:
        A = (~val) & 0xFFFFFFFFFFFF
    else:
        A = val & 0xFFFFFFFFFFFF
    U = "".join(f"{(A >> (40 - 8 * i)) & 0xFF:02x}" for i in range(6))
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    rand_bytes = os.urandom(14)
    X = "".join(alphabet[b % 62] for b in rand_bytes)
    return U + X

def gen_session_id():
    return "ses_" + tU(True)

def gen_message_id():
    return "msg_" + tU(False)

app = FastAPI(title="OpenCode Unlimited Proxy")

UPSTREAM_URL = "https://opencode.ai/zen/v1/chat/completions"

@app.get("/v1/models")
@app.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "big-pickle", "object": "model", "owned_by": "opencode"},
            {"id": "deepseek-v4-flash-free", "object": "model", "owned_by": "opencode"},
            {"id": "nemotron-3-super-free", "object": "model", "owned_by": "opencode"},
        ]
    }

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    requested_model = body.get("model", "big-pickle")
    if requested_model.startswith("litellm/"):
        requested_model = requested_model.replace("litellm/", "")
    body["model"] = requested_model

    # Внедряем официальные инструменты OpenCode
    existing_tools = body.get("tools") or []
    existing_names = {t.get("function", {}).get("name") for t in existing_tools if isinstance(t, dict)}

    merged_tools = list(existing_tools)
    for tool in OPENCODE_TOOLS:
        name = tool.get("function", {}).get("name")
        if name and name not in existing_names:
            merged_tools.append(tool)

    body["tools"] = merged_tools
    if "tool_choice" not in body:
        body["tool_choice"] = "auto"

    is_streaming = body.get("stream", True)
    body["stream"] = is_streaming

    max_retries = max(5, len(KEYS) * 2)
    last_error_text = ""

    for attempt in range(max_retries):
        current_key = get_next_key()

        headers = {
            "Authorization": f"Bearer {current_key}",
            "Content-Type": "application/json",
            "User-Agent": "opencode/1.18.31 ai-sdk/provider-utils/4.0.23 runtime/bun/1.3.14",
            "x-opencode-client": "cli",
            "x-opencode-project": "global",
            "x-opencode-session": gen_session_id(),
            "x-opencode-request": gen_message_id(),
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

        try:
            client = httpx.AsyncClient(timeout=120.0)
            req = client.build_request("POST", UPSTREAM_URL, json=body, headers=headers)
            resp = await client.send(req, stream=is_streaming)

            if resp.status_code == 429:
                mark_key_cooldown(current_key, 60)
                await resp.aclose()
                await client.aclose()
                continue

            if resp.status_code != 200:
                error_body = await resp.aread()
                await resp.aclose()
                await client.aclose()
                last_error_text = error_body.decode("utf-8", errors="ignore")
                print(f"[!] Ответ OpenCode {resp.status_code}: {last_error_text[:150]}")
                mark_key_cooldown(current_key, 60)
                continue

            # Успешный ответ
            if is_streaming:
                async def stream_generator():
                    try:
                        async for chunk in resp.aiter_bytes():
                            yield chunk
                    finally:
                        await resp.aclose()
                        await client.aclose()

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
            else:
                resp_data = await resp.aread()
                await resp.aclose()
                await client.aclose()
                return JSONResponse(content=json.loads(resp_data))

        except Exception as e:
            print(f"[!] Ошибка соединения: {e}")
            await asyncio.sleep(0.5)

    raise HTTPException(status_code=502, detail=f"Все аккаунты временно недоступны. Ошибка: {last_error_text}")

if __name__ == "__main__":
    import uvicorn
    port = 4000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    print(f"[*] Запуск OpenCode Unlimited Proxy на http://127.0.0.1:{port}...")
    print(f"[*] Загружено {len(KEYS)} ключей для ротации.")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
