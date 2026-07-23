import pandas as pd

from prospects_carte import ajouter_distance, build_carte


def _df():
    return pd.DataFrame([
        # CHAUDE proche -> sur la carte
        {"siret": "11111111100011", "denomination": "Alpha Nettoyage",
         "adresse_complete": "1 rue A 75008 Paris", "categorie_chruth": "BUREAUX",
         "domaine_chruth": "PRIVE", "effectif_label": "10 a 19", "priorite": "CHAUDE",
         "latitude": 48.87, "longitude": 2.30},
        # TIEDE proche -> sur la carte
        {"siret": "33333333300033", "denomination": "Gamma Proprete",
         "adresse_complete": "3 rue C 75010 Paris", "categorie_chruth": "BUREAUX",
         "domaine_chruth": "PRIVE", "effectif_label": "20 a 49", "priorite": "TIEDE",
         "latitude": 48.88, "longitude": 2.36},
        # FROIDE proche -> EXCLUE (priorite non activable)
        {"siret": "22222222200022", "denomination": "Beta Services",
         "adresse_complete": "2 av B 75009 Paris", "categorie_chruth": "COMMERCE",
         "domaine_chruth": "PRIVE", "effectif_label": "1 a 2", "priorite": "FROIDE",
         "latitude": 48.88, "longitude": 2.34},
        # CHAUDE lointaine (Marseille) -> EXCLUE (hors zone servable <= 50 km)
        {"siret": "44444444400044", "denomination": "Delta Sud",
         "adresse_complete": "4 quai D 13001 Marseille", "categorie_chruth": "BUREAUX",
         "domaine_chruth": "PRIVE", "effectif_label": "50 a 99", "priorite": "CHAUDE",
         "latitude": 43.30, "longitude": 5.40},
    ])


def test_carte_activables_seulement(tmp_path):
    """La carte ne montre que les prospects ACTIVABLES : priorite CHAUDE/TIEDE
    ET dans la zone servable (<= rayon). FROIDE et hors-zone sont exclus."""
    centre = (48.869893, 2.30194)
    df = ajouter_distance(_df(), centre)
    out = tmp_path / "c.html"
    build_carte(df, centre, rayon_km=50, sortie_html=out)
    h = out.read_text(encoding="utf-8")
    # couches cluster par priorite (lisibles, filtrables via LayerControl)
    assert "Prospects CHAUDE" in h
    assert "Prospects TIEDE" in h
    assert "markercluster" in h.lower()
    # FROIDE jamais sur la carte
    assert "Beta Services" not in h
    # CHAUDE hors zone (Marseille) exclue par la distance
    assert "Delta Sud" not in h
    # activables proches bien presents (CHAUDE + TIEDE)
    assert "Alpha Nettoyage" in h
    assert "Gamma Proprete" in h
    # recherche societe + acquis (itineraire + cercles)
    assert "chruth-search" in h
    assert "leaflet-routing-machine" in h
    for rk in ["5 km", "50 km"]:
        assert rk in h
