import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ============================
# Настройки
# ============================

WIDTH = 1072
HEIGHT = 1448

STATION_ID = "081822"  # Sant Cugat Centre FGC
UA = {"User-Agent": "Mozilla/5.0 (PocketBookTablo)"}

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

OUTPUT_FILE = "fgc_sant_cugat_pocketbook.png"


# ============================
# Получение поездов FGC
# ============================

def get_trains():
    url = f"https://api.geotren.es/fgc/station/{STATION_ID}"
    trains = []

    try:
        r = requests.get(url, headers=UA, timeout=10)
        r.raise_for_status()
        data = r.

