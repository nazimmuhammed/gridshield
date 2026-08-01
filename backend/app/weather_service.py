"""
GridShield - Live Weather Polling
====================================
Polls real weather data every 15 minutes. Heat stress is a documented
driver of transformer failure - this ties live conditions into the
risk narrative.
"""

import os
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
CITY = "Bengaluru"

_latest_weather = {"temp_c": None, "updated_at": None, "status": "not_yet_polled"}


def fetch_weather():
    global _latest_weather
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        _latest_weather = {
            "temp_c": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "city": CITY,
            "updated_at": datetime.utcnow().isoformat(),
            "status": "ok",
        }
        print(f"[WEATHER] Updated: {_latest_weather['temp_c']}°C in {CITY}")
    except Exception as e:
        _latest_weather["status"] = f"error: {e}"
        print(f"[WEATHER] Fetch failed: {e}")


def get_latest_weather():
    return _latest_weather


def start_weather_polling():
    fetch_weather()
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_weather, "interval", minutes=15)
    scheduler.start()
    return scheduler