import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from gtfs_realtime_pb2 import FeedMessage  # из gtfs-realtime-bindings

STOP_ID = "70037"  # Sant Cugat Centre
WIDTH, HEIGHT = 1072, 1448
MARGIN = 60
ROW_HEIGHT = 160

def timer_text(dep_time):
    delta = dep_time - datetime.now()
    mins = int(delta.total_seconds() / 60)
    if mins <= 0:
        return "Сейчас"
    elif mins < 60:
        return f"{mins} мин"
    else:
        return f"{mins // 60} ч"

def fetch_gtfs():
    url = "https://dadesobertes.fgc.cat/gtfs-realtime/trip-updates"
    r = requests.get(url, timeout=10)
    r.raise_for_status()

    feed = FeedMessage()
    feed.ParseFromString(r.content)
    return feed

def parse_trains(feed):
    trains = []
    now = datetime.now()

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        tu = entity.trip_update
        route_id = tu.trip.route_id

        if route_id not in ("S1", "S2"):
            continue

        direction_id = getattr(tu.trip, "direction_id", 0)

        if route_id == "S1":
            direction = "Barcelona" if direction_id == 0 else "Terrassa"
        else:
            direction = "Barcelona" if direction_id == 0 else "Sabadell"

        for stu in tu.stop_time_update:
            if stu.stop_id != STOP_ID:
                continue
            if not stu.HasField("arrival"):
                continue

            arrival_time = datetime.fromtimestamp(stu.arrival.time)
            if arrival_time <= now:
                continue

            trains.append((direction, arrival_time))
            break

    trains.sort(key=lambda x: x[1])
    return trains[:6]

def generate_image(trains):
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 70)
        dir_font = ImageFont.truetype("DejaVuSans.ttf", 80)
        time_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
        logo_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 50)
    except:
        title_font = dir_font = time_font = logo_font = ImageFont.load_default()

    # Лого
    logo_w, logo_h = 260, 90
    logo_x, logo_y = WIDTH - MARGIN - logo_w, 40
    draw.rectangle([logo_x, logo_y, logo_x + logo_w, logo_y + logo_h], fill=0)
    draw.text((logo_x + 20, logo_y + 15), "FGC", fill=255, font=logo_font)

    # Станция
    y = 150
    draw.text((MARGIN, y), "Sant Cugat Centre", fill=0, font=title_font)
    y += 170

    # Поезда
    for direction, t in trains:
        time_str = timer_text(t)

        draw.text((MARGIN, y), direction, fill=0, font=dir_font)

        bbox = draw.textbbox((0, 0), time_str, font=time_font)
        time_w = bbox[2] - bbox[0]
        x_time = WIDTH - MARGIN - time_w

        draw.text((x_time, y - 10), time_str, fill=0, font=time_font)
        y += ROW_HEIGHT

    img.save("fgc_sant_cugat_pocketbook.png")

def main():
    try:
        feed = fetch_gtfs()
        trains = parse_trains(feed)
        if not trains:
            raise Exception("No realtime trains")
    except:
        now = datetime.now()
        trains = [
            ("Barcelona", now + timedelta(minutes=3)),
            ("Barcelona", now + timedelta(minutes=7)),
            ("Terrassa", now + timedelta(minutes=12)),
            ("Sabadell", now + timedelta(minutes=18)),
            ("Barcelona", now + timedelta(minutes=25)),
            ("Sabadell", now + timedelta(minutes=31))
        ]

    generate_image(trains)

if __name__ == "__main__":
    main()
