import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from schoon import ZURICH_LAT, ZURICH_LON, laad_klaar, per_luchthaven

REGIO_NAMEN = {
    "Europe": "Europa", "Asia": "Azie", "Africa": "Afrika", "America": "Amerika",
    "Atlantic": "Atlantische eilanden", "Indian": "Indische Oceaan", "Australia": "Australie",
}


def getal(n):
    return f"{n:,}".replace(",", ".")


# woord bij de sterkte van een verband
def sterkte(r):
    if abs(r) < 0.2:
        return "zwak"
    if abs(r) < 0.5:
        return "matig"
    return "sterk"


st.title("Bestemmingen")
st.write("Deelvraag 2: verschilt de vertraging per bestemming?")
st.caption(
    "(Uitleg voor de groep: de tekst en grafieken staan in pages/4_Bestemmingen.py. "
    "De berekeningen per luchthaven (per_luchthaven) en de afstand (afstand_tot_zurich) staan onderaan schoon.py.)"
)

# stap 1
st.header("Stap 1: welke data gebruiken we?")
df = laad_klaar()
kolommen = ["Org/Des", "luchthaven", "land", "regio", "lat", "lon", "vertraging", "LSV", "jaar"]
n_zonder = int(df["luchthaven"].isna().sum())
vluchten = df.loc[df["luchthaven"].notna(), kolommen]
st.write(
    "We gebruiken de schone data van Data klaarmaken. Per vlucht hebben we de vertraging en de luchthaven waar "
    "de vlucht vandaan komt of naartoe gaat (Org/Des), met het land, het werelddeel en de plek op de kaart (lat en lon)."
)
st.write(
    "Bij een start (S) is dat de bestemming en bij een landing (L) de herkomst. Daarom kun je hieronder kiezen "
    f"welke vluchten je wilt zien. Vluchten zonder luchthaven laten we weg: {getal(n_zonder)} vluchten, "
    f"dat is {round(n_zonder / len(df) * 100, 2)}% van alle vluchten."
)
st.dataframe(vluchten.head())
st.caption(
    "(Uitleg voor de groep: df komt uit laad_klaar() in schoon.py, dus alle opschoonstappen zijn al gedaan. "
    "Het werelddeel (regio) halen we uit de tijdzone van de luchthaven, bijvoorbeeld Europe uit Europe/Zurich. "
    "Dat gebeurt in koppel_luchthavens in schoon.py.)"
)

# stap 2
st.header("Stap 2: per luchthaven samenvatten")
alle = per_luchthaven(vluchten)
st.write(
    "We willen een getal per luchthaven: de gemiddelde vertraging. Daarvoor groeperen we de vluchten per luchthaven. "
    "Maar sommige luchthavens hebben maar een paar vluchten, en dan zegt een gemiddelde niet veel."
)
grenzen = pd.DataFrame(
    {
        "minimaal aantal vluchten": [1, 30, 100, 500],
        "luchthavens": [int((alle["vluchten"] >= m).sum()) for m in [1, 30, 100, 500]],
        "vluchten": [int(alle.loc[alle["vluchten"] >= m, "vluchten"].sum()) for m in [1, 30, 100, 500]],
    }
)
st.dataframe(grenzen, hide_index=True)
n100 = grenzen.loc[grenzen["minimaal aantal vluchten"] == 100].iloc[0]
st.write(
    f"Er zijn {len(alle)} luchthavens, maar de helft heeft minder dan {int(alle['vluchten'].median())} vluchten. "
    f"Als we minimaal 100 vluchten vragen, houden we {n100['luchthavens']} luchthavens over. "
    f"Dat zijn nog {round(n100['vluchten'] / len(vluchten) * 100, 1)}% van alle vluchten."
)
# grafiek: elke stip is een luchthaven, ingezoomd op de luchthavens met weinig vluchten
zoom = 500
alle["status"] = ["valt weg" if n < 100 else "blijft" for n in alle["vluchten"]]
mediaan = int(alle["vluchten"].median())
n_weg = int((alle["vluchten"] < 100).sum())
n_blijft = len(alle) - n_weg
n_boven = int((alle["vluchten"] > zoom).sum())
fig = px.strip(
    alle[alle["vluchten"] <= zoom], x="vluchten", color="status", stripmode="overlay",
    color_discrete_map={"valt weg": "#e6550d", "blijft": "#1f77b4"},
    hover_name="luchthaven", hover_data={"vluchten": True, "land": True, "status": False},
    labels={"vluchten": "Aantal vluchten van de luchthaven", "status": ""},
    title=f"Elke stip is een luchthaven (ingezoomd tot {zoom} vluchten)",
)
fig.update_traces(jitter=1, marker=dict(size=8, opacity=0.6))
fig.update_yaxes(visible=False)
fig.update_xaxes(range=[-15, zoom])
fig.add_vrect(
    x0=0, x1=100, fillcolor="#e6550d", opacity=0.08, line_width=0,
    annotation_text=f"valt weg<br>{n_weg} luchthavens", annotation_position="top",
)
fig.add_vrect(
    x0=100, x1=zoom, fillcolor="#1f77b4", opacity=0.05, line_width=0,
    annotation_text=f"blijft: {n_blijft} luchthavens", annotation_position="top",
)
fig.add_vline(x=mediaan, line_dash="dot", line_color="gray", line_width=1)
fig.add_annotation(
    x=mediaan, y=0.08, yref="paper", xanchor="right", xshift=-4, showarrow=False,
    text=f"helft: {mediaan} vluchten of minder",
)
fig.add_annotation(
    x=zoom, xref="x", y=0.08, yref="paper", xanchor="right", showarrow=False, align="right",
    text=f"nog {n_boven} luchthavens met meer dan {zoom} vluchten<br>(tot {getal(int(alle['vluchten'].max()))} vluchten) staan buiten beeld",
)
fig.update_layout(height=420, margin=dict(t=110, b=60))
st.plotly_chart(fig)

