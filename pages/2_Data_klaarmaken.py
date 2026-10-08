import pandas as pd
import plotly.express as px
import streamlit as st

from data import laad_airports, laad_schedule, laad_weer
from schoon import (
    haal_uitschieters_weg, koppel_luchthavens, koppel_weer,
    maak_kolommen, maak_vertraging, streepjes_naar_leeg,
)

BLAUW = "#1f77b4"
ORANJE = "#e6550d"

# makkelijke namen voor in de grafiek
NAMEN = {
    "tavg": "temperatuur", "prcp": "neerslag", "wdir": "windrichting", "wspd": "windsnelheid",
    "wpgt": "windstoten", "pres": "luchtdruk", "drukte": "drukte",
}


def getal(n):
    return f"{n:,}".replace(",", ".")


# alle stappen na elkaar, in de volgorde van de tabs. De uitkomsten worden onthouden (cache),
# zodat de pagina snel opent
@st.cache_data
def bereken():
    r = {}

    # 1. vertraging uitrekenen
    schedule = laad_schedule()
    r["n_data"] = len(schedule)
    # vertraging zonder correctie, om te zien hoeveel vluchten over middernacht gaan
    ruw = (pd.to_timedelta(schedule["ATA_ATD_ltc"]) - pd.to_timedelta(schedule["STA_STD_ltc"])).dt.total_seconds() / 60
    r["n_middernacht"] = int((ruw < -180).sum())
    r["laagste_ruw"] = round(ruw.min())
    df = maak_vertraging(schedule)
    # percentage vroeg, op tijd en te laat per L en S
    groep = pd.cut(
        df["vertraging"], [-1000, 0, 15, 2000],
        labels=["te vroeg", "0 tot 15 min te laat", "meer dan 15 min te laat"],
    )
    kruis = (pd.crosstab(df["LSV"], groep, normalize="index") * 100).round(1)
    r["laat_s"] = kruis.loc["S", "meer dan 15 min te laat"]
    r["laat_l"] = kruis.loc["L", "meer dan 15 min te laat"]
    r["kruis"] = kruis.reset_index().melt(id_vars="LSV", var_name="groep", value_name="procent")

    # 2. streepjes en lege waarden
    df = streepjes_naar_leeg(df)
    kolommen = ["TAR", "GAT", "RWC", "Org/Des", "DL1", "IX1", "DL2", "IX2"]
    leeg = (df[kolommen].isna().mean() * 100).round(1).sort_values().reset_index()
    leeg.columns = ["kolom", "procent"]
    r["leeg"] = leeg

    # 3. uitschieters
    r["box"] = df[["LSV", "vertraging"]]
    r["totaal"] = len(df)
    r["n_weg"] = int((df["vertraging"] < -60).sum())
    r["n_laat"] = int((df["vertraging"] > 180).sum())
    r["max_laat"] = df["vertraging"].max() / 60
    r["n_buiten"] = int(((df["vertraging"] < -150) | (df["vertraging"] > 300)).sum())
    r["gem_voor"] = round(df["vertraging"].mean(), 1)
    r["pct_voor"] = round((df["vertraging"] > 15).mean() * 100, 1)
    df = haal_uitschieters_weg(df)
    r["gem_na"] = round(df["vertraging"].mean(), 1)
    r["pct_na"] = round((df["vertraging"] > 15).mean() * 100, 1)

    # 4. nieuwe kolommen
    df = maak_kolommen(df)
    r["per_uur"] = df.groupby("uur")["vertraging"].agg(["mean", "count"]).reset_index()

    # 5. luchthavens en weer koppelen
    r["n_codes"] = df["Org/Des"].nunique()
    df = koppel_luchthavens(df, laad_airports())
    r["n_gevonden"] = df.loc[df["luchthaven"].notna(), "Org/Des"].nunique()
    r["n_zonder"] = int((df["luchthaven"].isna() & df["Org/Des"].notna()).sum())
    weer = laad_weer()
    weer_jaren = weer[pd.to_datetime(weer["datum"]).dt.year.isin([2019, 2020])]
    r["weer_leeg"] = list(weer_jaren.columns[weer_jaren.isna().all()])
    df = koppel_weer(df, weer)
    # verband (correlatie) van weer en drukte met vertraging
    verband = df[["vertraging", "tavg", "prcp", "wdir", "wspd", "wpgt", "pres", "drukte"]].corr()["vertraging"]
    verband = verband.drop("vertraging").round(3).reset_index()
    verband.columns = ["kolom", "verband"]
    verband["naam"] = verband["kolom"].map(NAMEN)
    verband["soort"] = ["drukte" if k == "drukte" else "weer" for k in verband["kolom"]]
    r["verband"] = verband.sort_values("verband", key=abs)

    r["n_klaar"] = len(df)
    return r


st.set_page_config(page_title="Data klaarmaken", layout="wide")

r = bereken()

