import math

import pandas as pd
import pytest

import prospects_carte
from prospects_carte import ajouter_distance, geocode_adresse, haversine_km


def test_haversine_known_distance():
    d = haversine_km(45.7578, 4.8320, 45.7667, 4.8795)  # Lyon -> Villeurbanne
    assert 3.0 < d < 5.0
    assert haversine_km(48.0, 2.0, 48.0, 2.0) == pytest.approx(0.0, abs=1e-6)


def test_ajouter_distance_sorts_and_handles_bad_coords():
    df = pd.DataFrame([
        {"denomination": "Loin", "latitude": 43.6, "longitude": 1.44},     # Toulouse
        {"denomination": "Pres", "latitude": 48.87, "longitude": 2.30},    # Paris
        {"denomination": "Sans", "latitude": None, "longitude": None},
    ])
    out = ajouter_distance(df, (48.869893, 2.30194))
    assert "distance_km" in out.columns
    assert list(out["denomination"])[:2] == ["Pres", "Loin"]  # trie par proximite
    assert math.isnan(out[out["denomination"] == "Sans"]["distance_km"].iloc[0])


def test_geocode_fallback_when_network_fails(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no network")
    monkeypatch.setattr(prospects_carte.requests, "get", boom)
    assert geocode_adresse("adresse bidon", fallback=(1.0, 2.0)) == (1.0, 2.0)