st.write(
    f"Wat opvalt: de meeste stippen liggen links. De helft van de luchthavens heeft {mediaan} vluchten of minder, "
    f"en een kwart heeft er maar {int(alle['vluchten'].quantile(0.25))} of minder. De meeste luchthavens zijn dus klein. "
    f"De grafiek is ingezoomd tot {zoom} vluchten. De {n_boven} drukkere luchthavens staan buiten beeld."
)
onder = alle[alle["vluchten"] < 100]
st.write(
    f"{len(onder)} van de {len(alle)} luchthavens hebben minder dan 100 vluchten (oranje). "
    f"Samen zijn dat maar {getal(int(onder['vluchten'].sum()))} vluchten, "
    f"{round(onder['vluchten'].sum() / len(vluchten) * 100, 1)}% van alle vluchten. "
    "De meeste vluchten zitten dus bij de luchthavens die we houden (blauw)."
)
st.caption(
    "(Uitleg voor de groep: dit heet een strip plot. De plek links of rechts is het aantal vluchten van een luchthaven. "
    "De hoogte betekent niets, die is willekeurig (jitter) zodat de stippen niet over elkaar liggen. "
    "We zoomen in op de luchthavens met weinig vluchten, anders is de grens van 100 niet te zien. "
    "Je kunt in de grafiek zelf ook verder inzoomen door een stuk te slepen. Dit maken we met px.strip.)"
)
st.caption(
    "(Uitleg voor de groep: groupby maakt groepjes, hier een groepje per luchthaven. Daarna rekenen we per groepje "
    "het aantal vluchten en het gemiddelde uit. Dat doet de functie per_luchthaven in schoon.py.)"
)
st.write(
    "Conclusie: een grens van 100 vluchten kost bijna geen vluchten, maar maakt de gemiddelden wel veel betrouwbaarder. "
    "Hieronder kun je de grens zelf aanpassen. In stap 8 laten we zien dat onze conclusie niet van deze grens afhangt."
)

# stap 3
st.header("Stap 3: de kaart")
kolom1, kolom2, kolom3, kolom4 = st.columns(4)
soort = kolom1.selectbox("Soort vlucht", ["Alleen starts (bestemming)", "Alleen landingen (herkomst)", "Alle vluchten"])
jaar = kolom2.selectbox("Jaar", ["2019 en 2020", "2019", "2020"])
gebied = kolom3.selectbox("Gebied op de kaart", ["Wereld", "Europa"])
minimum = kolom4.slider("Minimaal aantal vluchten", 10, 1000, 100, step=10)

# vluchten filteren op de keuzes
deel = vluchten
if soort.startswith("Alleen starts"):
    deel = deel[deel["LSV"] == "S"]
