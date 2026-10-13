# src/weather.py
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import time
import json

# Корень проекта — на уровень выше src (check-in/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

DEBUG_MODE = False   # включи True, если нужны подробные логи погоды

class WeatherService:
    """Сервис для получения погоды без API-ключа"""

    def __init__(self, city="elektrostal"):
        self.city = city
        self.cache = {}
        self.last_update = None

    def _dump_html(self, name, response):
        """
        Сохраняет HTML-ответ и логирует диагностику:
        - файл logs/debug_<name>.html
        - статус, длину, кодировку, title
        """
        try:
            # 1) Сохраняем полный HTML
            html_path = os.path.join(LOG_DIR, f"debug_{name}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            # 2) Диагностика
            self._log(
                f"💾 {name}: HTML сохранён → {html_path} "
                f"({len(response.text)} символов)",
                "DEBUG"
            )

            # 3) Пытаемся вытащить title — сразу видно, что за страница
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                title = (soup.title.string or "").strip() if soup.title else "(нет title)"
                self._log(f"📄 {name}: title = {title!r}", "DEBUG")
            except Exception as e:
                self._log(f"⚠️ {name}: не удалось прочитать title: {e}", "WARNING")

            # 4) Первые 500 символов — для быстрого взгляда
            preview = response.text[:500].replace("\n", " ")
            self._log(f"👀 {name}: preview = {preview!r}", "DEBUG")

            # 5) Если это JSON — тоже сохраним
            try:
                data = response.json()
                json_path = os.path.join(LOG_DIR, f"debug_{name}.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self._log(f"💾 {name}: JSON сохранён → {json_path}", "DEBUG")
            except Exception:
                pass   # не JSON — не страшно

        except Exception as e:
            self._log(f"❌ {name}: ошибка дампа HTML: {e}", "ERROR")

    @staticmethod
    def _log(message, level="INFO"):
        """Единая функция логирования для weather.py"""
        if not DEBUG_MODE:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        try:
            log_file = os.path.join(LOG_DIR, "weather_debug.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            print(log_entry.strip())
        except Exception as e:
            print(f"❌ Ошибка записи лога погоды: {e}")

    def _get_wttr(self):
        """wttr.in — простой источник, отдаёт JSON, без ключа"""
        url = "https://wttr.in/Elektrostal?format=j1"
        headers = {"User-Agent": "curl/8.0"}
        self._log(f"GET {url}", "DEBUG")
        t = time.time()
        r = requests.get(url, headers=headers, timeout=15)
        self._log(f"HTTP {r.status_code} за {time.time()-t:.2f}s, "
                  f"{len(r.text)} байт", "DEBUG")
        #self._dump_html("wttr", r)

        if r.status_code != 200:
            return None
        try:
            data = r.json()
        except Exception as e:
            self._log(f"❌ wttr.in: не JSON: {e}", "ERROR")
            return None

        cur = data["current_condition"][0]
        code = int(cur.get("weatherCode", 113))
        wwo = {
            113: ("Ясно", "☀️"), 116: ("Переменная облачность", "⛅"),
            119: ("Облачно", "☁️"), 122: ("Пасмурно", "☁️"),
            143: ("Туман", "🌫️"), 176: ("Морось", "🌦️"),
            200: ("Гроза", "⛈️"), 227: ("Снег", "❄️"),
            230: ("Снегопад", "❄️"), 248: ("Туман", "🌫️"),
            260: ("Туман", "🌫️"), 263: ("Морось", "🌦️"),
            266: ("Морось", "🌦️"), 281: ("Морось", "🌦️"),
            284: ("Морось", "🌦️"), 293: ("Дождь", "🌧️"),
            296: ("Дождь", "🌧️"), 299: ("Дождь", "🌧️"),
            302: ("Дождь", "🌧️"), 305: ("Дождь", "🌧️"),
            308: ("Ливень", "🌧️"), 311: ("Ливень", "🌧️"),
            314: ("Ливень", "🌧️"), 353: ("Ливень", "🌧️"),
            356: ("Ливень", "🌧️"), 359: ("Ливень", "🌧️"),
            362: ("Дождь со снегом", "🌨️"), 365: ("Дождь со снегом", "🌨️"),
            368: ("Снег", "🌨️"), 371: ("Снегопад", "❄️"),
            374: ("Дождь со снегом", "🌨️"), 377: ("Дождь со снегом", "🌨️"),
            386: ("Гроза", "⛈️"), 389: ("Гроза", "⛈️"),
            392: ("Гроза со снегом", "⛈️"), 395: ("Гроза со снегом", "⛈️"),
        }
        cond, icon = wwo.get(code, ("—", "❓"))

        # Скорость ветра в wttr.in в km/h → м/с
        try:
            wind_ms = f"{int(cur['windspeedKmph']) / 3.6:.1f}"
        except Exception:
            wind_ms = "--"

        weather = {
            "temp": f"{cur['temp_C']}°C",
            "condition": cond,
            "icon": icon,
            "humidity": f"{cur['humidity']}%",
            "wind": f"{wind_ms} м/с",
        }
        self._log(f"✅ wttr.in распарсено: {weather}", "DEBUG")
        return weather

    def get_weather(self):
        """Получить текущую погоду"""
        # Кеширование на 30 минут
        if self.last_update:
            delta = datetime.now() - self.last_update
            if delta.seconds < 1800 and self.cache:
                return self.cache

        # 1) wttr.in — самый надёжный
        for name, fn in (
           #("wttr.in",     self._get_wttr),
            #("Gismeteo",    self._get_gismeteo),
            ("Яндекс",      self._get_yandex),
            #("Open-Meteo",  self._get_open_meteo),
        ):
            try:
                t = time.time()
                weather = fn()
                if weather and weather.get("temp", "--°C") != "--°C":
                    self.cache = weather
                    self.last_update = datetime.now()
                    self._log(f"✅ {name} за {time.time()-t:.2f}s → {weather}")
                    return weather
                self._log(f"⚠️ {name}: пустой результат", "WARNING")
            except Exception as e:
                self._log(f"❌ {name} ошибка: {e}", "ERROR")

        if self.cache:
            self._log("⚠️ Отдаём кеш", "WARNING")
            return self.cache
        return {
            "temp": "+-1°C", "condition": "неЯсно", "icon": "☀️",
            "humidity": "0%", "wind": "0 м/с"
        }
        
        # Если ничего не получилось, возвращаем кеш или дефолтные данные
        if self.cache:
            return self.cache
        
        # Дефолтные данные
        return {
            "temp": "+-1°C",
            "condition": "неЯсно",
            "icon": "☀️",
            "humidity": "0%",
            "wind": "0 м/с"
        }
    
    def _get_gismeteo(self):
        """Получение погоды с Gismeteo"""
       
        url = f"https://www.gismeteo.ru/weather-elektrostal-11312/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        #self._dump_html("gismeteo", response) 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        weather = {}
        
        # Температура
        temp_elem = soup.find('span', class_='js_value')
        if temp_elem:
            temp = temp_elem.text.strip()
            # Добавляем знак градуса если его нет
            if temp and not temp.endswith('°'):
                temp = temp + '°'
            weather['temp'] = temp
        
        # Температура может быть в другом месте
        if not weather.get('temp'):
            temp_elem = soup.find('span', class_=re.compile(r'temp[_-]value'))
            if temp_elem:
                temp = temp_elem.text.strip()
                if temp and not temp.endswith('°'):
                    temp = temp + '°'
                weather['temp'] = temp
        
        # Влажность
        humidity_elem = soup.find('span', class_=re.compile(r'humidity[_-]value'))
        if humidity_elem:
            humidity = humidity_elem.text.strip()
            weather['humidity'] = humidity + '%'
        else:
            # Ищем по другому классу
            humidity_elem = soup.find('div', class_=re.compile(r'humidity'))
            if humidity_elem:
                text = humidity_elem.text.strip()
                match = re.search(r'(\d+)%', text)
                if match:
                    weather['humidity'] = match.group(0)
        
        # Ветер
        wind_elem = soup.find('span', class_=re.compile(r'wind[_-]value'))
        if wind_elem:
            wind = wind_elem.text.strip()
            weather['wind'] = wind + ' м/с'
        else:
            wind_elem = soup.find('div', class_=re.compile(r'wind'))
            if wind_elem:
                text = wind_elem.text.strip()
                match = re.search(r'(\d+)\s*м/с', text)
                if match:
                    weather['wind'] = match.group(0)
        
        # Погодное условие и иконка
        condition_map = {
            'ясно': ('Ясно', '☀️'),
            'солнечно': ('Солнечно', '☀️'),
            'облачно': ('Облачно', '⛅'),
            'пасмурно': ('Пасмурно', '☁️'),
            'дождь': ('Дождь', '🌧️'),
            'ливень': ('Ливень', '🌧️'),
            'снег': ('Снег', '❄️'),
            'снегопад': ('Снегопад', '❄️'),
            'гроза': ('Гроза', '⛈️'),
            'туман': ('Туман', '🌫️'),
            'ветер': ('Ветер', '💨'),
            'переменная облачность': ('Переменная облачность', '⛅')
        }
        
        # Ищем описание погоды
        condition_elem = soup.find('div', class_=re.compile(r'weather[_-]description'))
        if condition_elem:
            text = condition_elem.text.strip().lower()
            for key, (condition, icon) in condition_map.items():
                if key in text:
                    weather['condition'] = condition
                    weather['icon'] = icon
                    break
            else:
                weather['condition'] = 'Ясно'
                weather['icon'] = '☀️'
        else:
            weather['condition'] = 'Ясно'
            weather['icon'] = '☀️'
        
        # Если температура не найдена, ищем по-другому
        if not weather.get('temp'):
            temp_elem = soup.find('div', class_=re.compile(r'temp[_-]'))
            if temp_elem:
                text = temp_elem.text.strip()
                match = re.search(r'([+-]?\d+°?)', text)
                if match:
                    temp = match.group(1)
                    if not temp.endswith('°'):
                        temp = temp + '°'
                    weather['temp'] = temp
        
        # Устанавливаем дефолтные значения для отсутствующих полей
        weather.setdefault('temp', '--°C')
        weather.setdefault('condition', '-')
        weather.setdefault('icon', '☀️')
        weather.setdefault('humidity', '--%')
        weather.setdefault('wind', '-- м/с')
        
        return weather

    def _get_open_meteo(self):
        """Надёжный источник — Open-Meteo, без ключа"""
        url = ("https://api.open-meteo.com/v1/forecast"
            "?latitude=55.784&longitude=38.445"
            "&current=temperature_2m,relative_humidity_2m,"
            "wind_speed_10m,weather_code")
        self._log(f"GET {url}", "DEBUG")
        r = requests.get(url, timeout=10)
        self._log(f"HTTP {r.status_code}, {len(r.text)} байт", "DEBUG")
        data = r.json().get("current", {})

        code = data.get("weather_code", 0)
        condition_map = {
            0: ("Ясно", "☀️"), 1: ("Преимущественно ясно", "🌤️"),
            2: ("Переменная облачность", "⛅"), 3: ("Пасмурно", "☁️"),
            45: ("Туман", "🌫️"), 48: ("Изморозь", "🌫️"),
            51: ("Морось", "🌦️"), 61: ("Дождь", "🌧️"),
            71: ("Снег", "❄️"), 80: ("Ливень", "🌧️"),
            95: ("Гроза", "⛈️"),
        }
        condition, icon = condition_map.get(code, ("—", "❓"))

        weather = {
            "temp": f"{data.get('temperature_2m', '--')}°C",
            "condition": condition,
            "icon": icon,
            "humidity": f"{data.get('relative_humidity_2m', '--')}%",
            "wind": f"{data.get('wind_speed_10m', '--')} м/с",
        }
        self._log(f"Open-Meteo распарсено: {weather}", "DEBUG")
        return weather
    
    def _get_yandex(self):
        """Яндекс.Погода — парсим регулярками по тексту страницы"""
        url = "https://yandex.ru/pogoda/ru?lat=55.784&lon=38.445"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }

        self._log(f"GET {url}", "DEBUG")
        t = time.time()
        r = requests.get(url, headers=headers, timeout=15)
        self._log(f"HTTP {r.status_code} за {time.time()-t:.2f}s, "
                  f"{len(r.text)} байт", "DEBUG")
        r.encoding = 'utf-8'

        #self._dump_html("yandex", r)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Берём ВЕСЬ текст страницы одной строкой
        text = soup.get_text(" ", strip=True)

        weather = {}

        # --- 1) Пытаемся найти JSON __NEXT_DATA__ (самый надёжный путь) ---
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data and next_data.string:
            import json as _json
            try:
                data = _json.loads(next_data.string)
                found = self._walk_json_for_weather(data)
                if found:
                    self._log(f"✅ Yandex: JSON найден: {found}", "DEBUG")
                    temp = (found.get('temperature') or found.get('temp')
                            or found.get('tempAvg'))
                    hum = (found.get('humidity')
                           or found.get('relativeHumidity'))
                    wind = (found.get('windSpeed') or found.get('wind')
                            or found.get('wind_speed'))
                    cond_txt = (found.get('condition') or found.get('weatherType')
                                or found.get('conditionText'))
                    if temp is not None:
                        weather['temp'] = f"{temp}°C"
                    if hum is not None:
                        weather['humidity'] = f"{hum}%"
                    if wind is not None:
                        weather['wind'] = f"{wind} м/с"
                    if cond_txt:
                        weather['condition'], weather['icon'] = \
                            self._map_condition(str(cond_txt))
            except Exception as e:
                self._log(f"⚠️ Yandex: NEXT_DATA не JSON: {e}", "DEBUG")

        # --- 2) Fallback: регулярки по тексту страницы ---
        if 'temp' not in weather:
            # Ищем "температура воздуха +10°" или "+10°, ощущается как"
            m = re.search(
                r'температура\s+воздуха\s+([+-−]?\d+)\s*°',
                text, re.I
            )
            if not m:
                m = re.search(r'Сейчас[^.]*?([+-−]\d+)\s*°', text)
            if not m:
                # Ищем во фразе "Сейчас в Электростали температура воздуха +10°"
                m = re.search(
                    r'температура\s+воздуха\s+([+-−]?\d+)\s*°',
                    text, re.I
                )
            if m:
                weather['temp'] = f"{m.group(1).replace('−','-')}°C"
                self._log(f"🔎 Yandex temp из текста: {weather['temp']}", "DEBUG")

        if 'humidity' not in weather:
            m = re.search(r'влажность\s+(\d+)\s*%', text, re.I)
            if not m:
                m = re.search(r'Влажность\s+(\d+)\s*%', text)
            if m:
                weather['humidity'] = f"{m.group(1)}%"

        if 'wind' not in weather:
            # Ищем "3,4 м/с" — запятая или точка
            m = re.search(r'(\d+[.,]\d+)\s*м/с', text)
            if not m:
                m = re.search(r'ветра\s+(\d+)\s*м/с', text, re.I)
            if m:
                weather['wind'] = f"{m.group(1).replace(',', '.')} м/с"

        # --- 3) Состояние погоды — строго из блока "погода сейчас" ---
        if 'condition' not in weather:
            m = re.search(
                r'погода\s+сейчас[:\s]+([А-Яа-яЁё\-\s]+?)(?:\.|,|Сегодня|Осадки|Температура|$)',
                text, re.I
            )
            if m:
                condition_text = m.group(1).strip()
                self._log(f"🔎 Yandex condition из блока 'сейчас': {condition_text!r}", "DEBUG")
                weather['condition'], weather['icon'] = self._map_condition(condition_text)
            else:
                # Fallback: если не нашли фразу "погода сейчас" — ищем в первых 300 символах текста
                head = text[:300].lower()
                for key, (cond, icon) in (
                    ('ясно',            ('Ясно', '☀️')),
                    ('малооблачно',     ('Малооблачно', '🌤️')),
                    ('переменная облачность', ('Переменная облачность', '⛅')),
                    ('облачно',         ('Облачно', '⛅')),
                    ('пасмурно',        ('Пасмурно', '☁️')),
                    ('небольшой дождь', ('Небольшой дождь', '🌧️')),
                    ('ливень',          ('Ливень', '🌧️')),
                    ('дождь',           ('Дождь', '🌧️')),
                    ('гроза',           ('Гроза', '⛈️')),
                    ('снег',            ('Снег', '❄️')),
                    ('туман',           ('Туман', '🌫️')),
                ):
                    if key in head:
                        weather['condition'], weather['icon'] = cond, icon
                        break
                else:
                    weather['condition'], weather['icon'] = ('—', '❓')

        # --- 4) Дефолты, если совсем ничего не нашли ---
        weather.setdefault('temp', '--°C')
        weather.setdefault('condition', '-')
        weather.setdefault('icon', '☀️')
        weather.setdefault('humidity', '--%')
        weather.setdefault('wind', '-- м/с')

        self._log(f"🔎 Yandex распарсено: {weather}", "DEBUG")

        if weather['temp'] == '--°C':
            self._log(
                "⚠️ Yandex: не удалось найти температуру. "
                "Смотри logs/debug_yandex.html",
                "WARNING"
            )
            return None

        return weather

    def _map_condition(self, text):
        t = text.lower()
        if 'дожд' in t:    return ('Дождь', '🌧️')
        if 'ливень' in t:  return ('Ливень', '🌧️')
        if 'гроз' in t:    return ('Гроза', '⛈️')
        if 'снег' in t:    return ('Снег', '❄️')
        if 'туман' in t:   return ('Туман', '🌫️')
        if 'пасмурно' in t: return ('Пасмурно', '☁️')
        if 'облачно' in t: return ('Облачно', '⛅')
        if 'ясно' in t:    return ('Ясно', '☀️')
        return ('—', '❓')


# Глобальный экземпляр сервиса
weather_service = WeatherService(city="Moscow")

def get_weather():
    """Получить погоду (глобальная функция)"""
    return weather_service.get_weather()