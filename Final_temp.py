import urllib.request
import urllib.parse
import json
import csv
import os
import time
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

# La date de référence est TOUJOURS celle de Paris.
PARIS_TZ = ZoneInfo("Europe/Paris")


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
# CONVERSION
# ============================================================

def celsius_to_fahrenheit(temp_c):
    return (temp_c * 9 / 5) + 32


# ============================================================
# RÉCUPÉRATION DES METAR
# ============================================================

def fetch_nws_metar_observations(station):

    params = {
        "ids": station,
        "format": "json",
        "hours": "72",
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


# ============================================================
# EXTRACTION DES OBSERVATIONS
# ============================================================

def extract_temperature_observations(
    data,
    timezone_name,
    target_date,
):

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
            obs_time = float(obs_time)
        except (TypeError, ValueError):
            continue

        dt_utc = datetime.fromtimestamp(
            obs_time,
            tz=timezone.utc,
        )

        dt_local = dt_utc.astimezone(tz)

        if dt_local.date() != target_date:
            continue

        observations.append(
            (temp_c, dt_local)
        )

    observations.sort(
        key=lambda x: x[1]
    )

    return observations


# ============================================================
# DATE CIBLE
# ============================================================

# La date cible est déterminée à Paris.
#
# Exemple :
# Paris = 23/08
# target_date = 22/08

target_date = (
    datetime.now(PARIS_TZ).date()
    - timedelta(days=1)
)

target_date_str = target_date.strftime(
    "%Y-%m-%d"
)

print(
    f"Date cible : {target_date_str}"
)


# ============================================================
# LECTURE DU CSV EXISTANT
# ============================================================

existing_rows = set()

if os.path.exists(OUTPUT_FILE):

    with open(
        OUTPUT_FILE,
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        reader = csv.DictReader(
            f,
            delimiter=";",
        )

        for row in reader:

            city = row.get("ville")
            date = row.get("date")

            if city and date:
                existing_rows.add(
                    (city, date)
                )


# ============================================================
# OUVERTURE EN MODE APPEND
# ============================================================

file_exists = os.path.exists(
    OUTPUT_FILE
)

file_is_empty = (
    not file_exists
    or os.path.getsize(OUTPUT_FILE) == 0
)


with open(
    OUTPUT_FILE,
    "a",
    newline="",
    encoding="utf-8-sig",
) as f:

    writer = csv.writer(
        f,
        delimiter=";",
    )

    # --------------------------------------------------------
    # En-tête uniquement si le fichier est nouveau/vide
    # --------------------------------------------------------

    if file_is_empty:

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
        timezone_name = config["timezone"]
        unit_label = config["unit_label"]

        # ----------------------------------------------------
        # Protection contre les doublons
        # ----------------------------------------------------

        if (city, target_date_str) in existing_rows:

            print(
                f"{city}: "
                f"{target_date_str} déjà présent, "
                f"ignoré."
            )

            continue

        print(
            f"\n{city} ({station})..."
        )

        try:

            # ------------------------------------------------
            # Récupération METAR
            # ------------------------------------------------

            data = fetch_nws_metar_observations(
                station
            )

            print(
                f"  {len(data)} observations reçues"
            )

            # ------------------------------------------------
            # Filtrage sur la date cible
            # ------------------------------------------------

            observations = (
                extract_temperature_observations(
                    data,
                    timezone_name,
                    target_date,
                )
            )

            print(
                f"  {len(observations)} observations "
                f"pour le {target_date_str}"
            )

            if not observations:

                print(
                    "  Aucune observation disponible"
                )

                continue

            # ------------------------------------------------
            # Conversion des températures
            # ------------------------------------------------

            temperatures = []

            for temp_c, dt_local in observations:

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
            # MIN / MAX
            # ------------------------------------------------

            min_temp, min_time = min(
                temperatures,
                key=lambda x: x[0],
            )

            max_temp, max_time = max(
                temperatures,
                key=lambda x: x[0],
            )

            # ------------------------------------------------
            # AJOUT AU CSV
            # ------------------------------------------------

            writer.writerow([
                city,
                target_date_str,
                min_temp,
                min_time.strftime("%H:%M:%S"),
                max_temp,
                max_time.strftime("%H:%M:%S"),
                unit_label,
            ])

            print(
                f"  MIN : {min_temp}{unit_label} "
                f"à {min_time.strftime('%H:%M')}"
            )

            print(
                f"  MAX : {max_temp}{unit_label} "
                f"à {max_time.strftime('%H:%M')}"
            )

        except Exception as e:

            print(
                f"  ERREUR : {e}"
            )

        # Petite pause entre les requêtes
        time.sleep(1)


# ============================================================
# FIN
# ============================================================

print(
    f"\nTerminé : {OUTPUT_FILE} mis à jour."
)
