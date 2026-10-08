import streamlit as st

st.set_page_config(page_title="Vluchten en vertraging", layout="wide")

st.title("Vluchten en vertraging op Zurich Airport")
st.caption("Groep 9, Case 3, minor Data Science")

st.header("Hoofdvraag")
st.write("Wat bepaalt de vertraging van vluchten op Zurich Airport, en kunnen we die voorspellen?")
st.write(
    "We hebben de vluchten van 2019 en 2020. Vertraging zit niet als kolom in de data, "
    "dus die rekenen we zelf uit."
)

st.header("Deelvragen")
st.markdown(
    "**1. Hoe verandert de vertraging over de tijd, en hangt dat samen met hoe druk het is op het vliegveld?**\n\n"
    "Drukte en vertraging lopen vooral in 2019 samen. In 2020 niet. (pagina Drukte op het vliegveld)\n\n"
    "**2. Verschilt de vertraging per bestemming?**\n\n"
    "Ja, maar de bestemming verklaart weinig van de vertraging. (pagina Bestemmingen)\n\n"
    "**3. Welke kenmerken voorspellen de vertraging, en hoe goed werkt ons model?**\n\n"
    "Vooral het tijdstip en de baan. Het model is beter dan gokken, maar niet precies. (pagina Voorspellen)"
)

st.header("Ons antwoord")
st.write(
    "De vertraging hangt vooral samen met het tijdstip en de baan. Weer en drukte helpen een beetje, "
    "de bestemming weinig. Een model kan de vertraging deels voorspellen. Veel oorzaken staan niet in onze data, "
    "zoals een technisch mankement of een probleem op een andere luchthaven."
)
