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


def test_build_carte_v2_features(tmp_path):
    centre = (48.869893, 2.30194)
    df = ajouter_distance(_df(), centre)
    out = tmp_path / "c.html"
    build_carte(df, centre, rayon_km=50, sortie_html=out)
    h = out.read_text(encoding="utf-8")
    # itineraire
    assert "leaflet-routing-machine" in h and "L.Routing" in h
    # recherche adresse (geocoder)
    assert "geocoder" in h.lower()
    # 5 cercles
    for rk in ["5 km", "10 km", "20 km", "30 km", "50 km"]:
        assert rk in h
    # societe (popup) + couche cluster par priorite + recherche societe + clustering
    assert "Alpha Nettoyage" in h
    assert "Prospects CHAUDE" in h
    assert "markercluster" in h.lower()
    assert "chruth-search" in h
