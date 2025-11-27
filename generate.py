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
        data = r.json()
    except Exception as e:
        print("FGC API error:", e)
        return trains

    departures = data.get("departures", [])
    for dep in departures[:6]:  # только 6 строк
        line = dep.get("line", "")
        dest = dep.get("destination", "")
        mins = dep.get("minutes", None)

        if not line or not dest or mins is None:
            continue

        direction = f"{line} → {dest}"
        trains.append((direction, mins))

    return trains


# ============================
# Генерация изображения
# ============================

def generate_image(trains):
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype(FONT_BOLD, 80)
    font_time = ImageFont.truetype(FONT_REG, 40)
    font_train = ImageFont.truetype(FONT_REG, 60)

    # Заголовок
    draw.text((40, 40), "Sant Cugat Centre", font=font_title, fill="black")

    # Линия
    draw.line((40, 150, WIDTH - 40, 150), fill="black", width=4)

    # Время обновления
    now = datetime.now().strftime("%H:%M")
    draw.text((40, 160), f"Обновлено: {now}", font=font_time, fill="gray")

    # Список поездов
    y = 260
    for direction, mins in trains:
        draw.text((40, y), direction, font=font_train, fill="black")

        right = "Сейчас" if mins == 0 else f"{mins} мин"

        w, _ = draw.textsize(right, font=font_train)
        draw.text((WIDTH - 60 - w, y), right, font=font_train, fill="black")

        y += 120

    img.save(OUTPUT_FILE)
    print("Saved", OUTPUT_FILE)


# ============================
# Главная логика
# ============================

if __name__ == "__main__":
    trains = get_trains()

    # Если поездов меньше 6 — добавляем пустые строки
    while len(trains) < 6:
        trains.append(("—", 0))

    generate_image(trains)
