import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from schoon import ZURICH_LAT, ZURICH_LON, laad_klaar, per_luchthaven

REGIO_NAMEN = {
    "Europe": "Europa", "Asia": "Azie", "Africa": "Afrika", "America": "Amerika",
    "Atlantic": "Atlantische eilanden", "Indian": "Indische Oceaan", "Australia": "Australie",
}
BLAUW = "#1f77b4"
ORANJE = "#e6550d"


def getal(n):
    return f"{n:,}".replace(",", ".")


# woord bij de sterkte van een verband
def sterkte(r):
    if abs(r) < 0.2:
        return "zwak"
    if abs(r) < 0.5:
        return "matig"
    return "sterk"


st.set_page_config(page_title="Bestemmingen", layout="wide")

st.title("Bestemmingen")
st.write("Deelvraag 2: verschilt de vertraging per bestemming?")

# plekken die we later invullen, zodat het antwoord en de kaart bovenaan staan
kop = st.container()
kaart_plek = st.container()

# data
df = laad_klaar()
kolommen = ["Org/Des", "luchthaven", "land", "regio", "lat", "lon", "vertraging", "LSV", "jaar"]
n_zonder = int(df["luchthaven"].isna().sum())
vluchten = df.loc[df["luchthaven"].notna(), kolommen]
alle = per_luchthaven(vluchten)

# keuzes voor de kaart staan links in de zijbalk
with st.sidebar:
    st.header("Kaart aanpassen")
    soort = st.selectbox("Soort vlucht", ["Alleen starts (bestemming)", "Alleen landingen (herkomst)", "Alle vluchten"])
    jaar = st.selectbox("Jaar", ["2019 en 2020", "2019", "2020"])
    gebied = st.selectbox("Gebied op de kaart", ["Wereld", "Europa"])
    minimum = st.slider("Minimaal aantal vluchten", 10, 1000, 100, step=10)

    deel = vluchten
    if soort.startswith("Alleen starts"):
        deel = deel[deel["LSV"] == "S"]
    elif soort.startswith("Alleen landingen"):
        deel = deel[deel["LSV"] == "L"]
    if jaar != "2019 en 2020":
        deel = deel[deel["jaar"] == int(jaar)]

    basis = per_luchthaven(deel)
    tabel = basis[basis["vluchten"] >= minimum].copy()
    landen = st.multiselect("Kies landen (leeg betekent alle landen)", sorted(tabel["land"].dropna().unique()))

zicht = tabel[tabel["land"].isin(landen)] if landen else tabel
if len(tabel) < 5 or len(zicht) < 3:
    with kaart_plek:
        st.write("Te weinig luchthavens met deze keuzes. Zet het minimale aantal vluchten lager of kies meer landen.")
    st.stop()

# cijfers die we in de tekst gebruiken
hoogste = zicht.loc[zicht["gemiddelde"].idxmax()]
laagste = zicht.loc[zicht["gemiddelde"].idxmin()]
vluchten_in_zicht = deel[deel["Org/Des"].isin(zicht["Org/Des"])]
spreiding_luchthaven = round(zicht["gemiddelde"].std(), 1)
spreiding_vluchten = round(vluchten_in_zicht["vertraging"].std(), 1)
klein_verschil = spreiding_luchthaven * 2 < spreiding_vluchten
r = zicht[["afstand", "gemiddelde"]].corr().iloc[0, 1].round(2)

# eerste laag: het antwoord en de kaart
with kop:
    if klein_verschil:
        st.subheader("Ja, de vertraging verschilt per bestemming, maar de bestemming verklaart weinig.")
    else:
        st.subheader("Ja, de vertraging verschilt flink per bestemming.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Meeste vertraging", f"{hoogste['gemiddelde']} min")
    m1.caption(hoogste["luchthaven"])
    m2.metric("Minste vertraging", f"{laagste['gemiddelde']} min")
    m2.caption(laagste["luchthaven"])
    m3.metric("Verschil tussen luchthavens", f"{spreiding_luchthaven} min")
    m3.caption("spreiding van de gemiddelden")
    m4.metric("Verschil tussen vluchten", f"{spreiding_vluchten} min")
    m4.caption("spreiding van alle vluchten")

