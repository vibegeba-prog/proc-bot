#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
УК "Процион" — Telegram-канал ЖК Мурино
---------------------------------------
Автоматические посты в канал:
  • Утро (8:45) — каждый будний день: погода + тёплое слово
  • Вечер (20:30) — каждый будний день: закат + пожелание
    (если солнце уже село в 20:30, пишем без упоминания времени)

Локация: ЖК Мурино, Воронцовский бульвар 5 и 9, Бугры

Запуск:
  python proccion_bot.py --mode morning
  python proccion_bot.py --mode evening

Переменные окружения:
  TELEGRAM_BOT_TOKEN  — токен бота от @BotFather
  TELEGRAM_CHANNEL_ID — @username канала или числовой ID
  OPENWEATHER_KEY     — ключ OpenWeatherMap
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime
from pathlib import Path

import requests

# ============================================================
# 1. НАСТРОЙКИ
# ============================================================

TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
OPENWEATHER_KEY     = os.environ.get("OPENWEATHER_KEY", "")

COMPLEX_NAME = "ЖК Мурино"
STREET       = "Воронцовский бульвар"
AREA         = "Бугры"
CITY_RU      = "Мурино"

LAT = 60.0513
LON = 30.4467

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

LOG_FILE = DATA_DIR / "posts_log.jsonl"

# ============================================================
# 2. ПОГОДА
# ============================================================

def get_weather():
    """Получает текущую погоду в районе ЖК Мурино."""
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={LAT}&lon={LON}&appid={OPENWEATHER_KEY}&units=metric&lang=ru"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        return {
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "description": data["weather"][0]["description"],
            "wind_speed": round(data["wind"]["speed"]),
            "humidity": data["main"]["humidity"],
        }
    except Exception as e:
        print(f"[ERROR] Не удалось получить погоду: {e}")
        return None


def weather_to_emoji(desc: str) -> str:
    desc = desc.lower()
    mapping = {
        "ясно": "☀️", "солнечно": "☀️", "clear": "☀️",
        "облачно": "☁️", "пасмурно": "☁️", "clouds": "☁️",
        "дождь": "🌧️", "ливень": "🌧️", "rain": "🌧️",
        "гроза": "⛈️", "thunderstorm": "⛈️",
        "снег": "❄️", "снегопад": "❄️", "snow": "❄️",
        "туман": "🌫️", "mist": "🌫️", "fog": "🌫️",
        "малооблачно": "🌤️", "переменная облачность": "⛅",
    }
    for key, emoji in mapping.items():
        if key in desc:
            return emoji
    return "🌡️"


# ============================================================
# 3. ЗАКАТ
# ============================================================

