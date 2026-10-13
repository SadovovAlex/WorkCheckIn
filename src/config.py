# src/config.py
import random
import json
import os
from datetime import datetime, timedelta
from src.weather import get_weather

# Корень проекта — на уровень выше src (check-in/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Файл настроек (в корне проекта)
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


# ============================================================
# ДЕФОЛТНЫЕ ЗНАЧЕНИЯ
# ============================================================
DEFAULT_EMPLOYEES = [
    {"id": 1, "name": "Иванов",     "first_name": "Иван",    "position": "Слесарь",   "avatar": "💡"},
    {"id": 2, "name": "Петров",     "first_name": "Пётр",    "position": "Наладчик",  "avatar": "🔧"},
    {"id": 3, "name": "Сидорова",   "first_name": "Анна",    "position": "ОТК",       "avatar": "👨‍🔬"},
    {"id": 4, "name": "Кузнецов",   "first_name": "Сергей",  "position": "Оператор",  "avatar": "👨‍🔧"},
    {"id": 5, "name": "Смирнов",    "first_name": "Алексей", "position": "Оператор",  "avatar": "👨‍🔧"},
    {"id": 6, "name": "Попов",      "first_name": "Григорий","position": "Оператор",  "avatar": "👨‍🔧"},
    {"id": 7, "name": "Волков",     "first_name": "Иван",    "position": "Наладчик",  "avatar": "🔧"},
    {"id": 8, "name": "Морозова",   "first_name": "Елена",   "position": "ОТК",       "avatar": "👨‍🔬"},
    {"id": 9, "name": "Новиков",    "first_name": "Сергей",  "position": "Универсал", "avatar": "🔥"},
    {"id": 10, "name": "Фёдорова",  "first_name": "Дарья",   "position": "ОТК",       "avatar": "👨‍🔬"},
    {"id": 11, "name": "Егорова",   "first_name": "Юлия",    "position": "ОТК",       "avatar": "👨‍🔬"},
    {"id": 12, "name": "Никитин",   "first_name": "Игорь",   "position": "Оператор",  "avatar": "👨‍🔧"},
    {"id": 13, "name": "Орлов",     "first_name": "Алексей", "position": "Оператор",  "avatar": "👨‍🔧"},
    {"id": 14, "name": "Русланов",  "first_name": "Руслан",  "position": "Слесарь",   "avatar": "💡"},
    {"id": 15, "name": "TEST",      "first_name": "test",    "position": "test",      "avatar": "💡"}
]

DEFAULT_PARTS = [
    {"name": "Толкатели",          "stock": 300,  "status": "Ежедневно",  "color": "#B51A34"},
    {"name": "Корпус Cummins",     "stock": 302,  "status": "Необходимо", "color": "#FF9800"},
    {"name": "Корпус газ",         "stock": 3000, "status": "В наличии",  "color": "#00FF7B"},
    {"name": "Звезда промвала E3", "stock": 1000, "status": "Необходимо", "color": "#D4DE15"},
]

DEFAULT_CAMERA_SETTINGS = {
    "camera_id": 0,
    "photo_width": 640,
    "photo_height": 480,
    "save_path": "photos",
    "photo_format": "jpg",
    "preview_duration": 3000,
    "flash_enabled": True,
    "auto_focus": True,
}

DEFAULT_APP_SETTINGS = {
    "idle_timeout": 10,
    "email_smtp_server": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_sender": "terminal@example.com",
    "email_password": "",
    "email_receiver": "admin@example.com",
    "email_send_time_morning": "09:00",
    "email_send_time_evening": "20:00",
    "auto_send_reports": True,
    "show_employee_photos": True,
    "animation_enabled": True,
    "font_size_scale": 1.5,
    "face_recognition_enabled": False,
    "face_recognition_confidence": 0.7,
    "show_work_time_on_card": False,
}


# ============================================================
# ЗАГРУЗКА ИЗ settings.json
# ============================================================
def _load_settings_file():
    """Прочитать settings.json, если он есть. Иначе — пустой dict."""
    if not os.path.exists(SETTINGS_FILE):
        print(f"ℹ️ settings.json не найден ({SETTINGS_FILE}) — используем значения по умолчанию")
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения settings.json: {e}")
        return {}


_settings_data = _load_settings_file()

# Сотрудники: из settings.json, иначе — дефолт
EMPLOYEES = _settings_data.get("employees", DEFAULT_EMPLOYEES)

# Детали: из settings.json, иначе — дефолт
PARTS = _settings_data.get("parts", DEFAULT_PARTS)

