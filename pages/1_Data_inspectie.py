import streamlit as st

from data import laad_airports, laad_schedule, laad_vlucht, laad_weer, vlucht_bestanden

st.title("Data inspectie")
st.write("De eerste regels van elke dataset, zodat we zien wat erin zit.")
st.write("Let op: deze pagina halen we later weg.")

schedule = laad_schedule()
st.subheader("Schedule Airport")
st.write(f"{schedule.shape[0]} rijen en {schedule.shape[1]} kolommen")
st.dataframe(schedule.head())
st.write("Je ziet per vlucht de datum, geplande en echte tijd, baan, vliegtuigtype en bestemming. Handig voor vraag 1, 2 en 4: hieruit rekenen we de vertraging uit.")

airports = laad_airports()
st.subheader("Luchthavens")
st.write(f"{airports.shape[0]} rijen en {airports.shape[1]} kolommen")
st.dataframe(airports.head())
st.write("Je ziet per luchthaven de code en de locatie. Handig voor vraag 2: hiermee zetten we de bestemmingen op de kaart.")

weer = laad_weer()
st.subheader("Weer in Zurich")
st.write(f"{weer.shape[0]} rijen en {weer.shape[1]} kolommen")
st.dataframe(weer.head())
st.write("Je ziet per dag de temperatuur, neerslag en wind. Handig voor vraag 3: we koppelen dit op datum aan de vluchten.")

bestanden = vlucht_bestanden()
if bestanden:
    vlucht = laad_vlucht(bestanden[0])
    st.subheader("Vluchtdata (optioneel)")
    st.write(f"Voorbeeld van een van de zeven vluchten: {vlucht.shape[0]} rijen en {vlucht.shape[1]} kolommen")
    st.dataframe(vlucht.head())
    st.write("Je ziet per moment de plek, hoogte en snelheid van een vlucht. Misschien handig voor een extra kaart of grafiek van een vlucht.")
