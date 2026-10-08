import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from plotly.subplots import make_subplots
from data import laad_airports, laad_schedule, laad_vlucht, laad_weer, vlucht_bestanden
from schoon import laad_klaar

schedule = laad_schedule()
airports = laad_airports()
weer = laad_weer()
bestanden = vlucht_bestanden()
df = laad_klaar()

st.set_page_config(
    page_title="Airport Traffic & Delay Dashboard", layout="wide"
)

st.title("🛫 Analyse Vliegverkeer & Vertraging")

# --- 1. DATA PREPARATIE ---
if "datum" in df.columns:
    df["datetime"] = pd.to_datetime(df["datum"])
    if "uur" in df.columns:
        df["datetime"] = df["datetime"] + pd.to_timedelta(
            df["uur"], unit="h"
        )
else:
    df["datetime"] = pd.to_datetime(
        df["STD"] + " " + df["STA_STD_ltc"], format="%d/%m/%Y %H:%M:%S"
    )

# Zorg dat de kolom 'vertraging' numeriek is
df["vertraging"] = pd.to_numeric(df["vertraging"], errors="coerce")


# --- 2. HULPFUNCTIES VOOR TIJDSREEKSEN ---
def generate_timeseries(dataframe, freq):
    df_sorted = dataframe.sort_values("datetime").set_index("datetime")

    ts = (
        df_sorted.resample(freq)
        .agg(
            aantal_vliegtuigen=("vertraging", "size"),
            gem_vertraging=("vertraging", "mean"),
        )
        .reset_index()
    )

    # Vervang 0 vluchten door NaN voor zichtbare gaten (connectgaps=False)
    ts.loc[ts["aantal_vliegtuigen"] == 0, "aantal_vliegtuigen"] = np.nan
    ts.loc[ts["aantal_vliegtuigen"].isna(), "gem_vertraging"] = np.nan
    return ts


def create_dual_axis_chart(
    ts_data, title, y1_range, y2_max, eenheid, colorbar_x=1.02
):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Blauwe lijn + bolletjes: Aantal vliegtuigen (Primaire Y-as)
    fig.add_trace(
        go.Scatter(
            x=ts_data["datetime"],
            y=ts_data["aantal_vliegtuigen"],
            name="Aantal Vliegtuigen",
            mode="lines+markers",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=5),
            connectgaps=False,
        ),
        secondary_y=False,
    )

    # Waarden <= 0 als 0 behandelen voor de lichtste kleur op de bolletjes
    delay_color_values = ts_data["gem_vertraging"].clip(lower=0)

    # 2. Oranje gestippelde lijn + gekleurde bolletjes: Gemiddelde vertraging (Secundaire Y-as)
    fig.add_trace(
        go.Scatter(
            x=ts_data["datetime"],
            y=ts_data["gem_vertraging"],
            name="Gem. Vertraging (min)",
            mode="lines+markers",
            line=dict(color="#e4ae7f", width=2, dash="dot"),
            marker=dict(
                size=5,
                color=delay_color_values,
                colorscale="Oranges",
                cmin=0,
                cmax=max(10, delay_color_values.max()),
                showscale=True,
                colorbar=dict(
                    title=dict(text="Vertraging<br>(min)", side="top"),
                    len=0.75,
                    x=colorbar_x,  # Dynamische positie afhankelijk van de grafiekbreedte
                    thickness=15,
                ),
            ),
            connectgaps=False,
        ),
        secondary_y=True,
    )

    # Marges instellen op basis van de x-positie van de colorbar
    right_margin = 80 if colorbar_x <= 1.05 else 140

    fig.update_layout(
        title=title,
        hovermode="x unified",
        margin=dict(r=right_margin),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )

    fig.update_xaxes(title_text="Tijdstip / Datum")

    fig.update_yaxes(
        title_text=f"Aantal vliegtuigen (per {eenheid})",
        range=y1_range,
        secondary_y=False,
    )

    # Secundaire Y-as titel
    fig.update_yaxes(
        title_text="Gemiddelde Vertraging (minuten)",
        title_standoff=15,
        range=[-y2_max, y2_max],
        secondary_y=True,
    )

    return fig


def filter_periode(ts, start_date, eenheid):
    start_dt = pd.to_datetime(start_date)

    if eenheid == "Uur":
        end_dt = start_dt + pd.Timedelta(days=1)
    elif eenheid == "Dag":
        end_dt = start_dt + pd.Timedelta(days=14)
    elif eenheid == "Week":
        end_dt = start_dt + pd.Timedelta(weeks=8)
    else:  # Maand
        end_dt = start_dt + pd.DateOffset(months=12)

    return ts[(ts["datetime"] >= start_dt) & (ts["datetime"] < end_dt)]


# --- SECTIE 1 (BOVENAAN): TOTALE TIJDSREEKS (VAST OP WEEKBASIS) ---
st.subheader("Volledig verloop vliegverkeer & vertraging (stappen van een week)")