# luchthavens indelen in 5 gelijke groepen (kwantielen) op gemiddelde vertraging
klassen = pd.qcut(tabel["gemiddelde"], 5, duplicates="drop")
namen = [f"{k.left:.1f} tot {k.right:.1f} min" for k in klassen.cat.categories]
tabel["klasse"] = [namen[c] for c in klassen.cat.codes]
zicht = tabel[tabel["land"].isin(landen)] if landen else tabel
n_groepen = len(namen)
kleuren = px.colors.sample_colorscale("YlOrRd", [0.15 + 0.8 * i / max(n_groepen - 1, 1) for i in range(n_groepen)])

with kaart_plek:
    fig = px.scatter_geo(
        zicht, lat="lat", lon="lon", size="vluchten", color="klasse",
        category_orders={"klasse": namen}, color_discrete_sequence=kleuren,
        hover_name="luchthaven",
        hover_data={"land": True, "vluchten": True, "gemiddelde": True, "klasse": False, "lat": False, "lon": False},
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
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), legend_title_text="Gem. vertraging per luchthaven")
    st.plotly_chart(fig)
    st.write(
        "Elke stip is een luchthaven. Grootte is het aantal vluchten, kleur is de gemiddelde vertraging "
        f"in {n_groepen} gelijke groepen. De zwarte ster is Zurich. "
        f"Luchthavens met minder dan {minimum} vluchten laten we weg, omdat hun gemiddelde niet betrouwbaar is."
    )

# tweede laag: de onderbouwing
st.header("Hoe komen we hieraan?")
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Hoogste en laagste", "Werelddelen", "Afstand", "Welke luchthavens tellen mee", "Klopt onze conclusie?"]
)

with tab1:
    kijk = ["luchthaven", "land", "vluchten", "gemiddelde"]
    links, rechts = st.columns(2)
    for kolom, data, kleur, titel in [
        (links, zicht.nlargest(10, "gemiddelde")[kijk], ORANJE, "Meeste vertraging"),
        (rechts, zicht.nsmallest(10, "gemiddelde")[kijk], BLAUW, "Minste vertraging"),
    ]:
        with kolom:
            fig = px.bar(
                data, x="gemiddelde", y="luchthaven", orientation="h", title=titel,
                hover_data={"land": True, "vluchten": True},
                labels={"gemiddelde": "Gem. vertraging (min)", "luchthaven": ""},
            )
            fig.update_traces(marker_color=kleur)
            fig.update_layout(yaxis=dict(autorange="reversed"), height=380, margin=dict(l=0, r=10, t=40, b=0))
            st.plotly_chart(fig)
    verschil = round(hoogste["gemiddelde"] - laagste["gemiddelde"], 1)
    st.markdown(
        f"**Wat we deden.** We hebben de 10 luchthavens met de meeste en de minste gemiddelde vertraging naast elkaar gezet.\n\n"
        f"**Wat opvalt.** Tussen de hoogste ({hoogste['luchthaven']}) en de laagste ({laagste['luchthaven']}) zit {verschil} minuten verschil.\n\n"
        "**Waarom.** Zo zien we direct welke bestemmingen er echt uitspringen."
    )

