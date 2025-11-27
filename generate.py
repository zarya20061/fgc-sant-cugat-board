import requests
import zipfile
import io
import csv
from datetime import datetime, timedelta, time, date
from PIL import Image, ImageDraw, ImageFont

# Download GTFS ZIP
url = 'https://dadesobertes.fgc.cat/download/file/google_transit.zip'
response = requests.get(url)
if response.status_code != 200:
    raise ValueError("Failed to download GTFS data")

zip_content = io.BytesIO(response.content)

with zipfile.ZipFile(zip_content) as z:
    # Find stop_id for "Sant Cugat"
    stop_id = None
    with io.StringIO(z.read('stops.txt').decode('utf-8')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['stop_name'].strip() == 'Sant Cugat':
                stop_id = row['stop_id']
                break
    if not stop_id:
        raise ValueError("Station 'Sant Cugat' not found in stops.txt")

    # Get active service_ids for today
    today = date.today()
    weekday = today.weekday()  # 0 = Monday
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_name = days[weekday]
    service_ids = set()

    if 'calendar.txt' in z.namelist():
        with io.StringIO(z.read('calendar.txt').decode('utf-8')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['start_date'] <= today.strftime('%Y%m%d') <= row['end_date'] and row[day_name] == '1':
                    service_ids.add(row['service_id'])

    # Handle exceptions from calendar_dates.txt
    if 'calendar_dates.txt' in z.namelist():
        with io.StringIO(z.read('calendar_dates.txt').decode('utf-8')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['date'] == today.strftime('%Y%m%d'):
                    if row['exception_type'] == '1':
                        service_ids.add(row['service_id'])
                    elif row['exception_type'] == '2' and row['service_id'] in service_ids:
                        service_ids.remove(row['service_id'])

    # Get trips for active services with headsign
    trips = {}
    with io.StringIO(z.read('trips.txt').decode('utf-8')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['service_id'] in service_ids:
                trips[row['trip_id']] = row['trip_headsign']

    # Get upcoming stop_times for the stop_id within next hour
    stop_times_list = []
    now = datetime.now()
    current_time = now.time()
    one_hour_later = (now + timedelta(hours=1)).time()

    with io.StringIO(z.read('stop_times.txt').decode('utf-8')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['stop_id'] == stop_id and row['trip_id'] in trips:
                arrival_str = row['arrival_time']
                hours, minutes, seconds = map(int, arrival_str.split(':'))
                if hours >= 24:
                    hours -= 24  # Handle overnight trips
                arrival_time = time(hours, minutes, seconds)
                if current_time <= arrival_time <= one_hour_later:
                    stop_times_list.append({
                        'arrival_time': arrival_time,
                        'headsign': trips[row['trip_id']]
                    })

    # Sort by arrival time and limit to 10
    stop_times_list.sort(key=lambda x: x['arrival_time'])
    stop_times_list = stop_times_list[:10]

# Generate PNG image
width, height = 800, 600
image = Image.new('RGB', (width, height), color='black')
draw = ImageDraw.Draw(image)

# Load fonts (use system fonts for reliability in GitHub Actions)
try:
    font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
    font_normal = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
except IOError:
    font_large = ImageFont.load_default()  # Fallback
    font_normal = ImageFont.load_default()

# Draw header
draw.text((width // 2, 20), "Train Schedule for Sant Cugat", fill='white', font=font_normal, anchor='mt')

# Draw trains
y_pos = 80
for entry in stop_times_list:
    time_str = entry['arrival_time'].strftime('%H:%M')
    draw.text((50, y_pos), time_str, fill='white', font=font_large)
    draw.text((400, y_pos), entry['headsign'], fill='white', font=font_large)
    y_pos += 50

# Draw footer with current date/time
footer_text = now.strftime('%Y-%m-%d %H:%M:%S')
draw.text((width // 2, height - 20), footer_text, fill='white', font=font_normal, anchor='mb')

# Save image
image.save('schedule.png')
print("Image generated successfully: schedule.png")
