import requests
from google.transit import gtfs_realtime_pb2
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

STOP_ID = "70037"
IMAGE_PATH = "fgc_sant_cugat_pocketbook.png"
WIDTH, HEIGHT = 1072, 1448
MARGIN = 60
ROW_HEIGHT = 160

# -------- GTFS REALTIME ----------
def fetch_gtfs():
    url = "https://dadesobertes.fgc.cat/gtfs-realtime/trip-updates"
    r = requests.get(url, timeout=10)
    r.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)
    return feed


def parse_realtime(feed):
    now = datetime.now()
    departures = []

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        tu = entity.trip_update
        route = tu.trip.route_id

        if route not in ("S1", "S2"):
            continue

        direction_id = getattr(tu.trip, "direction_id", 0)

        if route == "S1":
            direction = "Barcelona" if direction_id == 0 else "Terrassa"
        else:
            direction = "Barcelona" if direction_id == 0 else "Sabadell"

        for stu in tu.stop_time_update:
            if stu.stop_id != STOP_ID:
                continue
            if not stu.HasField("arrival"):
                continue

            t_arr = datetime.fromtimestamp(stu.arrival.time)
            if t_arr <= now:
                continue

            departures.append((direction, t_arr))
            break

    departures.sort(key=lambda x: x[1])
    return departures[:6]


# -------- FALLBACK ----------
def fallback_schedule():
    now = datetime.now()
    static = {
        "Barcelona": [3, 7, 25],
        "Terrassa":  [12],
        "Sabadell":  [18, 31]
    }

    deps = []
    for direction, minutes in static.items():
        for m in minutes:
            t = now.replace(minute=m, second=0, microsecond=0)
            if t <= now:
                t += timedelta(hours=1)
            deps.append((direction, t))

    deps.sort(key=lambda x: x[1])
    return deps[:6]


# -------- IMAGE ----------
def minutes_left(dt):
    delta = dt - datetime.now()
    m = int(delta.total_seconds() / 60)
    if m <= 0:
        return "Сейчас"
    elif m < 60:
        return f"{m} мин"
    else:
        return f"{m // 60} ч"


def generate_image(deps):
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
        font_direction = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 80)
        font_time = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
        font_logo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
    except:
        font_title = font_direction = font_time = font_logo = ImageFont.load_default()

    # ЛОГО
    logo_w, logo_h = 260, 90
    draw.rectangle([WIDTH - MARGIN - logo_w, 40, WIDTH - MARGIN, 40 + logo_h], fill=0)
    draw.text((WIDTH - MARGIN - logo_w + 20, 40 + 15), "FGC", font=font_logo, fill=255)

    # Заголовок
    draw.text((MARGIN, 150), "Sant Cugat Centre", font=font_title, fill=0)

    # Расписание
    y = 320
    for direction, t in deps:
        timer = minutes_left(t)

        draw.text((MARGIN, y), direction, font=font_direction, fill=0)

        bbox = draw.textbbox((0, 0), timer, font=font_time)
        timer_w = bbox[2] - bbox[0]
        draw.text((WIDTH - MARGIN - timer_w, y - 10), timer, font=font_time, fill=0)

        y += ROW_HEIGHT

    img.save(IMAGE_PATH)


# -------- MAIN ----------
def main():
    try:
        feed = fetch_gtfs()
        deps = parse_realtime(feed)
        if not deps:
            deps = fallback_schedule()
    except Exception as e:
        print("REALTIME ERROR:", e)
        deps = fallback_schedule()

    generate_image(deps)
    print("PNG GENERATED:", IMAGE_PATH)


if __name__ == "__main__":
    main()