with tab2:
    jaar_deel = vluchten if jaar == "2019 en 2020" else vluchten[vluchten["jaar"] == int(jaar)]
    regio = jaar_deel.groupby(["regio", "LSV"])["vertraging"].agg(["size", "mean"]).round(1).reset_index()
    regio.columns = ["regio", "LSV", "vluchten", "gemiddelde"]
    grote_regios = regio.groupby("regio")["vluchten"].sum()
    regio = regio[regio["regio"].isin(grote_regios[grote_regios >= 1000].index)].copy()
    regio["werelddeel"] = regio["regio"].map(REGIO_NAMEN).fillna(regio["regio"])
    regio["soort"] = regio["LSV"].map({"S": "Start", "L": "Landing"})
    fig = px.bar(
        regio, x="werelddeel", y="gemiddelde", color="soort", barmode="group",
        color_discrete_map={"Start": ORANJE, "Landing": BLAUW}, hover_data={"vluchten": True},
        labels={"werelddeel": "", "gemiddelde": "Gem. vertraging (min)", "soort": ""},
    )
    fig.update_layout(height=380, margin=dict(t=20))
    st.plotly_chart(fig)
    start = regio[regio["LSV"] == "S"].set_index("werelddeel")["gemiddelde"]
    landing = regio[regio["LSV"] == "L"].set_index("werelddeel")["gemiddelde"]
    tekst = (
        "**Wat we deden.** We hebben de vluchten per werelddeel bij elkaar gezet, voor starts en landingen apart. "
        "Het werelddeel halen we uit de tijdzone van de luchthaven.\n\n"
    )
    if len(start) >= 2 and len(landing) >= 2:
        tekst += (
            f"**Wat opvalt.** Bij starts is de vertraging het hoogst naar {start.idxmax()} ({start.max()} min) en het laagst naar "
            f"{start.idxmin()} ({start.min()} min). Bij landingen is het hoogst uit {landing.idxmax()} ({landing.max()} min) en het laagst uit "
            f"{landing.idxmin()} ({landing.min()} min).\n\n"
        )
        if start.idxmax() == landing.idxmin():
            tekst += (
                f"{start.idxmax()} heeft dus de meeste vertraging bij vertrek en de minste bij aankomst. "
                "Misschien halen die vluchten onderweg tijd in of is de aankomsttijd ruim gepland, maar dat kunnen we met deze data niet bewijzen.\n\n"
            )
    tekst += (
        "**Waarom.** Losse luchthavens zijn lastig te vergelijken. Per werelddeel zie je sneller of er een patroon is. "
        "Werelddelen met minder dan 1.000 vluchten laten we weg."
    )
    st.markdown(tekst)

with tab3:
    fig = px.scatter(
        zicht, x="afstand", y="gemiddelde", hover_name="luchthaven",
        hover_data={"land": True, "vluchten": True},
        labels={"afstand": "Afstand tot Zurich (km)", "gemiddelde": "Gem. vertraging (min)"},
    )
    fig.update_traces(marker_color=BLAUW)
    fig.update_layout(height=380, margin=dict(t=20))
    st.plotly_chart(fig)
    st.markdown(
        "**Wat we deden.** We hebben de afstand tot Zurich uitgerekend en tegen de gemiddelde vertraging gezet. Elke stip is een luchthaven.\n\n"
        f"**Wat opvalt.** Het verband is {sterkte(r)} ({r}). Een verband van 0 is geen verband en 1 is een perfect verband.\n\n"
        "**Waarom.** We dachten dat vluchten naar verre bestemmingen vaker te laat zijn."
    )

