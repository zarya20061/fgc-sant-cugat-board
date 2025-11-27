
import requests
from google.transit import gtfs_realtime_pb2
from PIL import Image, ImageDraw, ImageFont
import datetime

STOP_ID = "70037"  # Sant Cugat Centre
IMAGE_PATH = "fgc_sant_cugat_pocketbook.png"
WIDTH, HEIGHT = 1072, 1448
LOGO_PATH = "fgc_logo.png"

def fetch_gtfs():
    url = "https://dadesobertes.fgc.cat/gtfs-realtime/trip-updates"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed

def parse_trains(feed):
    trains = []
    now = datetime.datetime.now()
    for entity in feed.entity:
        for stop_time_update in entity.trip_update.stop_time_update:
            if stop_time_update.stop_id == STOP_ID:
                arrival = stop_time_update.arrival.time
                remaining = int((arrival - now.timestamp()) / 60)
                direction = "Barcelona" if entity.trip_update.trip.direction_id == 0 else "Terrassa/Sabadell"
                trains.append((direction, remaining))
    trains.sort(key=lambda x: x[1])
    return trains[:6]

def generate_image(trains):
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
    font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)

    # Логотип
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((200, 200))
        img.paste(logo, (WIDTH - 220, 40), logo)
    except FileNotFoundError:
        draw.text((WIDTH - 300, 50), "[FGC]", font=font_subtitle, fill="black")

    # Заголовок
    draw.text((50, 50), "Sant Cugat Centre", font=font_title, fill="black")
    draw.line((50, 150, WIDTH - 50, 150), fill="black", width=4)

    # Время обновления
    now_str = datetime.datetime.now().strftime("%H:%M")
    draw.text((50, 160), f"Обновлено: {now_str}", font=font_subtitle, fill="gray")

    # Список поездов
    y = 250
    for direction, mins in trains:
        time_str = "Сейчас" if mins <= 0 else f"{mins} мин"
        draw.text((50, y), f"{direction:<15} {time_str}", font=font_text, fill="black")
        y += 100

    img.save(IMAGE_PATH)

def main():
    try:
        feed = fetch_gtfs()
        trains = parse_trains(feed)
        if not trains:
            trains = [("Нет данных", 0)] * 6
    except Exception:
        trains = [("Резерв", i*10) for i in range(6)]
    generate_image(trains)

if __name__ == "__main__":
    main()
