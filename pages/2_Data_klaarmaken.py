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


st.set_page_config(page_title="Data klaarmaken", layout="wide")

st.title("Data klaarmaken")
st.write("Hier laten we stap voor stap zien hoe we de data klaar hebben gemaakt om de vertraging te voorspellen.")

# wat voorspellen we
st.header("Wat willen we voorspellen?")
st.write(
    "Vertraging zit niet als kolom in de data. Die rekenen we zelf uit: de echte tijd (ATA_ATD_ltc) "
    "min de geplande tijd (STA_STD_ltc). Dit is onze y. Een negatief getal betekent dat de vlucht te vroeg was."
)

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
st.write(
    "Deze gebruiken we niet: ATA_ATD_ltc (dat is de uitkomst zelf), Identifier (alleen datum, tijd en vlucht aan elkaar) "
    "en DL1 tot IX2 (we weten nog niet wat ze betekenen)."
)
st.write(
    "Conclusie: dit zijn onze kolommen om mee te beginnen. Welke echt helpen weten we pas na de analyse en het model."
)

# stap 1
st.header("Stap 1: vertraging uitrekenen")
schedule = laad_schedule()
# vertraging zonder correctie, om te zien hoeveel vluchten over middernacht gaan
ruw = (pd.to_timedelta(schedule["ATA_ATD_ltc"]) - pd.to_timedelta(schedule["STA_STD_ltc"])).dt.total_seconds() / 60
n_middernacht = int((ruw < -180).sum())
laagste_ruw = ruw.min()

df = maak_vertraging(schedule)
st.write(
    "De tijden in de data hebben geen datum. Een vlucht die om 23:50 gepland is en om 00:10 vertrekt, "
    "lijkt dan bijna 24 uur te vroeg."
)
st.write(
    f"Bij de eerste berekening kwam de laagste waarde uit op {round(laagste_ruw)} minuten. "
    f"Dat zijn {n_middernacht} vluchten die meer dan 3 uur te vroeg lijken. Dat kan niet echt zo zijn. "
    "Bij die vluchten hebben we een dag (1440 minuten) opgeteld."
)

# crosstab van vroeg, op tijd en te laat per landing/start
groep = pd.cut(
    df["vertraging"], [-1000, 0, 15, 2000],
    labels=["te vroeg", "0 tot 15 min te laat", "meer dan 15 min te laat"],
)
kruis = (pd.crosstab(df["LSV"], groep, normalize="index") * 100).round(1)
st.write("Crosstab: percentage vluchten per groep.")
st.dataframe(kruis)
st.write(
    f"Wat opvalt: bij S is {kruis.loc['S', 'meer dan 15 min te laat']}% van de vluchten meer dan 15 minuten te laat, "
    f"bij L is dat {kruis.loc['L', 'meer dan 15 min te laat']}%. Daarom nemen we LSV mee als kolom."
)
st.write(
    "Conclusie: we hebben nu een kolom vertraging, dat is wat we gaan voorspellen. "
    "Landingen en starts verschillen, dus LSV gaat mee in het model. En we kunnen nu grafieken maken van vertraging."
)

# stap 2
st.header("Stap 2: streepjes en lege waarden")
df = streepjes_naar_leeg(df)
kolommen = ["TAR", "GAT", "RWC", "Org/Des", "DL1", "IX1", "DL2", "IX2"]
leeg = df[kolommen].isna().sum()
leeg_tabel = pd.DataFrame({"aantal leeg": leeg, "procent": (leeg / len(df) * 100).round(1)})
st.write(
    "In veel kolommen staat een streepje. Dat betekent dat de waarde onbekend is. "
    "Wij hebben alle streepjes veranderd in een lege waarde, zodat we ze kunnen tellen."
)
st.dataframe(leeg_tabel)
st.write(
    "TAR, GAT, RWC en Org/Des hebben maar een paar lege waarden. Die vluchten houden we, we laten alleen die waarde leeg. "
    "DL1 tot IX2 zijn grotendeels leeg en we weten niet wat ze betekenen. Die laten we weg."
)
st.write(
    "Conclusie: RWC en Org/Des nemen we mee, met de lege waarden als onbekend. DL1 tot IX2 gebruiken we pas als we "
    "weten wat ze betekenen. Voor het model moeten de lege waarden later nog ingevuld of apart behandeld worden."
)

