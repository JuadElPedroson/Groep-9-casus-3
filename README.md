# Groep 9 - Case 3: vluchten en vertraging

Streamlit-dashboard voor Case 3 van de minor Data Science. We gebruiken het vluchtrooster van Zurich Airport, luchthavens van Kaggle en weerdata van Meteostat.

## Data

Alle data staat in de map data:

- schedule_airport.csv.gz: het vluchtrooster van Brightspace
- airports: de luchthavens van Kaggle
- weer_zurich.csv.gz: het weer van Meteostat (station 06670). Als dit bestand ontbreekt, wordt het bij het opstarten gedownload
- flightdata: zeven vluchten van Brightspace (optioneel)

De luchthavens staan al in de repo. Alleen als de map data/airports ontbreekt is een Kaggle-token nodig.

## Zelf draaien

```
git clone https://github.com/JuadElPedroson/Groep-9-casus-3.git
cd Groep-9-casus-3
pip install -r requirements.txt
streamlit run Home.py
```
