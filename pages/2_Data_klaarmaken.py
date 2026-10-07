import pandas as pd
import plotly.express as px
import streamlit as st

from data import laad_airports, laad_schedule, laad_weer
from schoon import (
    haal_uitschieters_weg, koppel_luchthavens, koppel_weer,
    maak_kolommen, maak_vertraging, streepjes_naar_leeg,
)

def getal(n):
    return f"{n:,}".replace(",", ".")

# wat voorspellen we
st.header("Wat willen we voorspellen?")

st.subheader("Welke kolommen denken we nodig te hebben?")
kolommen_tabel = pd.DataFrame(
    [
        ["LSV", "Waarschijnlijk landing of start", "Landingen en starts lijken te verschillen"],
        ["STD, STA_STD_ltc", "Datum en geplande tijd", "Maand, weekdag en uur kunnen uitmaken"],
        ["ACT", "Vliegtuigtype", "Misschien verschilt het per type"],
        ["RWY, RWC", "Baan en baanconfiguratie", "Hangt waarschijnlijk samen met wind en tijdstip"],
        ["Org/Des", "Herkomst of bestemming", "Misschien verschilt het per land"],
        ["FLT", "Vluchtnummer, eerste 2 letters zijn de maatschappij", "Maatschappijen werken anders"],
        ["Weer", "Temperatuur, neerslag en wind per dag", "Slecht weer kan voor vertraging zorgen"],
        ["Drukte", "Aantal vluchten per uur (zelf maken)", "Drukke uren geven misschien meer vertraging"],
    ],
    columns=["Kolom", "Wat is het", "Waarom denken we dat het helpt"],
)
st.table(kolommen_tabel)

# stap 1
st.header("Stap 1: vertraging uitrekenen")
schedule = laad_schedule()
# vertraging zonder correctie, om te zien hoeveel vluchten over middernacht gaan
ruw = (pd.to_timedelta(schedule["ATA_ATD_ltc"]) - pd.to_timedelta(schedule["STA_STD_ltc"])).dt.total_seconds() / 60
n_middernacht = int((ruw < -180).sum())
laagste_ruw = ruw.min()

df = maak_vertraging(schedule)

# crosstab van vroeg, op tijd en te laat per landing/start
groep = pd.cut(
    df["vertraging"], [-1000, 0, 15, 2000],
    labels=["te vroeg", "0 tot 15 min te laat", "meer dan 15 min te laat"],
)
kruis = (pd.crosstab(df["LSV"], groep, normalize="index") * 100).round(1)
st.write("Crosstab: percentage vluchten per groep.")
st.dataframe(kruis)

# stap 2
st.header("Stap 2: streepjes en lege waarden")
df = streepjes_naar_leeg(df)
kolommen = ["TAR", "GAT", "RWC", "Org/Des", "DL1", "IX1", "DL2", "IX2"]
leeg = df[kolommen].isna().sum()
leeg_tabel = pd.DataFrame({"aantal leeg": leeg, "procent": (leeg / len(df) * 100).round(1)})

st.dataframe(leeg_tabel)

# stap 3
st.header("Stap 3: uitschieters")
fig = px.box(
    df[["LSV", "vertraging"]], x="LSV", y="vertraging",
    labels={"LSV": "L of S", "vertraging": "Vertraging (minuten)"},
)
st.plotly_chart(fig)

kijk = ["datum", "FLT", "LSV", "STA_STD_ltc", "ATA_ATD_ltc", "vertraging"]
col1, col2 = st.columns(2)
with col1:
    st.write("Vluchten die het meest te vroeg waren")
    st.dataframe(df.nsmallest(5, "vertraging")[kijk])
with col2:
    st.write("Vluchten die het meest te laat waren")
    st.dataframe(df.nlargest(5, "vertraging")[kijk])

n_weg = int((df["vertraging"] < -60).sum())
max_laat = df["vertraging"].max() / 60
df = haal_uitschieters_weg(df)
st.write(
    f"{n_weg} vluchten zijn meer dan 60 minuten te vroeg. Dat komt bijna niet voor en lijkt een fout in de data. "
    "Die halen we weg."
)

st.write(f"Er blijven {getal(len(df))} vluchten over.")

# stap 4
st.header("Stap 4: nieuwe kolommen")
df = maak_kolommen(df)

st.dataframe(df[["datum", "STA_STD_ltc", "uur", "weekdag", "maand", "jaar", "FLT", "maatschappij", "drukte"]].head())

