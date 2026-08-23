import urllib.request
import urllib.parse
import json
import csv
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
# RÉCUPÉRATION DES METAR POUR UNE STATION
# ============================================================

def fetch_nws_metar_observations(station):
    """
    Récupère les METAR des dernières 48 heures
    pour une station.

    Source :
        NOAA / NWS Aviation Weather Center

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


# ============================================================
# EXTRACTION DES TEMPÉRATURES
# ============================================================

def extract_temperature_observations(
    data,
    timezone_name,
    yesterday,
):
    """
    Extrait uniquement les observations de la veille
    dans le fuseau horaire local de la station.

    Retourne :
        [(temperature_c, datetime_local), ...]
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
            obs_time = float(obs_time)
        except (TypeError, ValueError):
            continue

        # obsTime = timestamp Unix UTC
        dt_utc = datetime.fromtimestamp(
            obs_time,
            tz=timezone.utc,
        )

        # Conversion en heure locale
        dt_local = dt_utc.astimezone(tz)

        # On ne garde que la veille locale
        if dt_local.date() != yesterday:
            continue

        observations.append(
            (temp_c, dt_local)
        )

    # Tri chronologique
    observations.sort(
        key=lambda x: x[1]
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
        timezone_name = config["timezone"]
        unit_label = config["unit_label"]

        tz = ZoneInfo(timezone_name)

        # ----------------------------------------------------
        # Date de la veille dans le fuseau local
        # ----------------------------------------------------

        yesterday = (
            datetime.now(tz).date()
            - timedelta(days=1)
        )

        print(
            f"\n{city} ({station})..."
        )

        try:

            # ------------------------------------------------
            # Une requête par station
            # ------------------------------------------------

            data = fetch_nws_metar_observations(
                station
            )

            print(
                f"  {len(data)} observations reçues"
            )

            # ------------------------------------------------
            # Extraction de la veille
            # ------------------------------------------------

            observations = extract_temperature_observations(
                data,
                timezone_name,
                yesterday,
            )

            if not observations:

                print(
                    f"  Aucune observation pour "
                    f"la veille ({yesterday})"
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
            # Min / Max
            #
            # La liste est déjà triée chronologiquement.
            # En cas d'égalité, min()/max() retiennent donc
            # la première occurrence.
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
            # Écriture dans le CSV
            # ------------------------------------------------

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
                f"  min {min_temp}{unit_label} "
                f"à {min_time.strftime('%H:%M')} | "
                f"max {max_temp}{unit_label} "
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
    f"\nTerminé : {OUTPUT_FILE} créé."
)
