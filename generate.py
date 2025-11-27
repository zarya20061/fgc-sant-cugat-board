import requests
from gtfs_realtime_bindings import FeedMessage
from PIL import Image, ImageDraw, ImageFont
import datetime

STOP_ID = "70037"  # Sant Cugat Centre
IMAGE_PATH = "fgc_sant_cugat_pocketbook.png"
WIDTH, HEIGHT = 1072, 1448

def fetch_gtfs():
    url = "https://dadesobertes.fgc.cat/gtfs-realtime/trip-updates"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    feed = FeedMessage()
    feed.ParseFromString(response.content)
    return feed

def parse_trains(feed):
    trains = []
    now = datetime.datetime.now()

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        trip = entity.trip_update.trip

        # Без direction_id пропускаем (бывает)
        direction_id = getattr(trip, "direction_id", None)
        if direction_id is None:
            continue

        # Линия
        route = trip.route_id
        if route not in ("S1", "S2"):
            continue

        # Логика направлений
        if route == "S1":
            direction = "Barcelona" if direction_id == 0 else "Terrassa"
        else:  # S2
            direction = "Barcelona" if direction_id == 0 else "Sabadell"

        # Парсим времена
        for stu in entity.trip_update.stop_time_update:
            if stu.stop_id != STOP_ID:
                continue

            if not stu.HasField("arrival"):
                continue

            arrival_time = stu.arrival.time
            mins = int((arrival_time - now.timestamp()) / 60)

            trains.append((direction, mins))

    trains.sort(key=lambda x: x[1])
    return trains[:6]

def generate_image(trains):
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Универсальный безопасный шрифт
    font_title = ImageFont.load_default()
    font_text = ImageFont.load_default()

    # Лого FGC
    draw.rectangle((WIDTH - 260, 40, WIDTH - 20, 130), fill=0)
    draw.text((WIDTH - 240, 65), "FGC", fill=255, font=font_title)

    # Название станции
    draw.text((50, 50), "Sant Cugat Centre", fill=0, font=font_title)

    # Линия под заголовком
    draw.line((50, 150, WIDTH - 50, 150), fill=0, width=3)

    # Время обновления
    now_str = datetime.datetime.now().strftime("%H:%M")
    draw.text((50, 160), f"Обновлено: {now_str}", fill=0, font=font_title)

    # Список поездов
    y = 250
    for direction, mins in trains:
        if mins <= 0:
            t = "Сейчас"
        else:
            t = f"{mins} мин"

        draw.text((50, y), f"{direction}: {t}", fill=0, font=font_text)
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
