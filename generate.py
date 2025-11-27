#!/usr/bin/env python3
"""
Улучшенный скрипт для FGC табло на PocketBook 632 (E Ink оптимизация).
"""

import csv
import io
import logging
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from typing import List, Dict, Optional

import requests
from PIL import Image, ImageDraw, ImageFont
import gtfs_realtime_pb2

# Настройка
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STATION_NAME = os.getenv('STATION_NAME', 'Sant Cugat Centre')
GTFS_STATIC_URL = 'https://dadesobertes.fgc.cat/gtfs/google_transit.zip'
GTFS_RT_URL = 'https://dadesobertes.fgc.cat/gtfs_rt/trip_updates'
OUTPUT_FILE = 'board.png'
IMAGE_SIZE = (800, 600)  # Landscape для PocketBook 632 6"
MAX_TRAINS = 10
NEXT_HOURS = 1

# E Ink режим (по умолчанию)
EINK_MODE = os.getenv('EINK_MODE', '1').lower() == '1'

session = requests.Session()
session.headers.update({'User-Agent': 'FGC-Board-PB632/1.0'})

# Функции fetch без изменений (get_stop_id, fetch_trains, retry_request) — копируйте из предыдущего

def retry_request(url: str, max_retries: int = 3, timeout: int = 10) -> Optional[bytes]:
    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            logger.warning(f"Попытка {attempt+1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    logger.error(f"Failed {url}")
    return None

def get_stop_id(station_name: str) -> Optional[str]:
    data = retry_request(GTFS_STATIC_URL)
    if not data:
        return None
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        with z.open('stops.txt') as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
            for row in reader:
                if station_name.lower() in row['stop_name'].lower():
                    logger.info(f"Stop_id: {row['stop_id']}")
                    return row['stop_id']
    except Exception as e:
        logger.error(f"stops.txt error: {e}")
    return None

def fetch_trains(stop_id: str) -> List[Dict[str, str]]:
    data = retry_request(GTFS_RT_URL)
    if not data:
        return []
    try:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(data)
        trains = []
        now_ts = datetime.now(timezone.utc).timestamp()
        end_ts = now_ts + (NEXT_HOURS * 3600)
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                tu = entity.trip_update
                for stu in tu.stop_time_update:
                    if (stu.stop_id == stop_id and
                        stu.HasField('arrival') and
                        stu.arrival.time > now_ts and stu.arrival.time < end_ts):
                        headsign = tu.trip.headsign or tu.trip.route_id or 'Unknown'
                        route_type = tu.trip.route_id.split('_')[-1] if '_' in tu.trip.route_id else ''
                        arr_time = datetime.fromtimestamp(stu.arrival.time, tz=timezone.utc).strftime('%H:%M')
                        trains.append({'time': arr_time, 'dir': headsign, 'type': route_type})
        trains.sort(key=lambda t: t['time'])
        logger.info(f"{len(trains)} поездов")
        return trains[:MAX_TRAINS]
    except Exception as e:
        logger.error(f"GTFS-RT error: {e}")
        return []

def generate_image(trains: List[Dict[str, str]], station: str):
    """Генерация оптимизированная под E Ink PocketBook 632."""
    if EINK_MODE:
        # B/W bitmap для E Ink (black=0, white=255)
        img = Image.new('1', IMAGE_SIZE, 0)  # Black background
        text_color = 255  # White
        logger.info("E Ink B/W mode")
    else:
        # Цветной preview
        img = Image.new('RGB', IMAGE_SIZE, 'black')
        text_color = 'white'

    draw = ImageDraw.Draw(img)

    # Шрифты (DejaVu — чёткие на E Ink)
    try:
        font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 64)
        font_med = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 48)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 32)
    except:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Заголовок (центр)
    bbox = draw.textbbox((0, 0), station, font=font_med)
    text_w = bbox,[object Object], - bbox,[object Object],
    draw.text((IMAGE_SIZE,[object Object], // 2 - text_w // 2, 20), station, fill=text_color, font=font_med)

    # Поезда: слева время (жирное), справа направление (right align)
    y = 130
    line_height = 90
    for train in trains:
        time_text = train['time']
        dir_text = f"{train['dir']} {train['type']}".strip() or '---'

        # Время слева
        bbox_time = draw.textbbox((0, 0), time_text, font=font_large)
        draw.text((60, y), time_text, fill=text_color, font=font_large)

        # Направление справа (anchor right в Pillow 10+ или calc)
        bbox_dir = draw.textbbox((0, 0), dir_text, font=font_med)
        dir_w = bbox_dir,[object Object], - bbox_dir,[object Object],
        right_x = IMAGE_SIZE,[object Object], - 60 - dir_w
        draw.text((right_x, y), dir_text, fill=text_color, font=font_med)

        y += line_height
        if y > IMAGE_SIZE,[object Object], - 120:
            break

    # Нет данных (центр, жирное)
    if not trains:
        no_data = "No trains"
        bbox = draw.textbbox((0, 0), no_data, font=font_large)
        text_w = bbox,[object Object], - bbox,[object Object],
        draw.text((IMAGE_SIZE,[object Object], // 2 - text_w // 2, IMAGE_SIZE,[object Object], // 2), no_data, fill=text_color, font=font_large)

    # Футер: дата/время (центр, мелкий)
    now_str = datetime.now().strftime('%d.%m %H:%M')
    bbox = draw.textbbox((0, 0), now_str, font=font_small)
    text_w = bbox,[object Object], - bbox,[object Object],
    draw.text((IMAGE_SIZE,[object Object], // 2 - text_w // 2, IMAGE_SIZE,[object Object], - 70), now_str, fill=text_color, font=font_small)

    # Сохранить (lossless PNG)
    img.save(OUTPUT_FILE, optimize=True, bits=1 if EINK_MODE else 8)
    logger.info(f"Сохранено {OUTPUT_FILE} ({'E Ink B/W' if EINK_MODE else 'Color'})")

def main():
    logger.info("Генерация табло для PocketBook 632...")
    stop_id = get_stop_id(STATION_NAME)
    if not stop_id:
        logger.error("Stop_id не найден!")
        sys.exit(1)
    trains = fetch_trains(stop_id)
    generate_image(trains, STATION_NAME)
    logger.info("Готово! Перенесите board.png на PocketBook.")

if __name__ == "__main__":
    main()