# Настройки камеры: из settings.json, иначе — дефолт
CAMERA_SETTINGS = {**DEFAULT_CAMERA_SETTINGS, **_settings_data.get("camera_settings", {})}

# Настройки приложения: из settings.json (секция app_settings), иначе — дефолт
APP_SETTINGS = {**DEFAULT_APP_SETTINGS, **_settings_data.get("app_settings", {})}

# Пароль администратора
ADMIN_PASSWORD = _settings_data.get("admin_password", "123")


def reload_settings():
    """Перечитать settings.json и обновить модульные переменные.
    Вызывать после сохранения настроек через UI."""
    global EMPLOYEES, PARTS, CAMERA_SETTINGS, APP_SETTINGS, ADMIN_PASSWORD
    data = _load_settings_file()
    EMPLOYEES = data.get("employees", DEFAULT_EMPLOYEES)
    PARTS = data.get("parts", DEFAULT_PARTS)
    CAMERA_SETTINGS = {**DEFAULT_CAMERA_SETTINGS, **data.get("camera_settings", {})}
    APP_SETTINGS = {**DEFAULT_APP_SETTINGS, **data.get("app_settings", {})}
    ADMIN_PASSWORD = data.get("admin_password", "123")
    return data


# ============================================================
# ФАЙЛ СОСТОЯНИЯ СОТРУДНИКОВ
# ============================================================
STATE_FILE = os.path.join(BASE_DIR, "employee_state.json")

EMPLOYEE_STATUS = {}
EMPLOYEE_CHECKIN_TIME = {}
EMPLOYEE_HISTORY = {}

MAX_SHIFT_HOURS = 15


# ============================================================
# СЕРИАЛИЗАЦИЯ / СОХРАНЕНИЕ / ЗАГРУЗКА СОСТОЯНИЯ
# ============================================================
def _serialize_state():
    state = {
        "employee_status": {},
        "employee_history": {},
        "saved_at": datetime.now().isoformat(),
    }

    for emp_id, data in EMPLOYEE_STATUS.items():
        state["employee_status"][str(emp_id)] = {
            "status": data.get("status"),
            "time": data.get("time"),
            "date": data.get("date"),
            "checkout_time": data.get("checkout_time"),
            "forgot_checkout": data.get("forgot_checkout", False),
        }

    for emp_id, data in EMPLOYEE_HISTORY.items():
        state["employee_history"][str(emp_id)] = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                state["employee_history"][str(emp_id)][key] = value.isoformat()
            else:
                state["employee_history"][str(emp_id)][key] = value

    return state


def save_state():
    try:
        state = _serialize_state()
        tmp_file = STATE_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, STATE_FILE)
        print(f"💾 Состояние сотрудников сохранено: {STATE_FILE}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения состояния: {e}")
        return False


def load_state():
    global EMPLOYEE_STATUS, EMPLOYEE_CHECKIN_TIME, EMPLOYEE_HISTORY

    if not os.path.exists(STATE_FILE):
        print("ℹ️ Файл состояния не найден — начинаем с чистого листа")
        return False

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        loaded_status = state.get("employee_status", {})
        EMPLOYEE_STATUS = {}
        EMPLOYEE_CHECKIN_TIME = {}

        today = datetime.now().strftime("%Y-%m-%d")
        saved_at = state.get("saved_at", "")
        saved_date = saved_at[:10] if saved_at else ""

        for emp_id_str, data in loaded_status.items():
            try:
                emp_id = int(emp_id_str)
            except ValueError:
                continue

            EMPLOYEE_STATUS[emp_id] = {
                "status": data.get("status", "off"),
                "time": data.get("time"),
                "date": data.get("date"),
                "checkout_time": data.get("checkout_time"),
                "forgot_checkout": data.get("forgot_checkout", False),
            }

            if data.get("status") == "on" and data.get("time"):
                if saved_date == today:
                    try:
                        h, m, s = map(int, data["time"].split(":"))
                        checkin_dt = datetime.now().replace(
                            hour=h, minute=m, second=s, microsecond=0
                        )
                        EMPLOYEE_CHECKIN_TIME[emp_id] = checkin_dt
                    except Exception:
                        pass
                else:
                    EMPLOYEE_STATUS[emp_id]["status"] = "off"
                    EMPLOYEE_STATUS[emp_id]["checkout_time"] = "23:59:59"
                    EMPLOYEE_STATUS[emp_id]["forgot_checkout"] = True

        loaded_history = state.get("employee_history", {})
        EMPLOYEE_HISTORY = {}
        for emp_id_str, data in loaded_history.items():
            try:
                emp_id = int(emp_id_str)
            except ValueError:
                continue
            EMPLOYEE_HISTORY[emp_id] = {}
            for key, value in data.items():
                if isinstance(value, str) and ("T" in value or "-" in value):
                    try:
                        EMPLOYEE_HISTORY[emp_id][key] = datetime.fromisoformat(value)
                        continue
                    except Exception:
                        pass
                EMPLOYEE_HISTORY[emp_id][key] = value

        print(f"📂 Состояние сотрудников загружено ({len(EMPLOYEE_STATUS)} записей)")
        auto_close_forgotten_shifts()
        return True

    except Exception as e:
        print(f"❌ Ошибка загрузки состояния: {e}")
        return False


