#!/usr/bin/env python3
"""
FGC Sant Cugat Centre board для PocketBook 632 (E Ink B/W оптимизация).
Полный, устойчивый код без зависимостей от scraping.
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

# Логи
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Конфиг
STATION_NAME = os.getenv('STATION_NAME', 'Sant Cugat Centre')
GTFS_STATIC_URL = 'https://dadesobertes.fgc.cat/gtfs/google_transit.zip'
GTFS_RT_URL = 'https://dadesobertes.fgc.cat/gtfs_rt/trip_updates'
OUTPUT_FILE = 'board.png'
IMAGE_SIZE = (800, 600)  # 6" landscape для PB 632
MAX_TRAINS = 10
NEXT_HOURS = 1
EINK_MODE = os.getenv('EINK_MODE', '1').lower() == '1'

session = requests.Session()
session.headers.update({'User-Agent': 'FGC-PB632/1.0'})

def retry_request(url: str, max_retries: int = 3, timeout: int = 10) -> Optional[bytes]:
    """Запрос с retries и обработкой ошибок."""
    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            logger.warning(f"Попытка {attempt + 1} failed для {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    logger.error(f"Все retries failed: {url}")
    return None

def get_stop_id(station_name: str) -> Optional[str]:
    """Stop_id из static GTFS."""
    data = retry_request(GTFS_STATIC_URL)
    if not data:
        logger.error("Static GTFS недоступен")
        return None
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        with z.open('stops.txt') as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
            for row in reader:
                if station_name.lower() in row['stop_name'].lower():
                    logger.info(f"Stop_id '{row['stop_id']}' для '{row['stop_name']}'")
                    return row['stop_id']
        logger.warning(f"Станция '{station_name}' не найдена")
    except Exception as e:
        logger.error(f"Ошибка stops.txt: {e}")
    return None

def fetch_trains(stop_id: str) -> List[Dict[str, str]]:
    """Поезда из GTFS-RT (следующий час)."""
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
                        now_ts < stu.arrival.time < end_ts):
                        headsign = tu.trip.headsign or tu.trip.route_id or '---'
                        route_type = tu.trip.route_id.split('_')[-1] if '_' in tu.trip.route_id else ''
                        arr_time = datetime.fromtimestamp(stu.arrival.time, tz=timezone.utc).strftime('%H:%M')
                        trains.append({
                            'time': arr_time,
                            'dir': headsign,
                            'type': route_type
                        })
        trains.sort(key=lambda t: t['time'])
        logger.info(f"Получено {len(trains)} поездов")
        return trains[:MAX_TRAINS]
    except Exception as e:
        logger.error(f"GTFS-RT парсинг: {e}")
        return []

def generate_image(trains: List[Dict[str, str]], station: str):
    """PNG для E Ink PB 632 (B/W bitmap)."""
    if EINK_MODE:
        img = Image.new('1', IMAGE_SIZE, 0)  # Black=0 bg
        text_color = 255  # White
        mode_str = "E Ink B/W"
    else:
        img = Image.new('RGB', IMAGE_SIZE, 'black')
        text_color = 'white'
        mode_str = "Color preview"

    draw = ImageDraw.Draw(img)
    logger.info(f"Режим: {mode_str}")

    # Шрифты (E Ink: жирные, крупные)
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    ]
    fonts = {}
    sizes = {'large': 64, 'med': 48, 'small': 32}
    for name, size in sizes.items():
        font = None
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, size)
                break
            except:
                pass
        if not font:
            font = ImageFont.load_default()
        fonts[name] = font

    font_large = fonts['large']
    font_med = fonts['med']
    font_small = fonts['small']

    # Заголовок центр
    bbox = draw.textbbox((0, 0), station, font=font_med)
    text_w = bbox,[object Object], - bbox,[object Object],
    draw.text((IMAGE_SIZE,[object Object], // 2 - text_w // 2, 20), station, fill=text_color, font=font_med)

    # Поезда
    y = 130
    for train in trains:
        time_text = train['time']
        dir_text = f"{train['dir']} {train['type']}".strip() or '---'

        # Время слева
        bbox_time = draw.textbbox((0, 0), time_text, font=font_large)
        draw.text((60, y), time_text, fill=text_color, font=font_large)

        # Направление справа (calc right align)
        bbox_dir = draw.textbbox((0, 0), dir_text, font=font_med)
        dir_w = bbox_dir,[object Object], - bbox_dir,[object Object],
        draw.text((IMAGE_SIZE,[object Object], - 60 - dir_w, y), dir_text, fill=text_color, font=font_med)

        y += 90

    # No data
    if not trains:
        bbox = draw.textbbox((0, 0), "No trains", font=font_large)
        text_w = bbox,[object Object], - bbox,[object Object],
        draw.text((IMAGE_SIZE,[object Object], // 2 - text_w // 2, IMAGE_SIZE,[object Object], // 2), "No trains", fill=text_color, font=font_large)

    # Футер
    now_str = datetime.now().strftime('%d.%m %H:%M')
    bbox = draw.textbbox((0, 0), now_str, font=font_small)
    text_w = bbox,[object Object], - bbox,[object Object],
    draw.text((IMAGE_SIZE,[object Object], // 2 - text_w // 2, IMAGE_SIZE,[object Object], - 70), now_str, fill=text_color, font=font_small)

    img.save(OUTPUT_FILE, ,[object Object]