import urllib.request
import urllib.parse
import json
import csv
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"

WU_BASE_URL = "https://api.weather.com/v1/location/{location}/observations/historical.json"
NWS_BASE_URL = "https://api.weather.gov/stations/{station}/observations"

# La NWS (weather.gov) exige un User-Agent identifiable (nom d'app + contact)
NWS_HEADERS = {
    "User-Agent": "(temperatures-veille-script, contact@example.com)",
    "Accept": "application/geo+json",
}

CITIES = {
    "New York": {
        "location": "KLGA:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Londres": {
        "location": "EGLC:9:GB",
        "timezone": "Europe/London",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Paris": {
        "location": "LFPB:9:FR",
        "timezone": "Europe/Paris",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Madrid": {
        "location": "LEMD:9:ES",
        "timezone": "Europe/Paris",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Milan": {
        "location": "LIMC:9:IT",
        "timezone": "Europe/Paris",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Munich": {
        "location": "EDDM:9:DE",
        "timezone": "Europe/Paris",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Amsterdam": {
        "location": "EHAM:9:NL",
        "timezone": "Europe/Amsterdam",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Varsovie": {
        "location": "EPWA:9:PL",
        "timezone": "Europe/Paris",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Helsinski": {
        "location": "EFHK:9:FI",
        "timezone": "Europe/Istanbul",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Miami": {
        "location": "KMIA:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Austin": {
        "location": "KAUS:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Atlanta": {
        "location": "KATL:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Denver": {
        "location": "KBKF:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Dallas": {
        "location": "KDAL:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Los Angeles": {
        "location": "KLAX:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Chicago": {
        "location": "KORD:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Houston": {
        "location": "KHOU:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "San Francisco": {
        "location": "KSFO:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Seattle": {
        "location": "KSEA:9:US",
        "timezone": "America/New_York",
        "units": "e",
        "unit_label": "°F",
        "source": "nws",
    },
    "Tokyo": {
        "location": "RJTT:9:JP",
        "timezone": "Asia/Tokyo",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
    "Seoul": {
        "location": "RKSI:9:KR",
        "timezone": "Asia/Seoul",
        "units": "m",
        "unit_label": "°C",
        "source": "wu",
    },
}

OUTPUT_FILE = "temperatures_veille.csv"


def celsius_to_fahrenheit(temp_c):
    return (temp_c * 9 / 5) + 32


def fetch_wu_observations(location, units, date_str):
    """Récupère les observations via Weather Underground (villes non-US)."""
    url = (
        WU_BASE_URL.format(location=location)
        + "?"
        + urllib.parse.urlencode({
            "apiKey": API_KEY,
            "units": units,
            "startDate": date_str,
            "endDate": date_str,
        })
    )

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode("utf-8"))

    observations = data.get("observations", [])

    results = []
    for obs in observations:
        temp = obs.get("temp")
        ts = obs.get("valid_time_gmt")
        if temp is None or ts is None:
            continue
        results.append((temp, ts))

    return results


def fetch_nws_observations(station, start_utc, end_utc):
    """Récupère les observations via l'API weather.gov (villes US)."""
    url = (
        NWS_BASE_URL.format(station=station)
        + "?"
        + urllib.parse.urlencode({
            "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    )

    req = urllib.request.Request(url, headers=NWS_HEADERS)

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))

    features = data.get("features", [])

    results = []
    for feature in features:
        props = feature.get("properties", {})
        temp_info = props.get("temperature", {}) or {}
        temp_c = temp_info.get("value")
        ts_str = props.get("timestamp")

        if temp_c is None or ts_str is None:
            continue

        # Timestamp NWS déjà en ISO8601 UTC (ex: 2024-01-15T14:53:00+00:00)
        dt_utc = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        ts_epoch = dt_utc.timestamp()

        temp_f = celsius_to_fahrenheit(temp_c)
        results.append((round(temp_f), ts_epoch))

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
        "unite"
    ])

    for city, config in CITIES.items():

        location = config["location"]
        tz = ZoneInfo(config["timezone"])
        units = config["units"]
        unit_label = config["unit_label"]
        source = config["source"]

        # Date de la veille dans le fuseau horaire de la ville
        yesterday = datetime.now(tz).date() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")

        try:
            if source == "nws":
                station = location.split(":")[0]  # ex: "KMIA:9:US" -> "KMIA"

                # Bornes de la journée locale, converties en UTC pour l'API NWS
                start_local = datetime.combine(
                    yesterday, datetime.min.time(), tzinfo=tz
                )
                end_local = start_local + timedelta(days=1)
                start_utc = start_local.astimezone(timezone.utc)
                end_utc = end_local.astimezone(timezone.utc)

                raw_observations = fetch_nws_observations(
                    station, start_utc, end_utc
                )
            else:
                raw_observations = fetch_wu_observations(
                    location, units, date_str
                )

            temperatures = []

            for temp, ts in raw_observations:
                dt_local = datetime.fromtimestamp(
                    ts,
                    tz=timezone.utc
                ).astimezone(tz)

                # On garde uniquement les observations de la veille
                if dt_local.date() == yesterday:
                    temperatures.append((temp, dt_local))

            # Tri chronologique croissant : indispensable pour que min()/max()
            # retiennent la PREMIERE heure d'occurrence en cas d'égalité.
            # (Les API ne garantissent pas toujours l'ordre chronologique :
            # api.weather.gov, par exemple, renvoie les observations du plus
            # récent au plus ancien.)
            temperatures.sort(key=lambda x: x[1])

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
