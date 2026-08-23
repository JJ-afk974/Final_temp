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
# CONVERSION
# ============================================================

def celsius_to_fahrenheit(temp_c):
    return (temp_c * 9 / 5) + 32


# ============================================================
# RÉCUPÉRATION DES METAR
# ============================================================

def fetch_nws_metar_observations(stations):
    """
    Récupère les METAR des stations demandées.

    L'API AWC/NWS accepte plusieurs identifiants ICAO
    séparés par des virgules.

    Les données sont demandées sur les dernières 48 heures.
    """

    station_list = ",".join(stations)

    params = {
        "ids": station_list,
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
# TRAITEMENT DES OBSERVATIONS
# ============================================================

def get_station_temperatures(
    observations,
    station,
    timezone_name,
    yesterday,
):
    """
    Retourne les observations de température de la veille
    pour une station donnée.

    Résultat :
        [(temperature_c, datetime_local), ...]
    """

    tz = ZoneInfo(timezone_name)

    temperatures = []

    for observation in observations:

        if observation.get("icaoId") != station:
            continue

        temp_c = observation.get("temp")
        obs_time = observation.get("obsTime")

        if temp_c is None or obs_time is None:
            continue

        try:
            temp_c = float(temp_c)
            obs_time = float(obs_time)
        except (TypeError, ValueError):
            continue

        # obsTime est un timestamp Unix UTC.
        dt_utc = datetime.fromtimestamp(
            obs_time,
            tz=timezone.utc,
        )

        # Conversion vers l'heure locale de la ville.
        dt_local = dt_utc.astimezone(tz)

        # On ne conserve que la veille locale.
        if dt_local.date() != yesterday:
            continue

        temperatures.append(
            (temp_c, dt_local)
        )

    # Tri chronologique.
    temperatures.sort(
        key=lambda x: x[1]
    )

    return temperatures


# ============================================================
# PRÉPARATION DES STATIONS
# ============================================================

stations = [
    config["station"]
    for config in CITIES.values()
]


# ============================================================
# RÉCUPÉRATION UNIQUE DES DONNÉES
# ============================================================

try:

    print("Récupération des METAR NWS/NOAA...")

    all_observations = fetch_nws_metar_observations(
        stations
    )

    print(
        f"{len(all_observations)} observations reçues."
    )

except Exception as e:

    print(
        f"ERREUR lors de la récupération NWS : {e}"
    )

    raise SystemExit(1)


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
    # TRAITEMENT DE CHAQUE VILLE
    # ========================================================

    for city, config in CITIES.items():

        station = config["station"]
        timezone_name = config["timezone"]
        unit_label = config["unit_label"]

        tz = ZoneInfo(timezone_name)

        # ----------------------------------------------------
        # Veille dans le fuseau horaire local
        # ----------------------------------------------------

        yesterday = (
            datetime.now(tz).date()
            - timedelta(days=1)
        )

        try:

            temperatures_c = get_station_temperatures(
                all_observations,
                station,
                timezone_name,
                yesterday,
            )

            if not temperatures_c:

                print(
                    f"{city}: aucune observation disponible "
                    f"(station {station})"
                )

                continue

            # ------------------------------------------------
            # Conversion des températures
            # ------------------------------------------------

            temperatures = []

            for temp_c, dt_local in temperatures_c:

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
            # La liste étant triée chronologiquement,
            # min()/max() retiennent la première occurrence
            # en cas d'égalité.
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
            # Écriture CSV
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
                f"{city}: "
                f"min {min_temp}{unit_label} "
                f"à {min_time.strftime('%H:%M')} | "
                f"max {max_temp}{unit_label} "
                f"à {max_time.strftime('%H:%M')}"
            )

        except Exception as e:

            print(
                f"{city}: ERREUR - {e}"
            )


# ============================================================
# FIN
# ============================================================

print(
    f"\nTerminé : {OUTPUT_FILE} créé."
)
