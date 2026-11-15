# src/api_reporter.py
import json
import os
import threading
from datetime import datetime

import requests

from src.config import BASE_DIR, APP_SETTINGS

PENDING_FILE = os.path.join(BASE_DIR, "api_pending.json")

# Корень проекта — на уровень выше src (check-in/)


def get_api_settings():
    """Настройки API берутся из app_settings (секция settings.json)"""
    return {
        "enabled": APP_SETTINGS.get("api_enabled", False),
        "url": (APP_SETTINGS.get("api_url") or "").strip(),
        "key": (APP_SETTINGS.get("api_key") or "").strip(),
    }


def build_snapshot():
    """Срез состояния — тот же формат, что employee_state.json"""
    import src.config as cfg
    return cfg._serialize_state()


def load_pending():
    if not os.path.exists(PENDING_FILE):
        return []
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    except Exception:
        return []


def save_pending(items):
    try:
        tmp = PENDING_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
        os.replace(tmp, PENDING_FILE)
    except Exception as e:
        print(f"❌ api_reporter: не удалось сохранить очередь: {e}")


def post_snapshot(snapshot):
    """Отправить один срез. Возвращает (ok, message)"""
    s = get_api_settings()
    if not s["enabled"] or not s["url"] or not s["key"]:
        return True, "API выключен — пропуск"
    try:
        resp = requests.post(
            s["url"],
            json=snapshot,
            headers={"X-API-Key": s["key"], "Content-Type": "application/json"},
            timeout=15,
        )
        ok = resp.status_code == 200 and resp.json().get("ok") is True
        if ok:
            counts = resp.json()
            msg = (f"✅ API: принято (новых событий: {counts.get('events_new', 0)}, "
                   f"смен: {counts.get('shifts', 0)})")
        else:
            msg = f"❌ API HTTP {resp.status_code}: {resp.text[:200]}"
        print(f"[api_reporter] {msg}")
        return ok, msg
    except Exception as e:
        print(f"[api_reporter] ❌ Ошибка отправки: {e}")
        return False, str(e)


def flush_queue():
    """Отправить накопленные срезы (старые → новые)"""
    items = load_pending()
    if not items:
        return
    rest = []
    for snap in items:
        ok, _ = post_snapshot(snap)
        if not ok:
            rest.append(snap)
    # Срез идемпотентен, поэтому при неудаче достаточно хранить последний
    save_pending(rest[-1:] if rest else [])


def send_snapshot(snapshot=None):
    """Отправить срез состояния в API (с очередью на неудачу).

    Вызывается из config.save_state() после каждой смены статуса,
    автозакрытия и сохранения состояния.
    """
    snap = snapshot if snapshot is not None else build_snapshot()
    ok, msg = post_snapshot(snap)
    if ok:
        flush_queue()
    else:
        items = load_pending()
        items.append(snap)
        save_pending(items[-1:])
    return ok, msg


def send_async(snapshot=None):
    """Не блокировать GUI: отправка в отдельном потоке"""
    snap = snapshot if snapshot is not None else build_snapshot()
    t = threading.Thread(target=send_snapshot, args=(snap,), daemon=True)
    t.start()


def start_reporter():
    """Первый срез при старте терминала (снимает автозакрытые смены)"""
    s = get_api_settings()
    if s["enabled"]:
        threading.Timer(2.0, lambda: send_async(build_snapshot())).start()
        print("📡 API-репортер запущен")
