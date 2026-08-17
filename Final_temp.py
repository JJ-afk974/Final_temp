import urllib.request
import urllib.parse
import json
import csv
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"

BASE_URL = "https://api.weather.com/v1/location/{location}/observations/historical.json"

CITIES = {
    "New York": {
        "location": "KLGA:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Londres": {
        "location": "EGLC:9:GB",
        "timezone": "Europe/London",
        "units": "m",
        "unit_label": "°C",
    },
    "Paris": {
        "location": "LFPB:9:FR",
        "timezone": "Europe/Paris",
        "units": "m",
        "unit_label": "°C",
    },
        "Madrid": {
        "location": "LMED:9:ES",
        "timezone": "Europe/Madrid",
        "units": "m",
        "unit_label": "°C",
    },
        "Milan": {
        "location": "LIMC:9:IT",
        "timezone": "Europe/Paris",
        "units": "m",
        "unit_label": "°C",
    },
        "Munich": {
        "location": "EDDM:9:DE",
        "timezone": "Europe/Paris",
        "units": "m",
        "unit_label": "°C",
    },
        "Amsterdam": {
        "location": "EHAM:9:NL",
        "timezone": "Europe/Amsterdam",
        "units": "m",
        "unit_label": "°C",
    },
        "Varsovie": {
        "location": "EPWA:9:PL",
        "timezone": "Europe/Varsovie",
        "units": "m",
        "unit_label": "°C",
    },
        "Helsinski": {
        "location": "EFHK:9:FI",
        "timezone": "Europe/Helsinski",
        "units": "m",
        "unit_label": "°C",
    },
    "Miami": {
        "location": "KMIA:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Austin": {
        "location": "KAUS:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Atlanta": {
        "location": "KATL:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Austin": {
        "location": "KAUS:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Denver": {
        "location": "KBKF:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Dallas": {
        "location": "KDAL:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Los Angeles": {
        "location": "KLAX:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Chicago": {
        "location": "KORD:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Houston": {
        "location": "KHOU:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "San Francisco": {
        "location": "KSFO:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Seattle": {
        "location": "KSEA:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
    },
    "Tokyo": {
        "location": "RJTT:9:JP",
        "timezone": "Asia/Tokyo",
        "units": "m",
        "unit_label": "°C",
    },
    "Seoul": {
        "location": "RKSI:9:KR",
        "timezone": "Asia/Seoul",
        "units": "m",
        "unit_label": "°C",
    },
}

OUTPUT_FILE = "temperatures_veille.csv"

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:

    writer = csv.writer(f, delimiter=";")

    writer.writerow([
        "ville",
        "date",
        "temperature_min",
        "heure_min",
        "temperature_max",
        "heure_max",
        "unite"
    ])

    for city, config in CITIES.items():

        location = config["location"]
        tz = ZoneInfo(config["timezone"])
        units = config["units"]
        unit_label = config["unit_label"]

        # Date de la veille dans le fuseau horaire de la ville
        yesterday = datetime.now(tz).date() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")

        url = (
            BASE_URL.format(location=location)
            + "?"
            + urllib.parse.urlencode({
                "apiKey": API_KEY,
                "units": units,
                "startDate": date_str,
                "endDate": date_str,
            })
        )

        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode("utf-8"))

            observations = data.get("observations", [])

            temperatures = []

            for obs in observations:

                temp = obs.get("temp")
                ts = obs.get("valid_time_gmt")

                if temp is None or ts is None:
                    continue

                # UTC -> heure locale de la ville
                dt_local = datetime.fromtimestamp(
                    ts,
                    tz=timezone.utc
                ).astimezone(tz)

                # On garde uniquement les observations de la veille
                if dt_local.date() == yesterday:
                    temperatures.append((temp, dt_local))

            if temperatures:

                # Température minimale
                min_temp, min_time = min(
                    temperatures,
                    key=lambda x: x[0]
                )

                # Température maximale
                max_temp, max_time = max(
                    temperatures,
                    key=lambda x: x[0]
                )

                writer.writerow([
                    city,
                    yesterday.strftime("%Y-%m-%d"),
                    min_temp,
                    min_time.strftime("%H:%M:%S"),
                    max_temp,
                    max_time.strftime("%H:%M:%S"),
                    unit_label
                ])

                print(
                    f"{city}: "
                    f"min {min_temp}{unit_label} à {min_time.strftime('%H:%M')} | "
                    f"max {max_temp}{unit_label} à {max_time.strftime('%H:%M')}"
                )

            else:
                print(f"{city}: aucune observation disponible")

        except Exception as e:
            print(f"{city}: ERREUR - {e}")

print(f"\nTerminé : {OUTPUT_FILE} créé.")