ts_weekly = generate_timeseries(df, "1W")
fig_full = create_dual_axis_chart(
    ts_weekly,
    "Zowel drukte als vertraging weergegeven in dezelfde grafiek",
    [0, ts_weekly["aantal_vliegtuigen"].max() * 1.05],
    ts_weekly["gem_vertraging"].abs().max() * 1.15,
    "Week",
    colorbar_x=1.02,  # Dicht bij de Y2-as voor de brede bovenste grafiek
)
st.plotly_chart(fig_full, use_container_width=True, key="fig_full_chart")

st.write("In de grafiek is te zien dat er een kleine dip zit in drukte op het vliegveld in November 2019. " \
"En een gigantische dip in Maart 2020. Het vermoeden bestaat dat dit te maken heeft gehad met de corona uitbraak." \
"Interessant om te onderzoeken is of de drukte op het vliegveld te maken heeft met de hoeveelheid vertraging." \
"Houd hierbij in gedachten dat als er weinig vluchten zijn de gemiddelde waardes van de vertraging minder " \
"betrouwbaar uitkomen.")

st.markdown("---")

# --- 4. SECTIE 2: VERGELIJKING VAN PERIODES ---
st.subheader("Vergelijk twee specifieke periodes")

st.write("Als er een wens is voor nader onderzoek, kan met onderstaande tool gefilterd worden.")

tijdseenheid = st.selectbox(
    "Kies gewenste tijdseenheid / aggregatie voor de vergelijking:",
    options=["Uur", "Dag", "Week", "Maand"],
    index=0,
)

freq_map = {"Uur": "1h", "Dag": "1D", "Week": "1W", "Maand": "1MS"}
selected_freq = freq_map[tijdseenheid]

ts_comparison = generate_timeseries(df, selected_freq)

min_date = ts_comparison["datetime"].min().date()
max_date = ts_comparison["datetime"].max().date()

col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    periode_1 = st.date_input("Datum / Start Periode 1", value=min_date)
with col_sel2:
    periode_2 = st.date_input("Datum / Start Periode 2", value=max_date)

ts_p1 = filter_periode(ts_comparison, periode_1, tijdseenheid)
ts_p2 = filter_periode(ts_comparison, periode_2, tijdseenheid)

# Bereken gelijke Y-as limieten
max_p1 = ts_p1["aantal_vliegtuigen"].max() if not ts_p1.empty else 0
max_p2 = ts_p2["aantal_vliegtuigen"].max() if not ts_p2.empty else 0
y1_max = (
    max(max_p1, max_p2) * 1.05
    if not (np.isnan(max_p1) and np.isnan(max_p2))
    else 10
)

max_delay_p1 = ts_p1["gem_vertraging"].abs().max() if not ts_p1.empty else 0
max_delay_p2 = ts_p2["gem_vertraging"].abs().max() if not ts_p2.empty else 0
y2_max = (
    max(max_delay_p1, max_delay_p2) * 1.15
    if not (np.isnan(max_delay_p1) and np.isnan(max_delay_p2))
    else 15
)

# Visualisatie van de vergelijkingsgrafieken
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"### Periode 1 (`{periode_1}`)")
    if not ts_p1.empty:
        avg_delay = ts_p1["gem_vertraging"].mean()
        st.metric(
            label="Gemiddelde Vertraging Periode 1",
            value=f"{avg_delay:.2f} min"
            if not np.isnan(avg_delay)
            else "Geen data",
        )

        fig1 = create_dual_axis_chart(
            ts_p1,
            f"Periode 1 - per {tijdseenheid.lower()}",
            [0, y1_max],
            y2_max,
            tijdseenheid,
            colorbar_x=1.18,  # Verder naar rechts voor de smalle kolomgrafiek
        )
        st.plotly_chart(fig1, use_container_width=True, key="fig1_chart")
    else:
        st.warning("Geen data gevonden voor Periode 1.")

with col2:
    st.markdown(f"### Periode 2 (`{periode_2}`)")
    if not ts_p2.empty:
        avg_delay = ts_p2["gem_vertraging"].mean()
        st.metric(
            label="Gemiddelde Vertraging Periode 2",
            value=f"{avg_delay:.2f} min"
            if not np.isnan(avg_delay)
            else "Geen data",
        )

        fig2 = create_dual_axis_chart(
            ts_p2,
            f"Periode 2 - per {tijdseenheid.lower()}",
            [0, y1_max],
            y2_max,
            tijdseenheid,
            colorbar_x=1.18,  # Verder naar rechts voor de smalle kolomgrafiek
        )
        st.plotly_chart(fig2, use_container_width=True, key="fig2_chart")
    else:
        st.warning("Geen data gevonden voor Periode 2.")

st.subheader("Conclusie deelvraag 1")
st.write("Het lijkt erop dat de drukte op het vliegveld wel degelijk invloed heeft op de vertraging. Met name in" \
"2019 is dit goed te zien. De lijnen lopen globaal parallel. In 2020 gedraagd de data zich onverwacht. Wat erop" \
" duidt dat er een grote gebeurtenis heeft plaatsgevonden. Binnen dit onderzoek is niet gedefinieerd wat dat is "
"(geweest), of onderzocht wat dit te maken heeft gehad met de vertragingen.")