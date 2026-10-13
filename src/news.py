# src/news.py
"""
Модуль получения новостей с regions.ru/elektrostal.

Использует парсинг HTML (RSS у сайта нет).
Кеширует результаты, чтобы не спамить сайт запросами.

⚠️ Правовой аспект: показываем только ЗАГОЛОВОК, КРАТКУЮ АННОТАЦИЮ и ССЫЛКУ
на источник. Полный текст новостей не копируем (ст. 1274 ГК РФ).
"""

import os
import json
import time
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# Корень проекта — на уровень выше src (check-in/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
NEWS_CACHE_FILE = os.path.join(CACHE_DIR, "news_cache.json")
NEWS_IMAGES_DIR = os.path.join(CACHE_DIR, "news_images")

for d in (LOG_DIR, CACHE_DIR, NEWS_IMAGES_DIR):
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

DEBUG_MODE = True   # включи False, если не нужны подробные логи


# ============================================================
# СЕРВИС НОВОСТЕЙ
# ============================================================
class NewsService:
    """Сервис получения новостей с regions.ru/elektrostal"""

    BASE_URL = "https://regions.ru/elektrostal"

    # Кеш живёт 30 минут — новости не так часто меняются, как погода
    CACHE_TTL_SECONDS = 30 * 60

    # Сколько новостей забираем
    MAX_NEWS = 10

    # Таймаут HTTP
    HTTP_TIMEOUT = 15

    # User-Agent — представляемся как обычный браузер
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self):
        self.cache = []           # список новостей
        self.last_update = None   # datetime последнего успешного обновления

        # Пытаемся загрузить кеш с диска при старте
        self._load_cache_from_disk()

    # ---------- ЛОГИРОВАНИЕ ----------
    @staticmethod
    def _log(message, level="INFO"):
        """Единая функция логирования"""
        if not DEBUG_MODE:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [NEWS] [{level}] {message}\n"
        try:
            log_file = os.path.join(LOG_DIR, "news_debug.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            print(log_entry.strip())
        except Exception as e:
            print(f"❌ Ошибка записи лога новостей: {e}")

    # ---------- КЕШ НА ДИСКЕ ----------
    def _load_cache_from_disk(self):
        """Загрузить кеш новостей с диска (на случай перезапуска приложения)"""
        if not os.path.exists(NEWS_CACHE_FILE):
            return
        try:
            with open(NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.cache = data.get("news", [])
            saved_at = data.get("saved_at")
            if saved_at:
                self.last_update = datetime.fromisoformat(saved_at)
            self._log(f"💾 Кеш новостей загружен с диска ({len(self.cache)} шт.)")
        except Exception as e:
            self._log(f"⚠️ Не удалось прочитать кеш новостей: {e}", "WARNING")

    def _save_cache_to_disk(self):
        """Сохранить кеш новостей на диск"""
        try:
            data = {
                "news": self.cache,
                "saved_at": (self.last_update or datetime.now()).isoformat(),
            }
            tmp_file = NEWS_CACHE_FILE + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, NEWS_CACHE_FILE)
            self._log(f"💾 Кеш новостей сохранён ({len(self.cache)} шт.)")
        except Exception as e:
            self._log(f"❌ Ошибка сохранения кеша новостей: {e}", "ERROR")

    # ---------- СКАЧИВАНИЕ HTML ----------
    def _fetch_html(self):
        """Скачать HTML главной страницы раздела Электросталь"""
        url = self.BASE_URL
        self._log(f"GET {url}", "DEBUG")
        t = time.time()
        try:
            r = requests.get(url, headers=self.HEADERS, timeout=self.HTTP_TIMEOUT)
        except Exception as e:
            self._log(f"❌ HTTP ошибка: {e}", "ERROR")
            return None

        self._log(
            f"HTTP {r.status_code} за {time.time()-t:.2f}s, "
            f"{len(r.text)} байт",
            "DEBUG",
        )
        if r.status_code != 200:
            return None
        r.encoding = "utf-8"
        return r.text

    # ---------- ПАРСИНГ HTML ----------
    def _parse_news(self, html):
        """
        Извлечь список новостей из HTML.

        Возвращает список словарей:
        [
            {
                "title": "...",
                "url": "https://...",
                "image": "https://..." или "",
                "summary": "..." (краткое описание, может быть пустым),
                "time": "14:32" или ""
            },
            ...
        ]
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        news = []

        # ---------- Попытка 1: искать JSON-LD (schema.org ItemList/NewsArticle) ----------
        news_from_jsonld = self._parse_jsonld(soup)
        if news_from_jsonld:
            self._log(f"✅ Найдено {len(news_from_jsonld)} новостей в JSON-LD")
            return news_from_jsonld[: self.MAX_NEWS]

        # ---------- Попытка 2: парсить по ссылкам на статьи ----------
        self._log("ℹ️ JSON-LD не найден — парсим HTML вручную", "DEBUG")

        # Ищем <a href="/elektrostal/..."> с текстом заголовка
        # Ссылки на новости у regions.ru обычно вида:
        #   /elektrostal/2024/11/15/some-slug/
        #   /news/...
        candidate_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href:
                continue

            # Оставляем только внутренние ссылки, похожие на новости
            if not (href.startswith("/") or href.startswith(self.BASE_URL)):
                continue

            # Признаки статьи: длинный slug, дата в URL или категория
            is_article = (
                re.search(r"/\d{4}/\d{2}/", href)        # /2024/11/
                or "/news/" in href
                or "/elektrostal/" in href and len(href) > 25
            )
            if not is_article:
                continue

            # Заголовок — текст ссылки (или title)
            title = (a.get_text(" ", strip=True) or a.get("title") or "").strip()
            if len(title) < 15:                          # слишком коротко — не заголовок
                continue

            # Картинка — либо <img> внутри <a>, либо data-src
            img_url = ""
            img_tag = a.find("img")
            if img_tag:
                img_url = (
                    img_tag.get("src")
                    or img_tag.get("data-src")
                    or img_tag.get("data-original")
                    or ""
                )
                if img_url and img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url and img_url.startswith("/"):
                    img_url = "https://regions.ru" + img_url

            # Делаем URL абсолютным
            full_url = href if href.startswith("http") else "https://regions.ru" + href

            candidate_links.append(
                {
                    "title": title,
                    "url": full_url,
                    "image": img_url,
                    "summary": "",
                    "time": "",
                }
            )

        # Убираем дубли по URL, сохраняя порядок
        seen = set()
        unique_news = []
        for item in candidate_links:
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            unique_news.append(item)

        self._log(f"🔎 Найдено кандидатов: {len(unique_news)}")
        return unique_news[: self.MAX_NEWS]

    def _parse_jsonld(self, soup):
        """Попытка вытащить новости из JSON-LD (schema.org)"""
        items = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except Exception:
                continue

            # Может быть список или один объект
            blocks = data if isinstance(data, list) else [data]
            for block in blocks:
                if not isinstance(block, dict):
                    continue

                # ItemList с itemListElement
                if block.get("@type") == "ItemList":
                    for el in block.get("itemListElement", []):
                        item = el.get("item") if isinstance(el, dict) else None
                        if isinstance(item, dict) and item.get("name") and item.get("url"):
                            items.append(self._jsonld_to_news(item))

                # NewsArticle напрямую
                elif block.get("@type") in ("NewsArticle", "Article"):
                    if block.get("headline") and block.get("url"):
                        items.append(
                            {
                                "title": block.get("headline", "").strip(),
                                "url": block.get("url"),
                                "image": self._extract_jsonld_image(block),
                                "summary": (block.get("description") or "").strip(),
                                "time": "",
                            }
                        )

        return items

    @staticmethod
    def _jsonld_to_news(item):
        img = ""
        image_field = item.get("image")
        if isinstance(image_field, str):
            img = image_field
        elif isinstance(image_field, dict):
            img = image_field.get("url", "")
        elif isinstance(image_field, list) and image_field:
            first = image_field[0]
            if isinstance(first, str):
                img = first
            elif isinstance(first, dict):
                img = first.get("url", "")

        return {
            "title": (item.get("name") or "").strip(),
            "url": item.get("url") or "",
            "image": img,
            "summary": (item.get("description") or "").strip(),
            "time": "",
        }

    @staticmethod
    def _extract_jsonld_image(block):
        image_field = block.get("image")
        if isinstance(image_field, str):
            return image_field
        if isinstance(image_field, dict):
            return image_field.get("url", "")
        if isinstance(image_field, list) and image_field:
            first = image_field[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("url", "")
        return ""

    # ---------- СКАЧИВАНИЕ КАРТИНОК ----------
    def _download_image(self, url, news_index):
        """
        Скачать картинку новости во временную папку.
        Возвращает локальный путь или "" при ошибке.
        """
        if not url:
            return ""
        try:
            # Определяем расширение
            ext = ".jpg"
            clean_url = url.split("?")[0]
            for e in (".jpg", ".jpeg", ".png", ".webp"):
                if clean_url.lower().endswith(e):
                    ext = e
                    break

            local_name = f"news_{news_index}{ext}"
            local_path = os.path.join(NEWS_IMAGES_DIR, local_name)

            # Если уже скачано сегодня — не качаем заново
            if os.path.exists(local_path) and (
                time.time() - os.path.getmtime(local_path) < 3600
            ):
                return local_path

            r = requests.get(url, headers=self.HEADERS, timeout=10)
            if r.status_code != 200 or not r.content:
                return ""

            with open(local_path, "wb") as f:
                f.write(r.content)

            self._log(f"🖼️ Картинка скачана: {local_name} ({len(r.content)} байт)")
            return local_path
        except Exception as e:
            self._log(f"⚠️ Не удалось скачать картинку {url}: {e}", "WARNING")
            return ""

    # ---------- ПУБЛИЧНОЕ API ----------
    def get_news(self, force_refresh=False):
        """
        Получить список новостей.

        :param force_refresh: если True — игнорируем кеш
        :return: список словарей (см. _parse_news)
        """
        # Проверка кеша
        if not force_refresh and self.last_update and self.cache:
            delta = datetime.now() - self.last_update
            if delta.total_seconds() < self.CACHE_TTL_SECONDS:
                self._log(
                    f"ℹ️ Отдаём кеш ({len(self.cache)} шт., "
                    f"возраст {int(delta.total_seconds())} сек)"
                )
                return self.cache

        # Скачиваем и парсим
        self._log("🌐 Обновляем новости с regions.ru...")
        html = self._fetch_html()
        if not html:
            self._log("⚠️ Не удалось получить HTML", "WARNING")
            return self.cache  # отдаём старый кеш, если есть

        parsed = self._parse_news(html)
        if not parsed:
            self._log("⚠️ Парсер вернул пустой список", "WARNING")
            return self.cache

        # Скачиваем картинки локально (для показа в tkinter)
        for i, item in enumerate(parsed):
            if item.get("image"):
                item["local_image"] = self._download_image(item["image"], i)
            else:
                item["local_image"] = ""

        self.cache = parsed
        self.last_update = datetime.now()
        self._save_cache_to_disk()

        self._log(f"✅ Загружено {len(parsed)} новостей")
        return self.cache


# ============================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================
news_service = NewsService()


def get_news(force_refresh=False):
    """Получить новости (глобальная функция)"""
    return news_service.get_news(force_refresh=force_refresh)


# ============================================================
# РУЧНАЯ ПРОВЕРКА
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Проверка модуля новостей")
    print("=" * 60)

    news = get_news(force_refresh=True)
    print(f"\n📰 Получено новостей: {len(news)}\n")
    for i, item in enumerate(news, 1):
        print(f"{i}. {item['title']}")
        print(f"   🔗 {item['url']}")
        if item.get("image"):
            print(f"   🖼️  {item['image']}")
        if item.get("local_image"):
            print(f"   💾 {item['local_image']}")
        print()