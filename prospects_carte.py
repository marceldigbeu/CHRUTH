from __future__ import annotations

import math
from pathlib import Path

import json

import folium
import pandas as pd
import requests
from folium.plugins import Geocoder, MarkerCluster

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

ADRESSE_CHRUTH = "60 rue François Ier 75008 Paris"
RAYON_KM_DEFAUT = 50
CENTRE_FALLBACK = (48.869893, 2.30194)
SORTIE_HTML = OUTPUT_DIR / "Carte_Prospects_CHRUTH.html"

# La carte ne montre que les prospects ACTIVABLES : priorite chaude/tiede ET dans la
# zone servable (<= rayon). Les FROIDE et hors-zone restent dans l'Excel.
PRIORITES_CARTE = ("CHAUDE", "TIEDE")
# Allegement : on ne cartographie que les N meilleurs (par score) parmi les activables.
# Marqueurs GeoJson individuels (triables) -> rester raisonnable pour un HTML leger.
MAX_POINTS_CARTE = 2000

_CANDIDATS_BASE = [
    OUTPUT_DIR,
    BASE_DIR,
    BASE_DIR / "CHRUTH_PROJET_ORGANISE" / "03_EXPORTS_EXCEL",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p = math.radians
    dlat, dlon = p(lat2 - lat1), p(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p(lat1)) * math.cos(p(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def geocode_adresse(adresse: str, fallback: tuple[float, float] = CENTRE_FALLBACK) -> tuple[float, float]:
    try:
        resp = requests.get(
            "https://api-adresse.data.gouv.fr/search/",
            params={"q": adresse, "limit": 1},
            timeout=15,
        )
        resp.raise_for_status()
        feat = resp.json()["features"][0]
        lon, lat = feat["geometry"]["coordinates"]
        return float(lat), float(lon)
    except Exception:
        return fallback


def ajouter_distance(df: pd.DataFrame, centre: tuple[float, float]) -> pd.DataFrame:
    df = df.copy()
    lat0, lon0 = centre
    lat = pd.to_numeric(df.get("latitude"), errors="coerce")
    lon = pd.to_numeric(df.get("longitude"), errors="coerce")

    def _d(la, lo):
        if pd.isna(la) or pd.isna(lo):
            return float("nan")
        return haversine_km(lat0, lon0, float(la), float(lo))

    df["distance_km"] = [round(_d(la, lo), 1) if not pd.isna(_d(la, lo)) else float("nan")
                         for la, lo in zip(lat, lon)]
    return df.sort_values("distance_km", na_position="last").reset_index(drop=True)


def charger_prospects() -> pd.DataFrame:
    fichiers = []
    for dossier in _CANDIDATS_BASE:
        if dossier.exists():
            fichiers.extend(dossier.glob("Base_Prospects_CHRUTH*.xlsx"))
            fichiers.extend(dossier.glob("Base_Prospects_CHRUTH*.xlsm"))
    if not fichiers:
        raise FileNotFoundError(
            "Aucun Base_Prospects_CHRUTH_France_*.xlsx trouve. Lance d'abord la pipeline Prospects."
        )
    dernier = max(fichiers, key=lambda p: p.stat().st_mtime)
    return pd.read_excel(dernier, sheet_name="Prospects")


_COULEUR_PRIORITE = {"CHAUDE": "red", "TIEDE": "orange", "FROIDE": "gray"}

_LEGENDE_HTML = """
<div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
     background: white; padding: 10px 14px; border: 1px solid #999; border-radius: 6px;
     font-family: Arial; font-size: 13px;">
  <b>Priorité</b><br>
  <span style="color:red;">●</span> CHAUDE&nbsp;
  <span style="color:orange;">●</span> TIEDE
</div>
"""


def _g(row, k: str) -> str:
    v = row.get(k)
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


def _popup_html(row) -> str:
    dist = row.get("distance_km")
    dist_txt = (f"{dist} km" if not (dist is None or (isinstance(dist, float) and pd.isna(dist)))
                else "n/a")
    lignes = [
        f"<b>{_g(row, 'denomination')}</b>",
        _g(row, "adresse_complete"),
        f"{_g(row, 'categorie_chruth')} / {_g(row, 'domaine_chruth')}",
        f"Effectif : {_g(row, 'effectif_label')}",
        f"Priorité : <b>{_g(row, 'priorite')}</b> &nbsp;|&nbsp; Distance : {dist_txt}",
    ]
    tel = _g(row, "telephone_finess") or _g(row, "telephone")
    if tel:
        lignes.append(f"Tél : {tel}")
    ca, marge = _g(row, "ca_estime_eur"), _g(row, "marge_estimee_eur")
    if ca:
        lignes.append(f"CA estimé/an : {ca} € (marge ~{marge} €)")
    site = _g(row, "site_web")
    if site:
        lignes.append(f"<a href='{site}' target='_blank'>site web</a>")
    return "<br>".join(x for x in lignes if x and not x.endswith(" / "))


RAYONS_KM = [5, 10, 20, 30, 50]


def _dessiner_cercles(carte, centre) -> None:
    rmax = max(RAYONS_KM)
    for rk in RAYONS_KM:
        fg = folium.FeatureGroup(name=f"Cercle {rk} km", show=(rk == rmax))
        folium.Circle(list(centre), radius=rk * 1000, color="#1f4e78", weight=1,
                      fill=False, tooltip=f"{rk} km").add_to(fg)
        fg.add_to(carte)


def _ajouter_cluster_priorite(carte, df: pd.DataFrame, prio: str) -> list[dict]:
    """Ajoute une couche cluster (legible : regroupe les points, s'ouvre au zoom)
    pour une priorite. Retourne la liste {nom, lat, lon} pour la recherche societe."""
    couleur = _COULEUR_PRIORITE.get(prio, "blue")
    mc = MarkerCluster(name=f"Prospects {prio} ({len(df)})", show=True)
    societes = []
    for _, row in df.iterrows():
        lat, lon = float(row["latitude"]), float(row["longitude"])
        nom = _g(row, "denomination")
        folium.CircleMarker(
            location=[lat, lon], radius=6, color="#333", weight=1,
            fill=True, fill_color=couleur, fill_opacity=0.85,
            tooltip=nom,
            popup=folium.Popup(_popup_html(row), max_width=340),
        ).add_to(mc)
        societes.append({"nom": nom, "lat": lat, "lon": lon})
    mc.add_to(carte)
    return societes


def _ajouter_recherche_societe(carte, societes: list[dict]) -> None:
    """Boîte de recherche par nom de société (fiable, maîtrisée) : suggestions +
    clic -> zoom sur la société (ce qui dé-cluster le point pour cliquer son info)."""
    data = json.dumps(societes, ensure_ascii=False)
    map_name = carte.get_name()
    html = (
        '<div id="chruth-search" style="position:fixed; top:80px; left:10px; z-index:9999;'
        ' background:white; padding:8px 10px; border:1px solid #999; border-radius:6px;'
        ' font-family:Arial; font-size:13px; box-shadow:0 1px 4px rgba(0,0,0,.3);">'
        '<b>Rechercher une société</b><br>'
        '<input id="chruth-q" placeholder="nom de société..." style="width:200px">'
        '<button id="chruth-go">🔍</button>'
        '<div id="chruth-res" style="max-height:150px; overflow:auto; margin-top:4px;"></div>'
        '</div>'
    )
    js = (
        "<script>document.addEventListener('DOMContentLoaded', function(){"
        "var SOC = __DATA__; var mapObj = __MAP__;"
        "function chercher(){"
        " var q=document.getElementById('chruth-q').value.toLowerCase().trim();"
        " var res=document.getElementById('chruth-res'); res.innerHTML='';"
        " if(q.length<2){return;}"
        " var found=SOC.filter(function(s){return (s.nom||'').toLowerCase().indexOf(q)>=0;}).slice(0,10);"
        " if(!found.length){res.textContent='Aucun résultat';return;}"
        " found.forEach(function(s){var a=document.createElement('div');a.textContent=s.nom;"
        "  a.style.cursor='pointer';a.style.padding='3px';a.style.borderBottom='1px solid #eee';"
        "  a.onclick=function(){mapObj.setView([s.lat,s.lon],17);};res.appendChild(a);});"
        "}"
        "document.getElementById('chruth-go').addEventListener('click',chercher);"
        "document.getElementById('chruth-q').addEventListener('keyup',function(e){if(e.key==='Enter')chercher();});"
        "});</script>"
    ).replace("__DATA__", data).replace("__MAP__", map_name)
    carte.get_root().html.add_child(folium.Element(html + js))


def _ajouter_routing(carte) -> None:
    """Itineraire routier entre 2 adresses (Leaflet Routing Machine + OSRM, gratuit)."""
    map_name = carte.get_name()
    css = (
        '<link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css"/>'
        '<link rel="stylesheet" href="https://unpkg.com/leaflet-control-geocoder@2.4.0/dist/Control.Geocoder.css"/>'
    )
    carte.get_root().header.add_child(folium.Element(css))
    js = f"""
<script src="https://unpkg.com/leaflet-control-geocoder@2.4.0/dist/Control.Geocoder.js"></script>
<script src="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {{
  try {{
    L.Routing.control({{
      waypoints: [],
      router: L.Routing.osrmv1({{ serviceUrl: 'https://router.project-osrm.org/route/v1' }}),
      geocoder: L.Control.Geocoder.nominatim(),
      routeWhileDragging: false,
      language: 'fr',
      showAlternatives: false,
      addWaypoints: false
    }}).addTo({map_name});
  }} catch (e) {{ console.warn('Routing non disponible:', e); }}
}});
</script>
"""
    carte.get_root().html.add_child(folium.Element(js))


def build_carte(df: pd.DataFrame, centre: tuple[float, float], rayon_km: int = RAYON_KM_DEFAUT,
                sortie_html: Path = SORTIE_HTML, max_points: int = MAX_POINTS_CARTE) -> Path:
    sortie_html = Path(sortie_html)
    sortie_html.parent.mkdir(parents=True, exist_ok=True)
    carte = folium.Map(location=list(centre), zoom_start=11, tiles="CartoDB positron")

    folium.Marker(list(centre), tooltip="CHRUTH (référence)",
                  icon=folium.Icon(color="blue", icon="home", prefix="fa")).add_to(carte)
    _dessiner_cercles(carte, centre)

    valides = df[pd.to_numeric(df["latitude"], errors="coerce").notna()
                 & pd.to_numeric(df["longitude"], errors="coerce").notna()].copy()

    # Activables : priorite CHAUDE/TIEDE ET zone servable (<= rayon).
    prio_norm = valides["priorite"].astype(str).str.upper()
    activable = prio_norm.isin(PRIORITES_CARTE)
    if "distance_km" in valides.columns:
        activable &= pd.to_numeric(valides["distance_km"], errors="coerce") <= rayon_km
    valides = valides[activable]
    prio_norm = valides["priorite"].astype(str).str.upper()

    # Allegement : ne garder que les meilleurs par score (les plus actionnables).
    if "signal_besoin" in valides.columns and not valides.empty:
        valides = valides.assign(
            _score=pd.to_numeric(valides["signal_besoin"], errors="coerce").fillna(0)
        ).sort_values("_score", ascending=False).drop(columns="_score")
        prio_norm = valides["priorite"].astype(str).str.upper()
    valides = valides.head(max_points)
    prio_norm = valides["priorite"].astype(str).str.upper()

    # Une couche CLUSTER par priorite (lisible + filtrable via le controle de couches).
    societes: list[dict] = []
    for prio in PRIORITES_CARTE:
        sous = valides[prio_norm == prio]
        if not sous.empty:
            societes.extend(_ajouter_cluster_priorite(carte, sous, prio))

    if societes:
        _ajouter_recherche_societe(carte, societes)

    Geocoder(collapsed=True, add_marker=True, position="topright").add_to(carte)
    _ajouter_routing(carte)

    folium.LayerControl(collapsed=False).add_to(carte)
    carte.get_root().html.add_child(folium.Element(_LEGENDE_HTML))
    carte.save(str(sortie_html))
    return sortie_html


def main() -> int:
    df = charger_prospects()
    centre = geocode_adresse(ADRESSE_CHRUTH)
    df = ajouter_distance(df, centre)
    chemin = build_carte(df, centre, rayon_km=RAYON_KM_DEFAUT)
    proches = int((pd.to_numeric(df["distance_km"], errors="coerce") <= RAYON_KM_DEFAUT).sum())
    print(f"Carte generee : {chemin}")
    print(f"Societes : {len(df)} total | {proches} dans {RAYON_KM_DEFAUT} km "
          f"| carte: top {MAX_POINTS_CARTE} activables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
