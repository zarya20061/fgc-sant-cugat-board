#!/usr/bin/env python3
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
from gtfs_realtime_bindings import gtfs_realtime_pb2   # <-- ВАЖНО!

# Логи
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Конфиг
STATION_NAME = os.getenv('STATION_NAME', 'Sant Cugat Centre')
GTFS_STATIC_URL = 'https://dadesobertes.fgc.cat/gtfs/google_transit.zip'
GTFS_RT_URL = 'https://dadesobertes.fgc.cat/gtfs_rt/trip_updates'
OUTPUT_FILE = 'board.png'
IMAGE_SIZE = (800, 600)
MAX_TRAINS = 10
NEXT_HOURS = 1
EINK_MODE = os.getenv('EINK_MODE', '1').lower() == '1'

session = requests.Session()
session.headers.update({'User-Agent': 'FGC-PB632/1.0'})


def retry_request(url: str, max_retries: int = 3, timeout: int = 10) -> Optional[bytes]:
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
                    return row['stop_id']
    except Exception as e:
        logger.error(f"Ошибка stops.txt: {e}")
        return None

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
                        now_ts < stu.arrival.time < end_ts):

                        headsign = (
                            tu.trip.headsign or tu.trip.route_id or '---'
                        )
                        route_type = (
                            tu.trip.route_id.split('_')[-1]
                            if '_' in tu.trip.route_id else ''
                        )
                        arr_time = datetime.fromtimestamp(
                            stu.arrival.time,
                            tz=timezone.utc
                        ).strftime('%H:%M')

                        trains.append({
                            'time': arr_time,
                            'dir': headsign,
                            'type': route_type
                        })

        trains.sort(key=lambda t: t['time'])
        return trains[:MAX_TRAINS]

    except Exception as e:
        logger.error(f"GTFS-RT парсинг: {e}")
        return []


def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def generate_image(trains: List[Dict[str, str]], station: str):
    if EINK_MODE:
        img = Image.new('1', IMAGE_SIZE, 0)
        text_color = 255
    else:
        img = Image.new('RGB', IMAGE_SIZE, 'black')
        text_color = 'white'

    draw = ImageDraw.Draw(img)

    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    ]
    sizes = {'large': 64, 'med': 48, 'small': 32}
    fonts = {}

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

    # Заголовок
    header_w = text_width(draw, station, font_med)
    draw.text(((IMAGE_SIZE[0] - header_w) // 2, 20),
              station, fill=text_color, font=font_med)

    y = 130
    for train in trains:
        t = train['time']
        d = f"{train['dir']} {train['type']}".strip()

        # время
        draw.text((60, y), t, fill=text_color, font=font_large)

        # направление
        dir_w = text_width(draw, d, font_med)
        draw.text((IMAGE_SIZE[0] - dir_w - 60, y),
                  d, fill=text_color, font=font_med)

        y += 90

    if not trains:
        txt = "No trains"
        w = text_width(draw, txt, font_large)
        draw.text(((IMAGE_SIZE[0] - w) // 2, IMAGE_SIZE[1] // 2),
                  txt, fill=text_color, font=font_large)

    now_str = datetime.now().strftime('%d.%m %H:%M')
    f_w = text_width(draw, now_str, font_small)
    draw.text(((IMAGE_SIZE[0] - f_w) // 2, IMAGE_SIZE[1] - 70),
              now_str, fill=text_color, font=font_small)

    img.save(OUTPUT_FILE)
    logger.info(f"PNG сохранён: {OUTPUT_FILE}")


if __name__ == '__main__':
    stop_id = get_stop_id(STATION_NAME)
    if not stop_id:
        logger.error("stop_id не найден")
        sys.exit(1)

    trains = fetch_trains(stop_id)
    generate_image(trains, STATION_NAME)