with tab4:
    zoom = 500
    alle["status"] = ["valt weg" if n < 100 else "blijft" for n in alle["vluchten"]]
    mediaan = int(alle["vluchten"].median())
    n_weg = int((alle["vluchten"] < 100).sum())
    n_blijft = len(alle) - n_weg
    n_boven = int((alle["vluchten"] > zoom).sum())
    fig = px.strip(
        alle[alle["vluchten"] <= zoom], x="vluchten", color="status", stripmode="overlay",
        color_discrete_map={"valt weg": ORANJE, "blijft": BLAUW},
        hover_name="luchthaven", hover_data={"vluchten": True, "land": True, "status": False},
        labels={"vluchten": "Aantal vluchten", "status": ""},
        title="Elke stip is een luchthaven",
    )
    fig.update_traces(jitter=1, marker=dict(size=8, opacity=0.6))
    fig.update_yaxes(visible=False)
    fig.update_xaxes(range=[-15, zoom])
    fig.add_vrect(x0=0, x1=100, fillcolor=ORANJE, opacity=0.08, line_width=0,
                  annotation_text=f"valt weg: {n_weg}", annotation_position="top")
    fig.add_vrect(x0=100, x1=zoom, fillcolor=BLAUW, opacity=0.05, line_width=0,
                  annotation_text=f"blijft: {n_blijft}", annotation_position="top")
    fig.add_vline(x=mediaan, line_dash="dot", line_color="gray", line_width=1)
    fig.add_annotation(x=mediaan, y=0.06, yref="paper", xanchor="right", xshift=-4, showarrow=False, text=f"helft: {mediaan}")
    fig.add_annotation(x=zoom, xref="x", y=0.06, yref="paper", xanchor="right", showarrow=False, text=f"+{n_boven} luchthavens buiten beeld")
    fig.update_layout(height=400, margin=dict(t=80, b=50))
    st.plotly_chart(fig)
    onder = alle[alle["vluchten"] < 100]
    st.markdown(
        "**Wat we deden.** We hebben per luchthaven het aantal vluchten geteld en de luchthavens met minder dan 100 vluchten weggelaten. "
        f"De grafiek is ingezoomd tot {zoom} vluchten. Daarboven zitten nog {n_boven} drukkere luchthavens, tot {getal(int(alle['vluchten'].max()))} vluchten.\n\n"
        f"**Wat opvalt.** De meeste luchthavens zijn klein: de helft heeft {mediaan} vluchten of minder en een kwart maar {int(alle['vluchten'].quantile(0.25))} of minder. "
        f"De {len(onder)} luchthavens onder de grens zijn samen maar {round(onder['vluchten'].sum() / len(vluchten) * 100, 1)}% van alle vluchten.\n\n"
        "**Waarom.** Het gemiddelde van een luchthaven met een paar vluchten zegt niets en kan flink uitschieten. "
        f"We verliezen bijna geen vluchten, en de gemiddelden worden betrouwbaarder. Daarnaast hebben we {getal(n_zonder)} vluchten zonder luchthaven "
        f"weggelaten ({round(n_zonder / len(df) * 100, 2)}%)."
    )

with tab5:
    # spreiding voor een groepje luchthavens
    def maak_rij(naam, t):
        in_t = deel[deel["Org/Des"].isin(t["Org/Des"])]
        return [
            {"keuze": naam, "soort": "tussen luchthavens", "minuten": round(t["gemiddelde"].std(), 1)},
            {"keuze": naam, "soort": "tussen vluchten", "minuten": round(in_t["vertraging"].std(), 1)},
        ]

    rijen = []
    for m in [30, 100, 500]:
        t = basis[basis["vluchten"] >= m]
        if len(t) >= 3:
            rijen += maak_rij(f"minimaal {m} vluchten", t)
    t100 = basis[basis["vluchten"] >= 100]
    if len(t100) >= 4:
        rijen += maak_rij("zonder luchthaven met meeste vertraging", t100.drop(t100["gemiddelde"].idxmax()))
    robuust = pd.DataFrame(rijen)
    fig = px.bar(
        robuust, x="keuze", y="minuten", color="soort", barmode="group",
        color_discrete_map={"tussen luchthavens": ORANJE, "tussen vluchten": BLAUW},
        labels={"keuze": "", "minuten": "Spreiding (min)", "soort": ""},
    )
    fig.update_layout(height=380, margin=dict(t=20))
    st.plotly_chart(fig)
    alles_klein = (
        robuust.pivot(index="keuze", columns="soort", values="minuten")
        .pipe(lambda p: (p["tussen luchthavens"] * 2 < p["tussen vluchten"]).all())
    )
    st.markdown(
        "**Wat we deden.** We hebben onze conclusie opnieuw berekend met een andere grens voor het aantal vluchten, "
        "en ook zonder de luchthaven met de meeste vertraging.\n\n"
        + (
            "**Wat opvalt.** Bij elke keuze verschillen de luchthavens veel minder van elkaar dan de vluchten onderling. "
            "De conclusie blijft dus hetzelfde.\n\n"
            if alles_klein
            else "**Wat opvalt.** Bij sommige keuzes verschillen de luchthavens meer van elkaar dan bij onze standaardkeuze. Let dus op met de conclusie.\n\n"
        )
        + f"**Waarom.** Zo weten we dat onze keuzes de conclusie niet bepalen. We hebben bewust geen luchthaven weggehaald omdat de vertraging hoog is: "
        f"{hoogste['luchthaven']} blijft staan, met {getal(int(hoogste['vluchten']))} vluchten is het gemiddelde betrouwbaar genoeg."
    )
