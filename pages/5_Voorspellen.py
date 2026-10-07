
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
 
from schoon import KOLOMMEN, laad_klaar, maak_train_test

st.set_page_config(page_title="Voorspellen", layout="wide")

 
# kolommen met tekst, die moeten we omzetten naar getallen voor het model
TEKST_KOLOMMEN = ["LSV", "ACT", "RWC", "maatschappij", "land"]
 
# bij welke groep hoort elke kolom
GROEPEN = {
    "tavg": "Weer", "prcp": "Weer", "wdir": "Weer", "wspd": "Weer", "wpgt": "Weer", "pres": "Weer",
    "drukte": "Drukte",
    "RWY": "Baan", "RWC": "Baan",
    "ACT": "Vliegtuigtype",
    "uur": "Tijd", "weekdag": "Tijd", "maand": "Tijd", "jaar": "Tijd",
    "LSV": "Overig", "maatschappij": "Overig", "land": "Overig",
}
 
# makkelijke namen voor in de grafiek
NAMEN = {
    "tavg": "temperatuur", "prcp": "neerslag", "wdir": "windrichting", "wspd": "windsnelheid",
    "wpgt": "windstoten", "pres": "luchtdruk", "drukte": "drukte", "RWY": "baan", "RWC": "baanconfiguratie",
    "ACT": "vliegtuigtype", "uur": "uur", "weekdag": "weekdag", "maand": "maand", "jaar": "jaar",
    "LSV": "landing of vertrek", "maatschappij": "maatschappij", "land": "land",
}
 
 
# tekst omzetten naar getallen en lege waarden vullen met -1
def maak_getallen(df):
    df = df.copy()
    for kolom in TEKST_KOLOMMEN:
        df[kolom] = df[kolom].astype("category").cat.codes
    df[KOLOMMEN] = df[KOLOMMEN].fillna(-1)
    return df
 
 
# het model trainen, door cache_resource hoeft dit maar 1 keer
@st.cache_resource
def train_model(X_train, y_train):
    model = RandomForestRegressor(n_estimators=50, max_depth=12, min_samples_leaf=20, n_jobs=-1, random_state=42)
    model.fit(X_train, y_train)
    return model
 
 
st.title("Voorspellen")
st.write("Deelvraag 3: welke kenmerken (weer, drukte, baan, vliegtuigtype) voorspellen de vertraging, en hoe goed doet ons model dat?")
 
# data splitsen in train en test
st.header("Stap 1: data splitsen")
df = maak_getallen(laad_klaar())
X_train, X_test, y_train, y_test = maak_train_test(df)
st.write(
    "We verdelen de vluchten in twee delen. Met 80% leert het model (de trainset). "
    "De andere 20% krijgt het model niet te zien (de testset). Daarmee controleren we aan het eind "
    "of het model ook goed voorspelt bij vluchten die het nog nooit gezien heeft."
)
links, rechts = st.columns(2)
links.metric("Trainset", f"{len(X_train):,} vluchten".replace(",", "."))
rechts.metric("Testset", f"{len(X_test):,} vluchten".replace(",", "."))
st.write("Het model krijgt deze kenmerken mee: " + ", ".join(NAMEN[k] for k in KOLOMMEN) + ".")
 
st.header("Stap 2: het model trainen")
st.write(
    "We gebruiken een random forest: een groep beslisbomen die samen een voorspelling maken. "
    "Het model rekent alleen met getallen, dus tekst zoals het vliegtuigtype hebben we omgezet naar een nummer. "
    "Lege waarden hebben we op -1 gezet."
)
model = train_model(X_train, y_train)
voorspelling = model.predict(X_test)
 
st.header("Stap 3: welke kenmerken voorspellen de vertraging?")
st.write(
    "Het random forest houdt bij hoeveel elk kenmerk helpt bij het voorspellen. "
    "Dat noemen we het belang. Samen is dat 100%."
)
belang = pd.DataFrame({"kolom": KOLOMMEN, "belang": model.feature_importances_ * 100})
belang["groep"] = belang["kolom"].map(GROEPEN)
belang["naam"] = belang["kolom"].map(NAMEN)
 