def get_sunset():
    """Получает время заката в районе ЖК Мурино."""
    url = (
        f"https://api.sunrise-sunset.org/json"
        f"?lat={LAT}&lng={LON}&formatted=0"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()["results"]
        sunset_utc = datetime.fromisoformat(data["sunset"].replace("Z", "+00:00"))
        sunset_local = sunset_utc.astimezone()
        return sunset_local.strftime("%H:%M")
    except Exception as e:
        print(f"[ERROR] Не удалось получить закат: {e}")
        return None


def sunset_already_passed(sunset_time: str) -> bool:
    """Проверяет, село ли солнце раньше текущего времени."""
    try:
        sunset_h, sunset_m = map(int, sunset_time.split(":"))
        sunset_dt = datetime.now().replace(hour=sunset_h, minute=sunset_m, second=0, microsecond=0)
        return datetime.now() > sunset_dt
    except Exception:
        return False


# ============================================================
# 4. УТРЕННИЕ ПОСТЫ
# ============================================================

def generate_morning_post(weather: dict) -> str:
    """Генерирует утренний пост для ЖК Мурино."""
    temp = weather["temp"]
    feels = weather["feels_like"]
    desc = weather["description"]
    wind = weather["wind_speed"]
    emoji = weather_to_emoji(desc)

    templates = []

    if "дождь" in desc or "ливень" in desc or "гроза" in desc:
        templates = [
            f"{emoji} За окнами {COMPLEX_NAME} — дождь, +{temp}° (по ощущениям +{feels}°). Не забудьте зонт, а если едете на авто — будьте аккуратны на подъездах к бульвару. Хорошего дня!",
            f"{emoji} Дождливое утро в {AREA}, +{temp}°. Захватите сменную обувь, а мы пока будем надеяться, что к обеду разойдётся. Удачного дня!",
        ]
    elif "снег" in desc or "снегопад" in desc:
        templates = [
            f"{emoji} Снегопад в {AREA}, +{temp}°. На {STREET} уже бело — будьте осторожны на дорогах и не спешите. Тёплого вам дня!",
            f"{emoji} Белое утро в {COMPLEX_NAME}, +{temp}°. Снег красивый, но скользкий. Выходите из дома в удобной обуви. Всего хорошего!",
        ]
    elif temp >= 25:
        templates = [
            f"{emoji} Жара на {STREET}: +{temp}°! Отличный повод проветрить квартиру с утра, пока не началась дневная жара. Пейте больше воды. Продуктивного дня!",
            f"{emoji} +{temp}° — лето в разгаре. Идеальный день для вечерней прогулки по {AREA}, а пока — тень и прохлада. Бодрого дня!",
        ]
    elif temp >= 18:
        templates = [
            f"{emoji} +{temp}° — погода, ради которой стоит проснуться пораньше. Ветер {wind} м/с, на {STREET} сейчас особенно свежо. Прекрасного дня!",
            f"{emoji} Прекрасное утро в {COMPLEX_NAME}: +{temp}°. Окна на запад открывайте сейчас — до обеда будет прохладно и тихо. Всего хорошего!",
        ]
    elif temp >= 10:
        templates = [
            f"{emoji} Прохладно, +{temp}°, {desc}. Ветер {wind} м/с — наденьте кофту. Ничего, скоро лето. Приятного дня!",
            f"{emoji} +{temp}° в {AREA}. Свежо, как после дождя. Чашка кофе — и вперёд. Бодрого дня!",
        ]
    elif temp >= 0:
        templates = [
            f"{emoji} Холодное утро на {STREET}: +{temp}°. Не забудьте шапку — ветер {wind} м/с. Подъезды тёплые, лифты работают. Удачного дня!",
            f"{emoji} +{temp}° — пора доставать пальто. Тёплый кофе, любимый шарф — и вперёд. Продуктивного дня!",
        ]
    else:
        templates = [
            f"{emoji} Морозное утро, {temp}°. Проверьте, закрыты ли окна, и одевайтесь потеплее. Берегите себя!",
            f"{emoji} {temp}° — настоящий мороз. Тёплый чай и хорошее настроение — лучшая защита от холода. Согревающего дня!",
        ]

    post = random.choice(templates)
    post = post + "\n\n" + "#УКПроцион #ЖКМурино #Бугры #Мурино #погода"
    return post


# ============================================================
# 5. ВЕЧЕРНИЕ ПОСТЫ
# ============================================================

def generate_evening_post(sunset_time: str | None) -> str:
    """Генерирует вечерний пост для ЖК Мурино."""

    if sunset_time and sunset_already_passed(sunset_time):
        templates = [
            f"🌙 Вечер на {STREET}. Надеемся, ваш день прошёл хорошо. Завтра встретимся снова — в 8:45. Тихой ночи!",
            f"🌃 {COMPLEX_NAME} засыпает. Если вы ещё на работе — скорее домой, тут тепло и уютно. До завтра!",
            f"🌆 Вечер в {AREA}. Окна горят тёплым светом — приятно смотреть с улицы. Отдохните хорошо. Ваш УК Процион.",
            f"⭐ Небо над {AREA} уже тёмное. Время чая, книги или любимого сериала. Завтра новый день. Спокойной ночи!",
            f"🌙 {STREET} тихий и спокойный. Мы желаем вам тёплого пледа и сладких снов. До встречи утром!",
        ]
        post = random.choice(templates)
        post = post + "\n\n" + "#УКПроцион #ЖКМурино #Бугры #Мурино #вечер"
        return post

    if sunset_time:
        templates = [
            f"🌅 Сегодня солнце сядет в {sunset_time}. Если у вас окна на запад — остановитесь на минутку: вид с {STREET} в этот час стоит того. Доброй ночи!",
            f"🌇 Закат сегодня в {sunset_time}. Рабочий день позади — время для себя и близких. Отдохните хорошо, завтра встретимся снова.",
            f"🌙 Сегодняшний закат в {sunset_time}. Вечера в {AREA} становятся уютнее с каждым днём. Желаем вам тёплого пледа, чая и сладких снов.",
            f"🌆 Закат в {sunset_time}. Прогуляйтесь вечером по {STREET} — свежий воздух после жаркого дня и красивый небосвод. Приятного вечера!",
            f"🌠 Сегодня солнце сядет в {sunset_time}. Если вы ещё в дороге — не спешите: небо над {AREA} сейчас особенное. Тихой ночи, {COMPLEX_NAME}!",
        ]
    else:
        templates = [
            f"🌙 Вечер на {STREET}. Надеемся, ваш день прошёл хорошо. Завтра встретимся снова — в 8:45. Тихой ночи!",
            f"🌃 {COMPLEX_NAME} засыпает. Если вы ещё на работе — скорее домой, тут тепло и уютно. До завтра!",
            f"🌆 Вечер в {AREA}. Окна горят тёплым светом — приятно смотреть с улицы. Отдохните хорошо. Ваш УК Процион.",
        ]

    post = random.choice(templates)
    post = post + "\n\n" + "#УКПроцион #ЖКМурино #Бугры #Мурино #вечер"
    return post


# ============================================================
# 6. TELEGRAM API
# ============================================================

def post_to_telegram(text: str, token: str, channel_id: str) -> bool:
    """Публикует пост в Telegram-канал."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, data=payload, timeout=20)
        r.raise_for_status()
        result = r.json()
        if not result.get("ok"):
            print(f"[ERROR] Telegram API ошибка: {result}")
            return False
        print(f"[OK] Пост опубликован в канал {channel_id}")
        return True
    except Exception as e:
        print(f"[ERROR] Не удалось опубликовать: {e}")
        return False


# ============================================================
# 7. ЛОГИРОВАНИЕ
# ============================================================

def log_post(mode: str, text: str, success: bool):
    """Записывает информацию о посте в лог."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "text_preview": text[:120],
        "success": success,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================
# 8. ГЛАВНАЯ ЛОГИКА
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="УК Процион — ЖК Мурино")
    parser.add_argument("--mode", choices=["morning", "evening"], required=True,
                        help="Режим: morning (8:45) или evening (20:30)")
    args = parser.parse_args()

    if not TELEGRAM_BOT_TOKEN:
        print("[FATAL] Задайте TELEGRAM_BOT_TOKEN!")
        sys.exit(1)
    if not TELEGRAM_CHANNEL_ID:
        print("[FATAL] Задайте TELEGRAM_CHANNEL_ID!")
        sys.exit(1)

    today = datetime.now()
    weekday = today.weekday()
    print(f"[{today.strftime('%Y-%m-%d %H:%M')}] Режим: {args.mode}")

    if args.mode == "morning":
        if OPENWEATHER_KEY:
            weather = get_weather()
            if weather:
                text = generate_morning_post(weather)
            else:
                text = "☀️ Всем, кто проснулся на " + STREET + ", — чудесного дня и отличного настроения. Ваш УК Процион.\n\n#УКПроцион #ЖКМурино #Бугры #Мурино"
        else:
            print("[WARN] Нет ключа OpenWeather — пост без погоды")
            text = "☀️ Всем, кто проснулся на " + STREET + ", — чудесного дня и отличного настроения. Ваш УК Процион.\n\n#УКПроцион #ЖКМурино #Бугры #Мурино"

        success = post_to_telegram(text, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)
        log_post("morning", text, success)
        return

    if args.mode == "evening":
        sunset = get_sunset()
        if sunset:
            print(f"[INFO] Закат сегодня в {sunset}")
            if sunset_already_passed(sunset):
                print("[INFO] Солнце уже село — пост без времени заката")
            else:
                print("[INFO] Солнце ещё не село — пишем с временем заката")

        text = generate_evening_post(sunset)
        success = post_to_telegram(text, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)
        log_post("evening", text, success)
        return


if __name__ == "__main__":
    main()
