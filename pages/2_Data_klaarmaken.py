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


st.title("Data klaarmaken")
st.write("Hier laten we stap voor stap zien hoe we de data klaar hebben gemaakt om de vertraging te voorspellen.")
st.caption(
    "(Uitleg voor de groep: de grijze regels met haakjes zijn extra uitleg voor ons. Die halen we weg voor de presentatie. "
    "Waar de code staat: data inlezen in data.py, de opschoonstappen in schoon.py, de tekst en grafieken op deze pagina "
    "in pages/2_Data_klaarmaken.py.)"
)

# wat voorspellen we
st.header("Wat willen we voorspellen?")
st.write(
    "Vertraging zit niet als kolom in de data. Die rekenen we zelf uit: de echte tijd (ATA_ATD_ltc) "
    "min de geplande tijd (STA_STD_ltc). Dit is onze y. Een negatief getal betekent dat de vlucht te vroeg was."
)
st.caption(
    "(Uitleg voor de groep: y is wat je wilt voorspellen, X zijn de kolommen waarmee je voorspelt. "
    "STA_STD_ltc is de geplande tijd en ATA_ATD_ltc de echte tijd, ltc is waarschijnlijk lokale tijd. "
    "Het verschil rekenen we uit in de functie maak_vertraging in schoon.py.)"
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
st.caption(
    "(Uitleg voor de groep: kolommen die niet in deze tabel staan gebruiken we niet om te voorspellen. "
    "De lijst die het model straks echt gebruikt staat bovenaan schoon.py bij KOLOMMEN. "
    "Sommige daarvan, zoals uur en drukte, bestaan nog niet en maken we in stap 4.)"
)
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
st.caption(
    "(Uitleg voor de groep: de tijden zijn alleen een tijdstip, zonder datum. Daarom rekenen we in minuten en tellen we "
    "bij een negatief verschil van meer dan 3 uur een dag op. Dit staat in maak_vertraging in schoon.py.)"
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
st.caption(
    "(Uitleg voor de groep: een crosstab telt hoe vaak combinaties voorkomen. Hier staat per L en S hoeveel procent "
    "van de vluchten in elke groep valt. De groepen maken we met pd.cut, de procenten met normalize='index'. "
    "Deze code staat in pages/2_Data_klaarmaken.py.)"
)
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
st.caption(
    "(Uitleg voor de groep: leeg (NaN) betekent dat er niets staat. Een streepje is voor pandas gewoon tekst en wordt "
    "niet als leeg geteld, daarom zetten we het eerst om. Dit staat in streepjes_naar_leeg in schoon.py.)"
)
st.dataframe(leeg_tabel)
st.write(
    "TAR, GAT, RWC en Org/Des hebben maar een paar lege waarden. Die vluchten houden we, we laten alleen die waarde leeg. "
    "DL1 tot IX2 zijn grotendeels leeg en we weten niet wat ze betekenen. Die laten we weg."
)
st.caption(
    "(Uitleg voor de groep: DL1 tot IX2 staan nog wel in de data, maar niet in KOLOMMEN in schoon.py. "
    "Het model ziet ze dus niet. TAR en GAT staan ook niet in KOLOMMEN, die kunnen we er later nog bij zetten.)"
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
st.caption(
    "(Uitleg voor de groep: een boxplot laat de verdeling zien. De doos is de middelste 50% van de vluchten, "
    "de streep in de doos is de mediaan. De punten ver buiten de doos zijn uitschieters. De boxplot maken we met px.box.)"
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
df = haal_uitschieters_weg(df)
st.write(
    f"{n_weg} vluchten zijn meer dan 60 minuten te vroeg. Dat komt bijna niet voor en lijkt een fout in de data. "
    "Die halen we weg."
)
st.caption(
    "(Uitleg voor de groep: de grens van 60 minuten staat in haal_uitschieters_weg in schoon.py. "
    "Willen we een andere grens, dan veranderen we alleen dat getal.)"
)
st.write(
    f"De te late vluchten laten we staan, ook de langste van {round(max_laat, 1)} uur. "
    "Die zijn echt gebeurd en wij willen juist vertraging voorspellen."
)
st.write(f"Er blijven {getal(len(df))} vluchten over.")
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
st.caption(
    "(Uitleg voor de groep: nieuwe kolommen maken uit bestaande kolommen heet feature engineering. "
    "Een model kan niets met een tijd als tekst, maar wel met het uur als getal. Weekdag 0 is maandag en 6 is zondag. "
    "Dit staat in maak_kolommen in schoon.py.)"
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
st.write(
    f"Ook het jaar maakt uit: gemiddeld {per_jaar[2019]} minuten in 2019 en {per_jaar[2020]} minuten in 2020. "
    "Dat zal met corona te maken hebben. Het jaar nemen we daarom ook mee."
)
st.write(
    "Conclusie: uur en jaar laten duidelijk verschil zien, dus die nemen we zeker mee. "
    "Weekdag, maand, maatschappij en drukte hebben we nog niet bekeken. Dat kan bij Analyse, bijvoorbeeld met een lijngrafiek."
)

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
st.caption(
    "(Uitleg voor de groep: ICAO is een code van 4 letters voor een luchthaven (Zurich is LSZH), IATA van 3 letters (Zurich is ZRH). "
    "Koppelen betekent dat we twee tabellen samenvoegen op een kolom die ze allebei hebben. "
    "Dit staat in koppel_luchthavens in schoon.py, de luchthavens zelf komen uit laad_airports in data.py.)"
)
st.write(
    f"Van {n_codes} codes hebben we er {n_gevonden} gevonden. "
    f"Dat laat {getal(n_zonder)} vluchten zonder luchthaven, die laten we leeg. "
    "Zo hebben we per vlucht het land en de plek op de kaart."
)
st.dataframe(df[["Org/Des", "luchthaven", "land", "lat", "lon"]].dropna().drop_duplicates("Org/Des").head())
st.write(
    "Conclusie: per vlucht kunnen we nu het land gebruiken in het model, en met lat en lon later de kaart maken. "
    "De vluchten zonder luchthaven vallen buiten de kaart."
)

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
st.caption(
    "(Uitleg voor de groep: tavg is de gemiddelde temperatuur, prcp neerslag, wdir windrichting, wspd windsnelheid, "
    "wpgt windstoten, pres luchtdruk, snow sneeuw en tsun zonuren. Elke vlucht krijgt het weer van zijn dag. "
    "Dit staat in koppel_weer in schoon.py, het weer zelf komt uit laad_weer in data.py.)"
)
st.write("Lege waarden in het weer van 2019 en 2020:")
st.dataframe(leeg_weer.rename("aantal leeg"))
st.write(
    f"Snow en tsun zijn helemaal leeg, die laten we weg. Bij prcp (neerslag) missen {leeg_weer.get('prcp', 0)} dagen, "
    "die laten we leeg. De rest nemen we mee."
)

# correlatie van weer en drukte met vertraging
verband = df[["vertraging", "tavg", "prcp", "wdir", "wspd", "wpgt", "pres", "drukte"]].corr()["vertraging"]
verband = verband.drop("vertraging").round(3).reset_index()
verband.columns = ["kolom", "verband"]
fig = px.bar(verband, x="kolom", y="verband", labels={"verband": "Verband met vertraging"})
st.plotly_chart(fig)
st.caption(
    "(Uitleg voor de groep: verband (correlatie) is een getal van -1 tot 1. Dichtbij 0 is geen verband. "
    "Dichtbij 1 betekent dat als het ene hoger is, het andere ook hoger is. Hier is alles klein.)"
)
weer_verband = verband[verband["kolom"] != "drukte"]
sterkste = weer_verband.loc[weer_verband["verband"].abs().idxmax()]
drukte_verband = verband.loc[verband["kolom"] == "drukte", "verband"].iloc[0]
st.write(
    f"Wat opvalt: de weerkolommen hebben allemaal een zwak verband met vertraging. Het sterkste is {sterkste['kolom']} "
    f"met {sterkste['verband']}. Dat kan komen doordat we het weer maar per dag hebben, terwijl de vertraging per vlucht verschilt. "
    "We nemen het weer toch mee en kijken later of het model er beter van wordt."
)
st.write(
    f"Drukte heeft een sterker verband ({drukte_verband}), maar ook dat is niet groot. "
    "Waarschijnlijk komt vertraging door meerdere dingen samen."
)
st.write(
    "Conclusie: we verwachten niet dat het weer alleen de vertraging verklaart. We nemen het wel mee en testen later "
    "of het model beter wordt met of zonder weer. Dat kunnen we dan laten zien in de presentatie."
)

st.header("Klaar")
st.write(f"We hebben nu {getal(len(df))} vluchten en {df.shape[1]} kolommen. Hiermee gaan we verder bij Voorspellen.")
st.caption(
    "(Uitleg voor de groep: alle stappen achter elkaar staan in de functie laad_klaar in schoon.py. "
    "De andere pagina's gebruiken die functie, zodat we de stappen maar op een plek hoeven aan te passen.)"
)
st.write("Conclusie: de data is klaar. We kunnen nu grafieken maken bij Analyse en een model bouwen bij Voorspellen.")
st.dataframe(df.head())
