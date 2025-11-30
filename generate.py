# generate.py — Реальное табло FGC Sant Cugat Centre (GTFS Realtime JSON, тест 30.11.2025)
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import json

STOP_ID = "70037"  # Sant Cugat Centre

FALLBACK = {
    "S1 → Barcelona": [5, 15, 25, 35, 45, 55],
    "S1 ← Terrassa":  [2, 12, 22, 32, 42, 52],
    "S2 → Barcelona": [8, 18, 28, 38, 48, 58],
    "S2 ← Sabadell":  [0, 10, 20, 30, 40, 50],
}

def get_realtime():
    try:
        url = "https://fgc.opendatasoft.com/api/records/1.0/search/?dataset=trip-updates-gtfs_realtime&q=&rows=50&facet=route_id&facet=stop_id&refine.stop_id=" + STOP_ID + "&refine.route_id=S1 OR refine.route_id=S2"
        r = requests.get(url, timeout=15).json()
        
        deps = []
        now = datetime.now()
        for record in r.get("records", []):
            fields = record["fields"]
            if "arrival_time" in fields:
                arrival = datetime.fromtimestamp(fields["arrival_time"])
                if arrival > now:
                    line = fields.get("route_id", "S?")
                    direction = "Barcelona" if "Barcelona" in str(fields) else "Terrassa/Sabadell"
                    deps.append({"line": line, "direction": direction, "time": arrival})
        
        deps.sort(key=lambda x: x["time"])
        return deps[:6] if deps else None
    except Exception as e:
        print(f"API error: {e}")
        return None

def get_fallback():
    now = datetime.now()
    hour = now.hour
    peak = 7 <= hour <= 9 or 17 <= hour <= 19
    step = 5 if peak else 10

    deps = []
    base = list(range(0, 60, step))
    offsets = {"S1": 2, "S2": 8}

    for line, offset in offsets.items():
        mins = [(m + offset) % 60 for m in base]
        for m in mins:
            t = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=m)
            if t <= now:
                t += timedelta(hours=1)
            if t < now + timedelta(hours=2):
                direction = "Barcelona" if m < 30 else "Terrassa/Sabadell"
                deps.append({"line": line, "direction": direction, "time": t})
    deps.sort(key=lambda x: x["time"])
    return deps[:6]

def timer(t):
    mins = int((t - datetime.now()).total_seconds() / 60)
    return "Сейчас!" if mins <= 0 else f"Осталось: {mins}м"

def generate():
    data = get_realtime()
    deps = data if data else get_fallback()

    img = Image.new("RGB", (1072, 1448), "white")
    draw = ImageDraw.Draw(img)
    try:
        f1 = ImageFont.truetype("DejaVuSans-Bold.ttf", 50)
        f2 = ImageFont.truetype("DejaVuSans.ttf", 50)
        f3 = ImageFont.truetype("DejaVuSans-Bold.ttf", 50)
    except:
        f1 = f2 = f3 = ImageFont.load_default()

    y = 70
    draw.text((50, y), "FGC Sant Cugat Centre", fill=0, font=f1); y += 140
    draw.text((50, y), datetime.now().strftime("%d.%m %H:%M:%S"), fill=0, font=f2); y += 110
    draw.text((50, y), "Линия → Направление          Осталось", fill=0, font=f2); y += 120

    for d in deps:
        draw.text((50, y), f"{d['line']} → {d['direction']}", fill=0, font=f2)
        draw.text((690, y), timer(d['time']), fill=0, font=f3)
        y += 128

    img.save("fgc_sant_cugat.png")
    source = "GTFS Realtime" if data else "fallback"
    print(f"Готово! Источник: {source}")

if __name__ == "__main__":
    generate()