elif soort.startswith("Alleen landingen"):
    deel = deel[deel["LSV"] == "L"]
if jaar != "2019 en 2020":
    deel = deel[deel["jaar"] == int(jaar)]

basis = per_luchthaven(deel)
tabel = basis[basis["vluchten"] >= minimum].copy()
if len(tabel) < 5:
    st.write("Te weinig luchthavens met deze keuzes. Zet het minimale aantal vluchten lager.")
    st.stop()

# luchthavens indelen in 5 gelijke groepen (kwantielen) op gemiddelde vertraging
klassen = pd.qcut(tabel["gemiddelde"], 5, duplicates="drop")
namen = [f"{k.left:.1f} tot {k.right:.1f} min" for k in klassen.cat.categories]
tabel["klasse"] = [namen[c] for c in klassen.cat.codes]
n_groepen = len(namen)
kleuren = px.colors.sample_colorscale("YlOrRd", [0.15 + 0.8 * i / max(n_groepen - 1, 1) for i in range(n_groepen)])

landen = st.multiselect("Kies landen (leeg betekent alle landen)", sorted(tabel["land"].dropna().unique()))
zicht = tabel[tabel["land"].isin(landen)] if landen else tabel
if len(zicht) < 3:
    st.write("Te weinig luchthavens met deze keuzes. Kies meer landen of zet het minimale aantal vluchten lager.")
    st.stop()

st.write(
    "Elke stip is een luchthaven. Hoe groter de stip, hoe meer vluchten. De kleur laat de gemiddelde vertraging zien: "
    "hoe donkerder, hoe meer vertraging. De zwarte ster is Zurich."
)
fig = px.scatter_geo(
    zicht, lat="lat", lon="lon", size="vluchten", color="klasse",
    category_orders={"klasse": namen}, color_discrete_sequence=kleuren,
    hover_name="luchthaven", hover_data={"land": True, "vluchten": True, "gemiddelde": True, "klasse": False, "lat": False, "lon": False},
    size_max=28, projection="natural earth",
    labels={"klasse": "Gem. vertraging", "gemiddelde": "Gem. vertraging (min)"},
)
fig.add_trace(
    go.Scattergeo(
        lat=[ZURICH_LAT], lon=[ZURICH_LON], mode="markers", name="Zurich",
        marker=dict(symbol="star", size=14, color="black"),
    )
)
fig.update_geos(showcountries=True, showland=True, landcolor="#f0f0f0")
if gebied == "Europa":
    fig.update_geos(scope="europe")
fig.update_layout(height=550, margin=dict(l=0, r=0, t=0, b=0), legend_title_text="Gem. vertraging per luchthaven")
st.plotly_chart(fig)

hoogste = zicht.loc[zicht["gemiddelde"].idxmax()]
laagste = zicht.loc[zicht["gemiddelde"].idxmin()]
st.write(
    f"De kleuren zijn {n_groepen} gelijke groepen (kwantielen): in elke groep zit ongeveer evenveel luchthavens. "
    f"Zo bepaalt een luchthaven met een heel hoge vertraging, zoals {tabel.loc[tabel['gemiddelde'].idxmax(), 'luchthaven']} "
    f"({tabel['gemiddelde'].max()} minuten), niet de hele kleurschaal."
)
st.caption(
    "(Uitleg voor de groep: bij een gewone kleurschaal krijgt de hoogste waarde de donkerste kleur en lijken alle andere "
    "stippen bijna hetzelfde. Met pd.qcut verdelen we de luchthavens in 5 groepen van gelijke grootte, en elke groep krijgt een kleur. "
    "px.scatter_geo zet de punten op de kaart met lat en lon. Zurich voegen we er apart bij met go.Scattergeo.)"
)
st.write(
    f"Wat opvalt: de hoogste gemiddelde vertraging is bij {hoogste['luchthaven']} ({hoogste['land']}) met "
    f"{hoogste['gemiddelde']} minuten. De laagste is bij {laagste['luchthaven']} ({laagste['land']}) met "
    f"{laagste['gemiddelde']} minuten."
)

