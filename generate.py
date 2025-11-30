# generate.py — FGC Sant Cugat Centre (аккуратные шрифты, без наездов)
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

STOP_ID = "70037"

def get_realtime():
    try:
        url = "https://fgc.opendatasoft.com/api/records/1.0/search/?dataset=trip-updates-gtfs_realtime&q=&rows=50&refine.stop_id=" + STOP_ID
        r = requests.get(url, timeout=15).json()
        deps = []
        now = datetime.now()
        for rec in r.get("records", []):
            f = rec["fields"]
            if "arrival_time" in f:
                arr = datetime.fromtimestamp(f["arrival_time"])
                if arr > now - timedelta(minutes=1):
                    line = f.get("route_id", "S?")
                    direction = "Barcelona" if "plaça" in str(f).lower() else "Terrassa/Sabadell"
                    deps.append({"line": line, "direction": direction, "time": arr})
        deps.sort(key=lambda x: x["time"])
        return deps[:6] if deps else None
    except:
        return None

def get_fallback():
    now = datetime.now()
    peak = 7 <= now.hour <= 9 or 17 <= now.hour <= 19
    step = 5 if peak else 10
    deps = []
    base = list(range(0, 60, step))
    offsets = {"S1": 2, "S2": 8}
    for line, offset in offsets.items():
        for m in [(m + offset) % 60 for m in base]:
            t = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=m)
            if t <= now: t += timedelta(hours=1)
            if t < now + timedelta(hours=2):
                direction = "Barcelona" if m < 30 else "Terrassa/Sabadell"
                deps.append({"line": line, "direction": direction, "time": t})
    deps.sort(key=lambda x: x["time"])
    return deps[:6]

def timer(t):
    mins = int((t - datetime.now()).total_seconds() / 60)
    return "Сейчас!" if mins <= 0 else f"{mins} мин"

data = get_realtime()
deps = data if data else get_fallback()

img = Image.new("RGB", (1072, 1448), "white")
draw = ImageDraw.Draw(img)

try:
    title = ImageFont.truetype("DejaVuSans-Bold.ttf", 60)  # заголовок поменьше
    text  = ImageFont.truetype("DejaVuSans.ttf", 45)       # линии
    timef = ImageFont.truetype("DejaVuSans-Bold.ttf", 55)  # таймер
except:
    title = text = timef = ImageFont.load_default()

y = 50  # начало выше
draw.text((50, y), "FGC Sant Cugat Centre", fill=0, font=title); y += 120  # больше отступ
draw.text((50, y), datetime.now().strftime("%d.%m %H:%M"), fill=0, font=text); y += 80

for d in deps:
    draw.text((50, y), f"{d['line']} → {d['direction']}", fill=0, font=text)
    draw.text((950, y), timer(d['time']), fill=0, font=timef)  # x=950, чтобы не уплывало
    y += 90  # меньше отступ между строками, но достаточно

img.save("fgc_sant_cugat.png")
print("Готово!")
