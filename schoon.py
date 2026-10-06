import numpy as np
import pandas as pd
import streamlit as st
from sklearn.model_selection import train_test_split

from data import laad_airports, laad_schedule, laad_weer

KOLOMMEN = [
    "LSV", "ACT", "RWY", "RWC", "maatschappij", "uur", "weekdag", "maand", "jaar",
    "drukte", "land", "tavg", "prcp", "wdir", "wspd", "wpgt", "pres",
]


# datum omzetten en vertraging in minuten uitrekenen (echte tijd min geplande tijd)
def maak_vertraging(df):
    df = df.copy()
    df["datum"] = pd.to_datetime(df["STD"], format="%d/%m/%Y")
    gepland = pd.to_timedelta(df["STA_STD_ltc"])
    echt = pd.to_timedelta(df["ATA_ATD_ltc"])
    df["vertraging"] = (echt - gepland).dt.total_seconds() / 60
    # meer dan 3 uur te vroeg betekent dat de echte tijd na middernacht valt
    df.loc[df["vertraging"] < -180, "vertraging"] += 1440
    return df


# streepjes betekenen onbekend, dus lege waarde
def streepjes_naar_leeg(df):
    return df.replace("-", np.nan)


# vluchten die meer dan 60 minuten te vroeg zijn halen we weg
def haal_uitschieters_weg(df):
    return df[df["vertraging"] >= -60].copy()


# nieuwe kolommen maken uit datum, tijd en vluchtnummer
def maak_kolommen(df):
    df = df.copy()
    df["uur"] = pd.to_timedelta(df["STA_STD_ltc"]).dt.components.hours
    df["jaar"] = df["datum"].dt.year
    df["maand"] = df["datum"].dt.month
    df["weekdag"] = df["datum"].dt.dayofweek
    df["maatschappij"] = df["FLT"].str[:2]
    # drukte is het aantal vluchten in hetzelfde uur op dezelfde dag
    df["drukte"] = df.groupby(["datum", "uur"])["FLT"].transform("count")
    return df


# luchthaven erbij zoeken op ICAO-code, als dat niet lukt op IATA-code
def koppel_luchthavens(df, airports):
    df = df.copy()
    nieuw = {"Name": "luchthaven", "Country": "land", "Latitude": "lat", "Longitude": "lon"}
    op_icao = airports.drop_duplicates("ICAO").set_index("ICAO")[list(nieuw)].rename(columns=nieuw)
    op_iata = airports.drop_duplicates("IATA").set_index("IATA")[list(nieuw)].rename(columns=nieuw)
    df = df.join(op_icao, on="Org/Des")
    gemist = df["luchthaven"].isna() & df["Org/Des"].notna()
    for kolom in op_iata.columns:
        df.loc[gemist, kolom] = df.loc[gemist, "Org/Des"].map(op_iata[kolom])
    return df


# weer van 2019 en 2020 koppelen op datum, snow en tsun zijn leeg dus die laten we weg
def koppel_weer(df, weer):
    weer = weer.copy()
    weer["datum"] = pd.to_datetime(weer["datum"])
    weer = weer[["datum", "tavg", "prcp", "wdir", "wspd", "wpgt", "pres"]]
    return df.merge(weer, on="datum", how="left")


# alle stappen achter elkaar, zodat andere pagina's de schone data kunnen gebruiken
@st.cache_data
def laad_klaar():
    df = maak_vertraging(laad_schedule())
    df = streepjes_naar_leeg(df)
    df = haal_uitschieters_weg(df)
    df = maak_kolommen(df)
    df = koppel_luchthavens(df, laad_airports())
    df = koppel_weer(df, laad_weer())
    return df


# 80 procent om van te leren (train) en 20 procent om te testen
def maak_train_test(df):
    return train_test_split(df[KOLOMMEN], df["vertraging"], test_size=0.2, random_state=42)