# stap 4
st.header("Stap 4: is er een patroon per werelddeel?")
jaar_deel = vluchten if jaar == "2019 en 2020" else vluchten[vluchten["jaar"] == int(jaar)]
regio = jaar_deel.groupby(["regio", "LSV"])["vertraging"].agg(["size", "mean"]).round(1).reset_index()
regio.columns = ["regio", "LSV", "vluchten", "gemiddelde"]
grote_regios = regio.groupby("regio")["vluchten"].sum()
regio = regio[regio["regio"].isin(grote_regios[grote_regios >= 1000].index)].copy()
regio["werelddeel"] = regio["regio"].map(REGIO_NAMEN).fillna(regio["regio"])
regio["soort"] = regio["LSV"].map({"S": "Start", "L": "Landing"})
st.write(
    "Op de kaart zie je losse luchthavens. Daarom zetten we de vluchten ook per werelddeel naast elkaar, "
    "voor starts en landingen apart."
)
fig = px.bar(
    regio, x="werelddeel", y="gemiddelde", color="soort", barmode="group",
    hover_data={"vluchten": True},
    labels={"werelddeel": "Werelddeel", "gemiddelde": "Gem. vertraging (min)", "soort": ""},
)
st.plotly_chart(fig)
st.caption(
    "(Uitleg voor de groep: het werelddeel halen we uit de tijdzone van de luchthaven (kolom regio). "
    "Werelddelen met minder dan 1000 vluchten laten we weg, dan zegt het gemiddelde te weinig. "
    "De grafiek maken we met px.bar met barmode='group'.)"
)
start = regio[regio["LSV"] == "S"].set_index("werelddeel")["gemiddelde"]
landing = regio[regio["LSV"] == "L"].set_index("werelddeel")["gemiddelde"]
if len(start) >= 2 and len(landing) >= 2:
    st.write(
        f"Wat opvalt: bij starts is de vertraging het hoogst naar {start.idxmax()} ({start.max()} minuten) en het laagst naar "
        f"{start.idxmin()} ({start.min()} minuten). Bij landingen is dat het hoogst uit {landing.idxmax()} ({landing.max()} minuten) "
        f"en het laagst uit {landing.idxmin()} ({landing.min()} minuten)."
    )
    if start.idxmax() == landing.idxmin():
        st.write(
            f"Het patroon: {start.idxmax()} heeft de meeste vertraging bij vertrek, maar de minste bij aankomst. "
            "Een mogelijke verklaring is dat vluchten hier onderweg tijd inhalen of ruim gepland zijn. "
            "Dat kunnen we met deze data niet bewijzen."
        )

# stap 5
st.header("Stap 5: hoogste en laagste")
kijk = ["luchthaven", "land", "vluchten", "gemiddelde"]
links, rechts = st.columns(2)
with links:
    st.write("Gemiddeld de meeste vertraging")
    st.dataframe(zicht.nlargest(10, "gemiddelde")[kijk], hide_index=True)
with rechts:
    st.write("Gemiddeld de minste vertraging")
    st.dataframe(zicht.nsmallest(10, "gemiddelde")[kijk], hide_index=True)
verschil = round(hoogste["gemiddelde"] - laagste["gemiddelde"], 1)
st.write(
    f"Conclusie: tussen de luchthaven met de meeste en de minste vertraging zit {verschil} minuten verschil. "
    "Of dat aan de luchthaven zelf ligt of aan iets anders, zoeken we in de volgende stappen uit."
)

# stap 6
st.header("Stap 6: ligt het aan de afstand?")
st.write(
    "Een idee is dat vluchten naar verre bestemmingen vaker te laat zijn. Daarom rekenen we de afstand tot Zurich uit "
    "en zetten die tegen de gemiddelde vertraging."
)
fig = px.scatter(
    zicht, x="afstand", y="gemiddelde", hover_name="luchthaven",
    hover_data={"land": True, "vluchten": True},
    labels={"afstand": "Afstand tot Zurich (km)", "gemiddelde": "Gem. vertraging (min)"},
)
st.plotly_chart(fig)
st.caption(
    "(Uitleg voor de groep: de afstand rekenen we uit met de haversine-formule, die uit lat en lon de afstand over "
    "de aarde berekent. Dat staat in afstand_tot_zurich in schoon.py. Elk punt is een luchthaven.)"
)
r = zicht[["afstand", "gemiddelde"]].corr().iloc[0, 1].round(2)
st.write(
    f"Het verband tussen afstand en vertraging is {sterkte(r)} ({r}). "
    "Een verband van 0 is geen verband en 1 is een perfect verband."
)

