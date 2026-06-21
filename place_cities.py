"""
Авторозміщення та верифікація координат міст на карті Зоряної Пам'яті.

Режими:
  python place_cities.py                         # оновити тільки міста з pos_x=0
  python place_cities.py --all                   # переоновити всі міста
  python place_cities.py --report                # звіт про відхилення без змін у БД
  python place_cities.py --fix                   # виправити тільки суттєво неправильні (Δ > 0.015)
  python place_cities.py --fix --tolerance=0.03  # поріг 0.03 (~50 км)
  python place_cities.py --dry-run               # будь-який режим без запису в БД
"""

import os
import sys
import time

import pymysql
import requests
from dotenv import load_dotenv

load_dotenv()

# Коефіцієнти калібровані по 5 референсних містах (Київ, Харків, Львів, Одеса, Дніпро)
LON_MIN    = 21.30
LON_RANGE  = 19.90
LAT_MAX    = 52.48
LAT_RANGE  =  7.59

# Кускова корекція для Кримського півострова
# SVG-карта стискає Крим по вертикалі відносно материка
CRIMEA_LAT    = 46.48   # широта точки стику (широта Одеси, де формула точна)
CRIMEA_POS_Y  = 0.790   # pos_y у точці стику
CRIMEA_Y_RATE = 0.0760  # темп зростання pos_y в Криму (калібровано по SVG шляхах)

NOMINATIM_URL   = "https://nominatim.openstreetmap.org/search"
NOMINATIM_DELAY = 1.1
USER_AGENT      = "ZoryanaPamyat/1.0 treetex.g.ads@gmail.com"

UA_LAT_MIN, UA_LAT_MAX = 43.8, 53.0
UA_LON_MIN, UA_LON_MAX = 21.0, 41.0


def geo_to_pos(lat: float, lon: float) -> tuple:
    pos_x = (lon - LON_MIN) / LON_RANGE
    if lat < CRIMEA_LAT:
        pos_y = CRIMEA_POS_Y + (CRIMEA_LAT - lat) * CRIMEA_Y_RATE
    else:
        pos_y = (LAT_MAX - lat) / LAT_RANGE
    return round(max(0.0, min(1.0, pos_x)), 4), round(max(0.0, min(1.0, pos_y)), 4)


def pos_distance(px1: float, py1: float, px2: float, py2: float) -> float:
    return ((px1 - px2) ** 2 + (py1 - py2) ** 2) ** 0.5


def geocode(name: str) -> tuple:
    try:
        r = requests.get(
            NOMINATIM_URL,
            params={"q": f"{name}, Україна", "format": "json", "limit": 1, "countrycodes": "ua"},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
            if UA_LAT_MIN <= lat <= UA_LAT_MAX and UA_LON_MIN <= lon <= UA_LON_MAX:
                return lat, lon
            else:
                print(f"    [BOUNDS] lat={lat:.2f} lon={lon:.2f} — поза Україною, пропускаємо")
    except Exception as e:
        print(f"    [ERR] {e}")
    return None, None


def main():
    dry_run   = "--dry-run" in sys.argv
    force_all = "--all"     in sys.argv
    fix_mode  = "--fix"     in sys.argv
    report    = "--report"  in sys.argv

    tol = 0.015
    for a in sys.argv:
        if a.startswith("--tolerance="):
            tol = float(a.split("=")[1])

    db = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME", "zoryana_pamyat"),
        charset="utf8mb4",
        autocommit=False,
    )

    with db.cursor() as cur:
        if force_all or fix_mode or report:
            cur.execute("SELECT id, name, tier, pos_x, pos_y FROM cities ORDER BY tier DESC, name")
        else:
            cur.execute(
                "SELECT id, name, tier, pos_x, pos_y FROM cities WHERE pos_x = 0 OR pos_x IS NULL ORDER BY tier DESC, name"
            )
        cities = cur.fetchall()

    total = len(cities)
    mode  = "fix" if fix_mode else "report" if report else "all" if force_all else "new"
    print(f"Знайдено {total} міст | Режим: {mode} | Поріг: {tol}")
    if dry_run or report:
        print("[Зміни в БД НЕ вносяться]\n")

    log_path = "cities_log.txt"
    ok = skip = unchanged = 0
    tier_names = {1: "★Столиця", 2: "Обласний", 3: "Районний"}

    with open(log_path, "w", encoding="utf-8") as log:
        for i, (city_id, name, tier, cur_x, cur_y) in enumerate(cities, 1):
            lat, lon = geocode(name)
            prefix = f"[{i}/{total}]"
            if lat is None:
                line = f"{prefix} [SKIP] {name}"
                print(line); log.write(line + "\n")
                skip += 1
                time.sleep(NOMINATIM_DELAY)
                continue

            new_x, new_y = geo_to_pos(lat, lon)
            dist = pos_distance(cur_x or 0, cur_y or 0, new_x, new_y)
            label = tier_names.get(tier, "     ")

            if fix_mode and dist <= tol:
                unchanged += 1
                time.sleep(NOMINATIM_DELAY)
                continue

            delta_str = f"Δ={dist:.4f}" if (cur_x or 0) > 0 else "NEW"
            line = f"{prefix} {label:9} {name}: {lat:.4f}N {lon:.4f}E → pos_x={new_x} pos_y={new_y} {delta_str}"
            print(line); log.write(line + "\n")

            if not dry_run and not report:
                with db.cursor() as cur2:
                    cur2.execute(
                        "UPDATE cities SET pos_x=%s, pos_y=%s WHERE id=%s",
                        (new_x, new_y, city_id),
                    )
                db.commit()
            ok += 1
            time.sleep(NOMINATIM_DELAY)

    db.close()
    summary = f"\nГотово: {ok} оновлено, {skip} не знайдено, {unchanged} без змін. Лог: {log_path}"
    print(summary)


if __name__ == "__main__":
    main()