def auto_close_forgotten_shifts():
    now = datetime.now()
    changed = False

    for emp_id in list(EMPLOYEE_CHECKIN_TIME.keys()):
        checkin_dt = EMPLOYEE_CHECKIN_TIME[emp_id]
        delta = now - checkin_dt

        if delta.total_seconds() >= MAX_SHIFT_HOURS * 3600:
            auto_checkout_dt = checkin_dt + timedelta(hours=MAX_SHIFT_HOURS)

            EMPLOYEE_STATUS[emp_id] = {
                "status": "off",
                "time": checkin_dt.strftime("%H:%M:%S"),
                "date": checkin_dt.strftime("%Y-%m-%d"),
                "checkout_time": auto_checkout_dt.strftime("%H:%M:%S"),
                "forgot_checkout": True,
            }

            EMPLOYEE_HISTORY.setdefault(emp_id, {})["departed"] = auto_checkout_dt
            del EMPLOYEE_CHECKIN_TIME[emp_id]
            changed = True

            print(f"⚠️ Сотрудник {emp_id}: смена автоматически закрыта "
                  f"(приход {checkin_dt.strftime('%H:%M:%S')}, "
                  f"закрыто в {auto_checkout_dt.strftime('%H:%M:%S')}, "
                  f"забыл нажать УШЁЛ)")

    if changed:
        save_state()

    return changed


# ============================================================
# РАБОТА СО СТАТУСАМИ
# ============================================================
def get_employee_status(emp_id):
    auto_close_forgotten_shifts()
    return EMPLOYEE_STATUS.get(emp_id, {"status": "off", "time": None, "date": None})


def set_employee_status(emp_id, status):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    if status == "on":
        EMPLOYEE_STATUS[emp_id] = {
            "status": "on",
            "time": now.strftime("%H:%M:%S"),
            "date": today,
            "checkout_time": None,
            "forgot_checkout": False,
        }
        EMPLOYEE_CHECKIN_TIME[emp_id] = now
        if emp_id not in EMPLOYEE_HISTORY:
            EMPLOYEE_HISTORY[emp_id] = {}
        EMPLOYEE_HISTORY[emp_id]["arrived"] = now

    elif status == "off":
        prev = EMPLOYEE_STATUS.get(emp_id, {})
        checkin = prev.get("time") or (
            EMPLOYEE_CHECKIN_TIME[emp_id].strftime("%H:%M:%S")
            if emp_id in EMPLOYEE_CHECKIN_TIME else None
        )
        checkin_date = prev.get("date") or (
            EMPLOYEE_CHECKIN_TIME[emp_id].strftime("%Y-%m-%d")
            if emp_id in EMPLOYEE_CHECKIN_TIME else None
        )

        EMPLOYEE_STATUS[emp_id] = {
            "status": "off",
            "time": checkin,
            "date": checkin_date,
            "checkout_time": now.strftime("%H:%M:%S"),
            "forgot_checkout": False,
        }
        if emp_id in EMPLOYEE_CHECKIN_TIME:
            EMPLOYEE_HISTORY.setdefault(emp_id, {})["departed"] = now
            del EMPLOYEE_CHECKIN_TIME[emp_id]

    save_state()


def get_work_time(emp_id):
    if emp_id in EMPLOYEE_CHECKIN_TIME:
        start = EMPLOYEE_CHECKIN_TIME[emp_id]
        now = datetime.now()
        delta = now - start
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    return "00:00"


def get_current_weather():
    return get_weather()


WEATHER = get_weather()


# ============================================================
# АВТОЗАГРУЗКА СОСТОЯНИЯ ПРИ ИМПОРТЕ (в самом конце!)
# ============================================================
load_state()