# stap 3
st.header("Stap 3: uitschieters")
fig = px.box(
    df[["LSV", "vertraging"]], x="LSV", y="vertraging",
    labels={"LSV": "L of S", "vertraging": "Vertraging (minuten)"},
)
st.plotly_chart(fig)
st.write(
    "In de boxplot zie je dat de meeste vluchten dicht bij 0 zitten, maar dat er veel punten ver weg liggen. "
    "We hebben naar de uiterste waarden gekeken."
)
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
totaal = len(df)
n_laat = int((df["vertraging"] > 180).sum())

# drie manieren om met uitschieters om te gaan, om te vergelijken
opties = {
    "alles houden": df,
    "te vroege vluchten weg (onze keuze)": df[df["vertraging"] >= -60],
    "ook vluchten van meer dan 3 uur te laat weg": df[(df["vertraging"] >= -60) & (df["vertraging"] <= 180)],
}
vergelijk = pd.DataFrame(
    {
        naam: {
            "vluchten": len(d),
            "gemiddelde vertraging": round(d["vertraging"].mean(), 1),
            "mediaan": round(d["vertraging"].median(), 1),
            "% meer dan 15 min te laat": round((d["vertraging"] > 15).mean() * 100, 1),
        }
        for naam, d in opties.items()
    }
).T
df = haal_uitschieters_weg(df)
st.write(
    f"{n_weg} vluchten zijn meer dan 60 minuten te vroeg. Dat komt bijna niet voor en lijkt een fout in de data. "
    "Die halen we weg."
)
st.write(
    f"De te late vluchten laten we staan, ook de langste van {round(max_laat, 1)} uur. "
    "Die zijn echt gebeurd en wij willen juist vertraging voorspellen."
)
st.write(
    f"Er blijven {getal(len(df))} vluchten over. We hebben dus {n_weg} vluchten weggehaald, "
    f"dat is {round(n_weg / totaal * 100, 3)}% van alle vluchten."
)
st.write("Maakt onze keuze uit? We hebben drie manieren naast elkaar gelegd:")
st.dataframe(vergelijk)
st.write(
    f"Het gemiddelde is {vergelijk.iloc[0]['gemiddelde vertraging']} minuten als we alles houden en "
    f"{vergelijk.iloc[1]['gemiddelde vertraging']} minuten na onze keuze. Het percentage vluchten dat meer dan 15 minuten te laat is, "
    f"is {vergelijk.iloc[0]['% meer dan 15 min te laat']}% tegen {vergelijk.iloc[1]['% meer dan 15 min te laat']}%. "
    f"Dat is bijna hetzelfde. Ook de {getal(n_laat)} vluchten van meer dan 3 uur te laat veranderen weinig, "
    "maar die laten we toch staan omdat ze echt lijken."
)
st.write(
    "Conclusie: een paar foute vluchten kunnen het model nu niet meer scheef trekken. "
    "De zeer late vluchten blijven, dus het model moet daar ook mee kunnen omgaan. Dat letten we op bij het beoordelen van het model."
)

# stap 4
st.header("Stap 4: nieuwe kolommen")
df = maak_kolommen(df)
st.write(
    "Uit de datum en tijd halen we uur, weekdag, maand en jaar. Uit het vluchtnummer halen we de maatschappij "
    "(eerste 2 letters). Drukte is het aantal vluchten in hetzelfde uur op dezelfde dag."
)
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
    "Org/Des is de herkomst bij een landing en de bestemming bij een start. "
    "We zoeken de code op in de Kaggle-data, eerst op ICAO-code en als dat niet lukt op IATA-code."
)
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
