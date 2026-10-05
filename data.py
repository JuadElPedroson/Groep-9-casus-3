import glob
import os
import urllib.request

import pandas as pd
import streamlit as st

SCHEDULE_PAD = "data/schedule_airport.csv.gz"
AIRPORTS_MAP = "data/airports"
WEER_PAD = "data/weer_zurich.csv.gz"
VLUCHT_MAP = "data/flightdata"

KAGGLE_DATASET = "open-flights/airports-train-stations-and-ferry-terminals"
WEER_URL = "https://bulk.meteostat.net/v2/daily/06670.csv.gz"

AIRPORT_KOLOMMEN = [
    "ID", "Name", "City", "Country", "IATA", "ICAO", "Latitude", "Longitude",
    "Altitude", "Timezone", "DST", "Tz", "Type", "Source",
]
WEER_KOLOMMEN = ["datum", "tavg", "tmin", "tmax", "prcp", "snow", "wdir", "wspd", "wpgt", "pres", "tsun"]


@st.cache_data
def laad_schedule():
    return pd.read_csv(SCHEDULE_PAD, encoding="utf-8-sig")


def _download_airports():
    # lokaal staat de token in ~/.kaggle/access_token, op Streamlit Cloud in de secrets
    try:
        if "KAGGLE_API_TOKEN" in st.secrets:
            os.environ["KAGGLE_API_TOKEN"] = st.secrets["KAGGLE_API_TOKEN"]
    except Exception:
        pass
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(KAGGLE_DATASET, path=AIRPORTS_MAP, unzip=True)
    except Exception as fout:
        st.error(f"Luchthavens ophalen via Kaggle is mislukt ({fout}). Zet de CSV zelf in {AIRPORTS_MAP}.")
        st.stop()


@st.cache_data
def laad_airports():
    bestanden = glob.glob(f"{AIRPORTS_MAP}/*.csv")
    if not bestanden:
        _download_airports()
        bestanden = glob.glob(f"{AIRPORTS_MAP}/*.csv")
    pad = next((b for b in bestanden if "clean" in b.lower()), bestanden[0])

    with open(pad, encoding="utf-8-sig") as f:
        eerste_regel = f.readline()
    sep = ";" if eerste_regel.count(";") > eerste_regel.count(",") else ","
    heeft_kopregel = not eerste_regel.split(sep)[0].strip('"').isdigit()
    return pd.read_csv(
        pad,
        sep=sep,
        decimal="," if sep == ";" else ".",
        header=0 if heeft_kopregel else None,
        names=None if heeft_kopregel else AIRPORT_KOLOMMEN,
    )


def _download_weer():
    os.makedirs("data", exist_ok=True)
    try:
        verzoek = urllib.request.Request(WEER_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(verzoek, timeout=30) as antwoord:
            inhoud = antwoord.read()
    except Exception as fout:
        st.error(
            f"Weer downloaden is mislukt ({fout}). Download de dagdata van station 06670 op "
            f"meteostat.net en sla die op als {WEER_PAD}."
        )
        st.stop()
    with open(WEER_PAD, "wb") as f:
        f.write(inhoud)


@st.cache_data
def laad_weer():
    if not os.path.exists(WEER_PAD):
        _download_weer()
    weer = pd.read_csv(WEER_PAD, header=None, names=WEER_KOLOMMEN)
    if not str(weer["datum"].iloc[0])[:4].isdigit():
        weer = pd.read_csv(WEER_PAD).rename(columns={"date": "datum"})
    return weer


def vlucht_bestanden():
    return sorted(glob.glob(f"{VLUCHT_MAP}/*.xlsx"))


@st.cache_data
def laad_vlucht(pad):
    return pd.read_excel(pad)
