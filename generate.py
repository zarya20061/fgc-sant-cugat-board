import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ============================
# Настройки
# ============================

WIDTH = 1072
HEIGHT = 1448

STATION_ID = "081822"  # Sant Cugat Centre FGC

# MET.NO погода (без API-ключей)
WEATHER_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=41.47&lon=2.08"

UA = {"User-Agent": "Mozilla/5.0 (PocketBookTablo)"}

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

OUTPUT_FILE = "fgc_sant_cugat_pocketbook.png"


# ============================
# Получение погоды
# ============================

def get_weather():
    try:
        r = requests.get(WEATHER_URL, headers=UA, timeout=10)
        r.raise_for_status()
        data = r.json()

        temp = data["properties"]["timeseries"][0]["data"]["instant"]["details"]["air_temperature"]

        # Пытаемся получить "ясно/облачно/дождь"
        symbol = "—"
        try:
            wx = data["properties"]["timeseries"][0]["data"]["next_1_hours"]["summary"]["symbol_code"]
            if "clearsky" in wx:
                symbol = "☀"
            elif "cloud" in wx:
                symbol = "☁"
            elif "rain" in wx:
                symbol = "🌧"
            elif "snow" in wx:
                symbol = "❄"
        except:
            pass

        return f"{temp:.0f}°C", symbol

    except Exception as e:
        print("Weather error:", e