# gemiddelde vertraging per uur, alleen uren met genoeg vluchten
per_uur = df.groupby("uur")["vertraging"].agg(["mean", "count"])
per_uur = per_uur[per_uur["count"] >= 500].reset_index()
fig = px.line(
    per_uur, x="uur", y="mean", markers=True,
    labels={"uur": "Uur van de dag", "mean": "Gemiddelde vertraging (minuten)"},
)
st.plotly_chart(fig)
hoogste = per_uur.loc[per_uur["mean"].idxmax()]
laagste = per_uur.loc[per_uur["mean"].idxmin()]
st.write(
    f"Wat opvalt: rond {int(hoogste['uur'])} uur is de vertraging het hoogst ({round(hoogste['mean'], 1)} minuten) "
    f"en rond {int(laagste['uur'])} uur het laagst ({round(laagste['mean'], 1)} minuten). "
    "Dus het uur is een goede kolom om mee te nemen."
)
per_jaar = df.groupby("jaar")["vertraging"].mean().round(1)

# stap 5
st.header("Stap 5: luchthavens koppelen")
n_codes = df["Org/Des"].nunique()
df = koppel_luchthavens(df, laad_airports())
n_gevonden = df.loc[df["luchthaven"].notna(), "Org/Des"].nunique()
n_zonder = int((df["luchthaven"].isna() & df["Org/Des"].notna()).sum())
st.write(
    f"Van {n_codes} codes hebben we er {n_gevonden} gevonden. "
    f"Dat laat {getal(n_zonder)} vluchten zonder luchthaven, die laten we leeg. "
    "Zo hebben we per vlucht het land en de plek op de kaart."
)
st.dataframe(df[["Org/Des", "luchthaven", "land", "lat", "lon"]].dropna().drop_duplicates("Org/Des").head())

# stap 6
st.header("Stap 6: weer koppelen")
weer = laad_weer()
weer_jaren = weer[pd.to_datetime(weer["datum"]).dt.year.isin([2019, 2020])]
leeg_weer = weer_jaren.isna().sum()
leeg_weer = leeg_weer[leeg_weer > 0]
df = koppel_weer(df, weer)
st.write(
    f"Het weerbestand begint in 1973 en heeft {getal(len(weer))} dagen. Wij hebben alleen de dagen van 2019 en 2020 nodig "
    f"({len(weer_jaren)} dagen) en koppelen die op datum aan de vluchten."
)
st.write("Lege waarden in het weer van 2019 en 2020:")
st.dataframe(leeg_weer.rename("aantal leeg"))

# correlatie van weer en drukte met vertraging
verband = df[["vertraging", "tavg", "prcp", "wdir", "wspd", "wpgt", "pres", "drukte"]].corr()["vertraging"]
verband = verband.drop("vertraging").round(3).reset_index()
verband.columns = ["kolom", "verband"]
fig = px.bar(verband, x="kolom", y="verband", labels={"verband": "Verband met vertraging"})
st.plotly_chart(fig)

weer_verband = verband[verband["kolom"] != "drukte"]
sterkste = weer_verband.loc[weer_verband["verband"].abs().idxmax()]
drukte_verband = verband.loc[verband["kolom"] == "drukte", "verband"].iloc[0]

st.header("Klaar")
st.write(f"We hebben nu {getal(len(df))} vluchten en {df.shape[1]} kolommen. Hiermee gaan we verder bij de deelvragen.")
st.write("Conclusie: de data is klaar. We kunnen nu de lijngrafiek en de kaart maken (Vertraging over de tijd en Bestemmingen) en een model bouwen (Voorspellen).")
st.dataframe(df.head())

df_vliegtuigen_per_uur = (
    df.groupby("uur").size().reset_index(name="aantal_vliegtuigen")
)

fig = px.line(
    df_vliegtuigen_per_uur,
    x="uur",
    y="aantal_vliegtuigen",
    title="Aantal vliegtuigen op de airport per uur",
    labels={
        "uur": "Tijd van de dag (Uur)",
        "aantal_vliegtuigen": "Aantal vliegtuigen",
    },
    markers=True,  # Voegt punten toe op de lijn voor betere leesbaarheid
)

# Optioneel: zorg dat de x-as nette uuraanduidingen heeft (0 t/m 23)
fig.update_xaxes(dtick=1)

st.plotly_chart(fig, use_container_width=True)
