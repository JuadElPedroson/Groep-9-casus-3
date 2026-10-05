import streamlit as st

from data import laad_airports, laad_schedule, laad_vlucht, laad_weer, vlucht_bestanden

st.title("Data inspectie")
st.write("De eerste regels van elke dataset, zodat we zien wat erin zit.")

schedule = laad_schedule()
st.subheader("Schedule Airport")
st.write(f"{schedule.shape[0]} rijen en {schedule.shape[1]} kolommen")
st.dataframe(schedule.head())

airports = laad_airports()
st.subheader("Luchthavens")
st.write(f"{airports.shape[0]} rijen en {airports.shape[1]} kolommen")
st.dataframe(airports.head())

weer = laad_weer()
st.subheader("Weer in Zurich")
st.write(f"{weer.shape[0]} rijen en {weer.shape[1]} kolommen")
st.dataframe(weer.head())

bestanden = vlucht_bestanden()
if bestanden:
    vlucht = laad_vlucht(bestanden[0])
    st.subheader("Vluchtdata (optioneel)")
    st.write(f"Voorbeeld van een van de zeven vluchten: {vlucht.shape[0]} rijen en {vlucht.shape[1]} kolommen")
    st.dataframe(vlucht.head())