st.title("Data klaarmaken")
st.write(
    f"Van de ruwe vluchtdata naar een tabel waarmee we de vertraging kunnen voorspellen. "
    f"We begonnen met {getal(r['n_data'])} vluchten en houden er {getal(r['n_klaar'])} over."
)

st.subheader("Wat voorspellen we?")
st.write(
    "De vertraging in minuten: de echte tijd min de geplande tijd. Die kolom zit niet in de data, dus we maken hem zelf. "
    "We voorspellen met de vlucht, de tijd, de plek en het weer."
)

# vertraging uitrekenen
st.subheader("Vertraging uitrekenen")
fig = px.bar(
    r["kruis"], x="groep", y="procent", color="LSV", barmode="group", text_auto=".1f",
    color_discrete_map={"L": BLAUW, "S": ORANJE},
    labels={"groep": "", "procent": "Percentage vluchten", "LSV": "L of S"},
)
fig.update_layout(height=320, margin=dict(t=20, b=20))
st.plotly_chart(fig)
st.write(
    f"De tijden hebben geen datum, dus {r['n_middernacht']} vluchten rond middernacht leken meer dan 3 uur te vroeg. "
    "Daar tellen we een dag bij op. "
    f"Bij S is {r['laat_s']}% van de vluchten meer dan 15 minuten te laat, bij L {r['laat_l']}%. Dat verschil is groot, dus LSV gaat mee."
)

# streepjes en lege waarden
st.subheader("Lege waarden")
dl = r["leeg"][r["leeg"]["kolom"].isin(["DL1", "IX1", "DL2", "IX2"])]["procent"]
st.write(
    "Een streepje betekent onbekend, dat hebben we leeg gemaakt. TAR, GAT, RWC en Org/Des zijn bijna volledig gevuld en blijven. "
    f"DL1 tot IX2 zijn {dl.min()}% tot {dl.max()}% leeg en we weten niet wat ze betekenen, die laten we weg."
)

# uitschieters
st.subheader("Uitschieters")
# boxplot, we zoomen in op -150 tot 300 minuten
fig = px.box(
    r["box"], x="LSV", y="vertraging",
    labels={"LSV": "L of S", "vertraging": "Vertraging (minuten)"},
)
fig.add_hline(y=-60, line_dash="dot", line_color="gray", annotation_text="grens: -60 min", annotation_position="bottom right")
fig.update_yaxes(range=[-150, 300])
fig.update_layout(height=340, margin=dict(t=20, b=20))
st.plotly_chart(fig)
st.write(
    f"De grafiek is ingezoomd, {r['n_buiten']} vluchten liggen buiten beeld. "
    f"Meer dan 60 minuten te vroeg lijkt een fout, die {r['n_weg']} vluchten ({round(r['n_weg'] / r['totaal'] * 100, 3)}%) halen we weg. "
    f"Te late vluchten blijven, ook de langste van {round(r['max_laat'], 1)} uur, want dat is echte vertraging. "
    f"Het gemiddelde verandert nauwelijks ({r['gem_voor']} tegen {r['gem_na']} minuten)."
)

# nieuwe kolommen
st.subheader("Nieuwe kolommen")
per_uur = r["per_uur"]
# alleen uren met minstens 500 vluchten
genoeg = per_uur[per_uur["count"] >= 500]
hoogste = genoeg.loc[genoeg["mean"].idxmax()]
laagste = genoeg.loc[genoeg["mean"].idxmin()]
st.write(
    "Uit datum en tijd maken we uur, weekdag, maand en jaar, uit het vluchtnummer de maatschappij. "
    "Drukte is het aantal vluchten in hetzelfde uur. "
    f"Het uur maakt uit: rond {int(hoogste['uur'])} uur is de vertraging het hoogst ({round(hoogste['mean'], 1)} minuten), "
    f"rond {int(laagste['uur'])} uur het laagst ({round(laagste['mean'], 1)} minuten)."
)

# luchthavens en weer koppelen
st.subheader("Luchthavens en weer koppelen")
verband = r["verband"]
fig = px.bar(
    verband, x="verband", y="naam", color="soort", orientation="h", text_auto=".2f",
    color_discrete_map={"weer": BLAUW, "drukte": ORANJE},
    labels={"verband": "Verband met vertraging (-1 tot 1)", "naam": "", "soort": ""},
)
fig.update_layout(height=320, margin=dict(t=20, b=20))
st.plotly_chart(fig)
weer_verband = verband[verband["soort"] == "weer"]
sterkste = weer_verband.loc[weer_verband["verband"].abs().idxmax()]
drukte_verband = verband.loc[verband["soort"] == "drukte", "verband"].iloc[0]
st.write(
    f"We zochten de luchthaven op in de Kaggle-data ({r['n_gevonden']} van de {r['n_codes']} codes gevonden) en koppelden het weer per dag. "
    f"Het weer hangt zwak samen met vertraging (sterkste: {sterkste['naam']}, {sterkste['verband']}), drukte iets sterker ({drukte_verband}). "
    "We nemen ze toch mee, het model kijkt ook naar combinaties."
)
