import urllib.request
import urllib.parse
import json
import csv
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURATION
# ============================================================

NWS_METAR_URL = "https://aviationweather.gov/api/data/metar"

NWS_HEADERS = {
    "User-Agent": "temperatures-veille-script/1.0",
    "Accept": "application/json",
}

OUTPUT_FILE = "temperatures_veille.csv"


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


# ============================================================
# OUTILS
# ============================================================

def celsius_to_fahrenheit(temp_c):
    return (temp_c * 9 / 5) + 32


def fetch_nws_metar_observations(station):
    """
    Récupère les METAR des dernières 48 heures
    via l'API officielle NOAA / NWS Aviation Weather Center.

    Aucun token ni compte nécessaire.
    """

    params = {
        "ids": station,
        "format": "json",
        "hours": "48",
    }

    url = (
        NWS_METAR_URL
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers=NWS_HEADERS,
    )

    with urllib.request.urlopen(request) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    return data


def extract_temperature_observations(data, timezone_name):
    """
    Extrait :
        température en °C
        date/heure locale de l'observation
    """

    observations = []

    tz = ZoneInfo(timezone_name)

    if not isinstance(data, list):
        return observations

    for observation in data:

        temp_c = observation.get("temp")
        obs_time = observation.get("obsTime")

        if temp_c is None or obs_time is None:
            continue

        try:
            temp_c = float(temp_c)
        except (TypeError, ValueError):
            continue

        try:
            dt_utc = datetime.fromisoformat(
                obs_time.replace("Z", "+00:00")
            )
        except ValueError:
            continue

        dt_local = dt_utc.astimezone(tz)

        observations.append(
            (temp_c, dt_local)
        )

    return observations


# ============================================================
# CRÉATION DU CSV
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8-sig",
) as f:

    writer = csv.writer(
        f,
        delimiter=";",
    )

    writer.writerow([
        "ville",
        "date",
        "temperature_min",
        "heure_min",
        "temperature_max",
        "heure_max",
        "unite",
    ])

    # ========================================================
    # TRAITEMENT DES VILLES
    # ========================================================

    for city, config in CITIES.items():

        station = config["station"]
        tz = ZoneInfo(config["timezone"])
        unit_label = config["unit_label"]

        # ----------------------------------------------------
        # Veille dans le fuseau local de la ville
        # ----------------------------------------------------

        yesterday = (
            datetime.now(tz).date()
            - timedelta(days=1)
        )

        try:

            # ------------------------------------------------
            # Récupération des METAR
            # ------------------------------------------------

            data = fetch_nws_metar_observations(
                station
            )

            # ------------------------------------------------
            # Extraction des températures
            # ------------------------------------------------

            observations = extract_temperature_observations(
                data,
                config["timezone"],
            )

            temperatures = []

            for temp_c, dt_local in observations:

                # On conserve uniquement les observations
                # de la veille dans le fuseau local.
                if dt_local.date() != yesterday:
                    continue

                # ------------------------------------------------
                # Conversion selon l'unité souhaitée
                # ------------------------------------------------

                if unit_label == "°F":
                    temperature = round(
                        celsius_to_fahrenheit(temp_c)
                    )
                else:
                    temperature = round(temp_c)

                temperatures.append(
                    (temperature, dt_local)
                )

            # ------------------------------------------------
            # Tri chronologique
            #
            # Important :
            # en cas d'égalité, min()/max() conserveront
            # ainsi la première occurrence.
            # ------------------------------------------------

            temperatures.sort(
                key=lambda x: x[1]
            )

            # ------------------------------------------------
            # Min / Max
            # ------------------------------------------------

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
                    f"min {min_temp}{unit_label} "
                    f"à {min_time.strftime('%H:%M')} | "
                    f"max {max_temp}{unit_label} "
                    f"à {max_time.strftime('%H:%M')}"
                )

            else:

                print(
                    f"{city}: "
                    "aucune observation disponible"
                )

        except Exception as e:

            print(
                f"{city}: ERREUR - {e}"
            )


print(
    f"\nTerminé : {OUTPUT_FILE} créé."
)
