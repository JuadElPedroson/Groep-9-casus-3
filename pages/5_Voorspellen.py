import streamlit as st

from schoon import KOLOMMEN, laad_klaar, maak_train_test

st.set_page_config(page_title="Voorspellen", layout="wide")

st.title("Voorspellen")
st.write("Deelvraag 3: welke kenmerken (weer, drukte, baan, vliegtuigtype) voorspellen de vertraging, en hoe goed werkt ons model?")

# data splitsen in train en test
st.header("Stap 1: data splitsen")
df = laad_klaar()
X_train, X_test, y_train, y_test = maak_train_test(df)
st.write(
    "Eerst splitsen we de data. 80% gebruiken we om het model van te laten leren (train). "
    "De andere 20% houden we apart (test). Pas aan het eind kijken we hoe goed het model is op de test. "
    "Zo weten we dat het model ook werkt op vluchten die het nog niet gezien heeft."
)
st.write(f"Train: {len(X_train)} vluchten. Test: {len(X_test)} vluchten.")
st.write("We gebruiken deze kolommen om te voorspellen: " + ", ".join(KOLOMMEN) + ".")
st.write(
    "Conclusie: we hebben nu een train en een test. We trainen alleen op de train en gebruiken de test pas aan het eind, "
    "om eerlijk te zien hoe goed het model is."
)

st.header("Hier komt nog")
st.write(
    "Ideeen: eerst een simpele voorspelling om mee te vergelijken (altijd het gemiddelde), daarna een model. "
    "Laten zien hoe goed het model is en waar het ernaast zit. Lege waarden en tekstkolommen omzetten voor het model."
)