keuze = st.radio("Bekijk het belang", ["Per groep", "Per kolom"], horizontal=True)
if keuze == "Per groep":
    per_groep = belang.groupby("groep", as_index=False)["belang"].sum().sort_values("belang")
    fig = px.bar(per_groep, x="belang", y="groep", orientation="h", text_auto=".0f")
    fig.update_layout(xaxis_title="Belang (%)", yaxis_title="")
else:
    per_kolom = belang.sort_values("belang")
    fig = px.bar(per_kolom, x="belang", y="naam", color="groep", orientation="h", text_auto=".1f")
    fig.update_layout(xaxis_title="Belang (%)", yaxis_title="", height=550)
st.plotly_chart(fig)
st.caption(
    "Let op: weer bestaat uit 6 kolommen en drukte uit 1. Per groep tellen we alles op, "
    "daarom is het ook goed om per kolom te kijken."
)
 
st.header("Stap 4: hoe goed werkt het model?")
st.write(
    "We vergelijken het model met een simpele gok: voor elke vlucht de gemiddelde vertraging voorspellen. "
    "Doet het model het niet beter dan die gok, dan heeft het niks geleerd. "
    "We kijken naar de gemiddelde fout: hoeveel minuten zit de voorspelling ernaast?"
)
fout_gok = mean_absolute_error(y_test, [y_train.mean()] * len(y_test))
fout_model = mean_absolute_error(y_test, voorspelling)
 
links, rechts = st.columns(2)
links.metric("Fout als we het gemiddelde gokken", f"{fout_gok:.1f} min")
rechts.metric("Fout van ons model", f"{fout_model:.1f} min", f"{fout_model - fout_gok:.1f} min", delta_color="inverse")
 
vergelijking = pd.DataFrame({"manier": ["Gemiddelde gokken", "Ons model"], "fout": [fout_gok, fout_model]})
fig = px.bar(vergelijking, x="manier", y="fout", text_auto=".1f")
fig.update_layout(xaxis_title="", yaxis_title="Gemiddelde fout (minuten)")
st.plotly_chart(fig)
 
st.subheader("Voorspeld tegenover echt")
st.write(
    "Elke stip is een vlucht uit de test. Als het model perfect was, lag elke stip op de stippellijn. "
    "We laten 3000 vluchten zien, anders wordt de grafiek te vol."
)
stippen = pd.DataFrame({"echt": y_test.values, "voorspeld": voorspelling}).sample(3000, random_state=42)
fig = px.scatter(stippen, x="echt", y="voorspeld", opacity=0.4)
fig.add_shape(type="line", x0=-60, y0=-60, x1=180, y1=180, line=dict(dash="dash", color="gray"))
fig.update_layout(xaxis_title="Echte vertraging (minuten)", yaxis_title="Voorspelde vertraging (minuten)")
fig.update_xaxes(range=[-60, 180])
fig.update_yaxes(range=[-60, 180])
st.plotly_chart(fig)
 
st.header("Conclusie")
st.write(
    "**Wat voorspelt de vertraging?** Vooral de tijd (het uur van de dag en het jaar) en de baan. "
    "Het weer telt samen ook flink mee, met temperatuur als belangrijkste. "
    "Drukte helpt een beetje, het vliegtuigtype bijna niet."
)
st.write(
    f"**Hoe goed is het model?** Het zit er gemiddeld {fout_model:.1f} minuten naast, "
    f"tegenover {fout_gok:.1f} minuten bij gokken. Het model is dus beter dan gokken, maar niet precies. "
    "Vooral grote vertragingen schat het te laag in."
)
st.write(
    "**Waarom niet beter?** Veel oorzaken van vertraging staan niet in onze data, "
    "zoals problemen op een andere luchthaven of een technisch mankement."
)
 
 