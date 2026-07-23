import pandas as pd

from prospects_carte import ajouter_distance, build_carte


def _df():
    return pd.DataFrame([
        {"denomination": "Alpha Nettoyage", "adresse_complete": "1 rue A 75008 Paris",
         "categorie_chruth": "BUREAUX", "domaine_chruth": "PRIVE", "effectif_label": "10 a 19",
         "priorite": "CHAUDE", "latitude": 48.87, "longitude": 2.30},
        {"denomination": "Beta Services", "adresse_complete": "Lyon",
         "categorie_chruth": "COMMERCE", "domaine_chruth": "PRIVE", "effectif_label": "1 a 2",
         "priorite": "FROIDE", "latitude": 45.76, "longitude": 4.83},
    ])


def test_build_carte_creates_html(tmp_path):
    centre = (48.869893, 2.30194)
    df = ajouter_distance(_df(), centre)
    out = tmp_path / "carte.html"
    chemin = build_carte(df, centre, rayon_km=50, sortie_html=out)
    assert chemin.exists()
    html = chemin.read_text(encoding="utf-8")
    assert "leaflet" in html.lower()                 # folium = leaflet
    assert "Alpha Nettoyage" in html                 # prospect activable (popup)
    assert "markercluster" in html.lower()           # clustering -> lisible
    assert "Prospects CHAUDE" in html                # couche cluster par priorite
    assert "Beta Services" not in html               # FROIDE exclue
    assert "chruth-search" in html                   # recherche societe (fiable)
