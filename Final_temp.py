import urllib.request
import urllib.parse
import json
import csv
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


NWS_BASE_URL = "https://api.weather.gov/stations/{station}/observations"

# La NWS (weather.gov) exige un User-Agent identifiable
NWS_HEADERS = {
    "User-Agent": "(temperatures-veille-script, contact@example.com)",
    "Accept": "application/geo+json",
}


CITIES = {
    "New York": {
        "station": "KLGA",
        "timezone": "America/New_York",
        "unit_label": "°F",
    },
    "Londres": {
        "station": "EGLC",
        "timezone": "Europe/London",
        "unit_label": "°C",
    },
    "Paris": {
        "station": "LFPB",
        "timezone": "Europe/Paris",
        "unit_label": "°C",
    },
    "Madrid": {
        "station": "LEMD",
        "timezone": "Europe/Madrid",
        "unit_label": "°C",
    },
    "Milan": {
        "station": "LIMC",
        "timezone": "Europe/Rome",
        "unit_label": "°C",
    },
    "Munich": {
        "station": "EDDM",
        "timezone": "Europe/Berlin",
        "unit_label": "°C",
    },
    "Amsterdam": {
        "station": "EHAM",
        "timezone": "Europe/Amsterdam",
        "unit_label": "°C",
    },
    "Varsovie": {
        "station": "EPWA",
        "timezone": "Europe/Warsaw",
        "unit_label": "°C",
    },
    "Helsinki": {
        "station": "EFHK",
        "timezone": "Europe/Helsinki",
        "unit_label": "°C",
    },
    "Miami": {
        "station": "KMIA",
        "timezone": "America/New_York",
        "unit_label": "°F",
    },
    "Austin": {
        "station": "KAUS",
        "timezone": "America/Chicago",
        "unit_label": "°F",
    },
    "Atlanta": {
        "station": "KATL",
        "timezone": "America/New_York",
        "unit_label": "°F",
    },
    "Denver": {
        "station": "KBKF",
        "timezone": "America/Denver",
        "unit_label": "°F",
    },
    "Dallas": {
        "station": "KDAL",
        "timezone": "America/Chicago",
        "unit_label": "°F",
    },
    "Los Angeles": {
        "station": "KLAX",
        "timezone": "America/Los_Angeles",
        "unit_label": "°F",
    },
    "Chicago": {
        "station": "KORD",
        "timezone": "America/Chicago",
        "unit_label": "°F",
    },
    "Houston": {
        "station": "KHOU",
        "timezone": "America/Chicago",
        "unit_label": "°F",
    },
    "San Francisco": {
        "station": "KSFO",
        "timezone": "America/Los_Angeles",
        "unit_label": "°F",
    },
    "Seattle": {
        "station": "KSEA",
        "timezone": "America/Los_Angeles",
        "unit_label": "°F",
    },
    "Tokyo": {
        "station": "RJTT",
        "timezone": "Asia/Tokyo",
        "unit_label": "°C",
    },
    "Seoul": {
        "station": "RKSI",
        "timezone": "Asia/Seoul",
        "unit_label": "°C",
    },
}


OUTPUT_FILE = "temperatures_veille.csv"


def celsius_to_fahrenheit(temp_c):
    return (temp_c * 9 / 5) + 32


def fetch_nws_observations(station, start_utc, end_utc):
    """Récupère les observations de température via l'API NWS."""
    url = (
        NWS_BASE_URL.format(station=station)
        + "?"
        + urllib.parse.urlencode({
            "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    )

    request = urllib.request.Request(url, headers=NWS_HEADERS)

    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read().decode("utf-8"))

    results = []

    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        temperature = properties.get("temperature", {}) or {}

        temp_c = temperature.get("value")
        timestamp = properties.get("timestamp")

        if temp_c is None or timestamp is None:
            continue

        dt_utc = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

        results.append((temp_c, dt_utc.timestamp()))

    return results


with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:

    writer = csv.writer(f, delimiter=";")

    writer.writerow([
        "ville",
        "date",
        "temperature_min",
        "heure_min",
        "temperature_max",
        "heure_max",
        "unite",
    ])

    for city, config in CITIES.items():

        station = config["station"]
        tz = ZoneInfo(config["timezone"])
        unit_label = config["unit_label"]

        # Date de la veille dans le fuseau horaire de la ville
        yesterday = datetime.now(tz).date() - timedelta(days=1)

        # Bornes de la journée locale
        start_local = datetime.combine(
            yesterday,
            datetime.min.time(),
            tzinfo=tz,
        )
        end_local = start_local + timedelta(days=1)

        # Conversion des bornes en UTC pour l'API NWS
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)

        try:
            raw_observations = fetch_nws_observations(
                station,
                start_utc,
                end_utc,
            )

            temperatures = []

            for temp_c, timestamp in raw_observations:

                dt_local = datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc,
                ).astimezone(tz)

                # Sécurité : on conserve uniquement les observations
                # appartenant réellement à la veille dans le fuseau local.
                if dt_local.date() != yesterday:
                    continue

                # NWS fournit toujours la température en °C.
                if unit_label == "°F":
                    temperature = round(
                        celsius_to_fahrenheit(temp_c)
                    )
                else:
                    temperature = round(temp_c)

                temperatures.append((temperature, dt_local))

            # Tri chronologique pour obtenir la première occurrence
            # en cas d'égalité sur la température min/max.
            temperatures.sort(key=lambda x: x[1])

            if temperatures:

                min_temp, min_time = min(
                    temperatures,
                    key=lambda x: x[0],
                )

                max_temp, max_time = max(
                    temperatures,
                    key=lambda x: x[0],
                )

                writer.writerow([
                    city,
                    yesterday.strftime("%Y-%m-%d"),
                    min_temp,
                    min_time.strftime("%H:%M:%S"),
                    max_temp,
                    max_time.strftime("%H:%M:%S"),
                    unit_label,
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