# stap 7
st.header("Stap 7: hoe groot is het verschil?")
vluchten_in_zicht = deel[deel["Org/Des"].isin(zicht["Org/Des"])]
spreiding_luchthaven = round(zicht["gemiddelde"].std(), 1)
spreiding_vluchten = round(vluchten_in_zicht["vertraging"].std(), 1)
st.write(
    f"De gemiddelden van de luchthavens verschillen ongeveer {spreiding_luchthaven} minuten van elkaar "
    f"(standaardafwijking). Maar de vluchten zelf verschillen ongeveer {spreiding_vluchten} minuten van elkaar."
)
st.caption(
    "(Uitleg voor de groep: standaardafwijking is hoeveel de getallen gemiddeld van het gemiddelde afliggen. "
    "Een kleine spreiding tussen luchthavens ten opzichte van de spreiding tussen vluchten betekent dat de luchthaven "
    "maar een klein deel van de vertraging verklaart.)"
)

# stap 8
st.header("Stap 8: hangt onze conclusie af van onze keuzes?")
st.write(
    "We hebben twee keuzes gemaakt: de grens van 100 vluchten, en we hebben geen luchthaven weggehaald omdat de vertraging "
    "hoog is. Daarom rekenen we stap 7 opnieuw met andere grenzen, en ook zonder de luchthaven met de hoogste vertraging."
)


# een rij voor de tabel: de spreiding voor een groepje luchthavens
def maak_rij(naam, t):
    in_t = deel[deel["Org/Des"].isin(t["Org/Des"])]
    return {
        "keuze": naam,
        "luchthavens": len(t),
        "verschil hoogste en laagste": round(t["gemiddelde"].max() - t["gemiddelde"].min(), 1),
        "spreiding luchthavens": round(t["gemiddelde"].std(), 1),
        "spreiding vluchten": round(in_t["vertraging"].std(), 1),
    }


rijen = []
for m in [30, 100, 500]:
    t = basis[basis["vluchten"] >= m]
    if len(t) >= 3:
        rijen.append(maak_rij(f"minimaal {m} vluchten", t))
t100 = basis[basis["vluchten"] >= 100]
if len(t100) >= 4:
    zonder = t100.drop(t100["gemiddelde"].idxmax())
    rijen.append(maak_rij("minimaal 100, zonder de luchthaven met de hoogste vertraging", zonder))
robuust = pd.DataFrame(rijen)
st.dataframe(robuust, hide_index=True)
st.caption(
    "(Uitleg voor de groep: dit heet een robuustheidscheck. We veranderen een keuze en kijken of de uitkomst hetzelfde blijft. "
    "Blijft de uitkomst gelijk, dan hangt de conclusie niet van die keuze af.)"
)
st.write(
    f"We hebben {hoogste['luchthaven']} niet weggehaald, ook al heeft die de hoogste vertraging. Er zijn {hoogste['vluchten']} vluchten, "
    "dus het gemiddelde is niet toeval van een paar vluchten."
)
if (robuust["spreiding luchthavens"] * 2 < robuust["spreiding vluchten"]).all():
    st.write(
        "Conclusie: bij elke keuze verschillen de luchthavens veel minder van elkaar dan de vluchten onderling. "
        "Onze conclusie hangt dus niet af van de grens of van die ene luchthaven."
    )
else:
    st.write(
        "Conclusie: bij sommige keuzes verschillen de luchthavens meer van elkaar dan bij onze standaardkeuze. "
        "Let dus op met de conclusie bij deze keuzes."
    )

# conclusie
st.header("Conclusie")
st.write(
    f"De gemiddelde vertraging per bestemming loopt van {laagste['gemiddelde']} tot {hoogste['gemiddelde']} minuten. "
    f"De bestemmingen verschillen {spreiding_luchthaven} minuten van elkaar, maar vluchten onderling "
    f"verschillen {spreiding_vluchten} minuten."
)
if spreiding_luchthaven * 2 < spreiding_vluchten:
    st.write("De bestemming alleen verklaart dus maar een klein deel van de vertraging.")
else:
    st.write("De bestemming verklaart bij deze keuzes dus een flink deel van de vertraging.")
st.write(
    f"De afstand heeft een {sterkte(r)} verband met de vertraging ({r}). "
    "Bij deelvraag 3 testen we of het land of de afstand het model beter maakt."
)
