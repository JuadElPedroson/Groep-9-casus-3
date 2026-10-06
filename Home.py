import streamlit as st

st.set_page_config(page_title="Vluchten en vertraging", layout="wide")

st.title("Vluchten en vertraging op Zurich Airport")
st.write("Groep 9, Case 3 van de minor Data Science.")

st.write("(Deze vragen zijn voor nu even bedacht we kunnen zelf nog kiezen waar we dieper op in gaan)")

st.subheader("Hoofdvraag")
st.write("Wat bepaalt de vertraging van vluchten op Zurich Airport, en kunnen we die voorspellen?")

st.subheader("Deelvragen")
st.write("1. Hoe verandert de vertraging over de tijd (maand, uur van de dag, 2019 tegenover 2020)? Hierbij hoort een lijngrafiek.")
st.write("2. Verschilt de vertraging per bestemming? Hierbij hoort een kaart.")
st.write("3. Welke kenmerken (weer, drukte, baan, vliegtuigtype) voorspellen de vertraging, en hoe goed werkt ons model?")

st.subheader("Conclusie")
st.write("Hier komt een korte samenvatting van ons antwoord.")
st.write("Ideeen: de belangrijkste bevindingen, het antwoord op de hoofdvraag, wat de data niet kan laten zien.")

st.write("Gebruik het menu links om door het dashboard te gaan.")
