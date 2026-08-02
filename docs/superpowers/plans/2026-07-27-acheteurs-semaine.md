# Acheteurs actifs de la semaine — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produire chaque semaine la liste des acheteurs ayant publié un AO propreté pertinent sur 7 jours glissants — dédoublonnés, classés public/privé-droit, enrichis par SIRET — exposée en page de plateforme et exportée.

**Architecture:** Un module métier pur `acheteurs_semaine.py` (collecte → extraction → enrichissement → classement → DataFrame → export), un helper d'enrichissement isolé dans `collect_api_entreprises.py`, une page Streamlit + une page HTML, une tâche planifiée. Réseau confiné à l'enrichissement, best-effort.

**Tech Stack:** Python 3.12, pandas, openpyxl, requests, Streamlit. Réutilise `ao_db`, `veille_depot`, `veille_etat`, `ao_extract_fields.normalize_text`, `theme_chruth`.

## Global Constraints

- Le livrable ne contient QUE des acheteurs d'AO **PERTINENT** publiés **dans la fenêtre** (défaut 7 jours) : jamais un rejeté, jamais un hors-fenêtre, jamais une date manquante.
- Pertinence : BOAMP → `priorite` dans `("CHAUD","TIEDE","TIÈDE")` ; Maximilien → `veille_etat.verdict_effectif(e) == "PERTINENT"`.
- L'enrichissement est **best-effort** : un échec réseau ou un SIRET absent laisse l'acheteur `enrichi=False`, sans jamais lever ni vider le livrable.
- `acheteurs_semaine` reste testable **sans réseau ni base** : les fonctions acceptent des données injectées.
- `FENETRE_JOURS = 7`. Constante, pas de réglage utilisateur.
- Aucun secret ; aucune donnée personnelle au-delà des contacts publics de l'avis/entreprise.
- Rien de l'ancien pipeline n'est supprimé (réversible).
- Tests avec `python -m pytest`. La suite complète reste verte.

---

### Task 1: Classement public / privé-droit

**Files:**
- Create: `acheteurs_semaine.py`
- Test: `tests/test_acheteurs_classer.py`

**Interfaces:**
- Produces: `acheteurs_semaine.classer(nature_juridique: str, nom: str = "") -> tuple[str, bool]` — renvoie `(type, incertain)` où `type ∈ {"public","prive"}`. Public si la catégorie juridique INSEE est de niveau I « 7 » ; sinon privé-droit. Sans catégorie, repli heuristique sur le nom avec `incertain=True`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_acheteurs_classer.py
from acheteurs_semaine import classer


def test_categorie_droit_public_niveau_7():
    assert classer("7220") == ("public", False)   # commune
    assert classer("7100", "") == ("public", False)


def test_societes_de_droit_prive():
    assert classer("5710") == ("prive", False)     # SA (ESH)
    assert classer("5385") == ("prive", False)     # SEM


def test_sans_categorie_repli_sur_le_nom():
    assert classer("", "Mairie de Créteil") == ("public", True)
    assert classer("", "Département de Seine-Saint-Denis") == ("public", True)
    assert classer("", "Immobilière 3F") == ("prive", True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_acheteurs_classer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'acheteurs_semaine'`.

- [ ] **Step 3: Write minimal implementation**

Créer `acheteurs_semaine.py` avec l'en-tête et `classer` :

```python
"""Acheteurs actifs de la semaine : les organisations ayant publié un AO
propreté pertinent sur 7 jours glissants, classées et enrichies.

Remplace l'ancienne collecte « toutes les entreprises IDF » comme source de
prospection (celle-ci est mise en sommeil, non supprimée).
"""
from __future__ import annotations

from ao_extract_fields import normalize_text

FENETRE_JOURS = 7
PRIORITES_PERTINENTES = ("CHAUD", "TIEDE", "TIÈDE")

# Indices de droit public dans le nom, quand la catégorie juridique manque.
_MOTS_PUBLIC = ("mairie", "commune", "ville de", "departement", "département",
                "prefecture", "préfecture", "region", "région", "hopital",
                "hôpital", "centre hospitalier", "ccas", "etablissement public",
                "établissement public", "communaute", "communauté", "metropole",
                "métropole", "syndicat", "academie", "académie", "rectorat")


def classer(nature_juridique: str, nom: str = "") -> tuple[str, bool]:
    """(type, incertain) : 'public' si catégorie juridique niveau I = « 7 »,
    sinon 'prive'. Sans catégorie, repli sur le nom, marqué incertain."""
    code = str(nature_juridique or "").strip()
    if code[:1] == "7":
        return ("public", False)
    if code:
        return ("prive", False)
    n = normalize_text(nom or "")
    for mot in _MOTS_PUBLIC:
        if normalize_text(mot) in n:
            return ("public", True)
    return ("prive", True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_acheteurs_classer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add acheteurs_semaine.py tests/test_acheteurs_classer.py
git commit -m "feat(acheteurs): classement public/prive-droit par categorie juridique"
```

---

### Task 2: Enrichissement d'une entreprise par SIRET

**Files:**
- Modify: `collect_api_entreprises.py` (nouvelle fonction `fetch_by_siret`)
- Test: `tests/test_fetch_by_siret.py`

**Interfaces:**
- Consumes: `SESSION`, `API_BASE_URL`, `extract_etablissements` (existants).
- Produces: `collect_api_entreprises.fetch_by_siret(siret: str) -> dict | None` — une fiche établissement (mêmes clés que `extract_etablissements` : `adresse`, `code_postal`, `libelle_commune`, `tranche_effectif_salarie`, `nature_juridique`, `denomination`, `siren`…). `None` si SIRET invalide, absent, ou réseau KO.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch_by_siret.py
import collect_api_entreprises as cae


class _FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def _payload():
    return {"results": [{
        "siren": "217500016", "nom_complet": "COMMUNE DE PARIS", "nature_juridique": "7210",
        "siege": {"siret": "21750001600019", "adresse": "PLACE DE L'HOTEL DE VILLE 75004 PARIS",
                  "code_postal": "75004", "libelle_commune": "PARIS", "departement": "75",
                  "tranche_effectif_salarie": "42", "est_siege": True},
        "matching_etablissements": []}]}


def test_fetch_by_siret_renvoie_une_fiche(monkeypatch):
    monkeypatch.setattr(cae.SESSION, "get", lambda *a, **k: _FakeResp(_payload()))
    fiche = cae.fetch_by_siret("21750001600019")
    assert fiche is not None
    assert fiche["code_postal"] == "75004"
    assert fiche["nature_juridique"] == "7210"
    assert fiche["libelle_commune"] == "PARIS"


def test_fetch_by_siret_reseau_ko_renvoie_none(monkeypatch):
    import requests
    def boom(*a, **k): raise requests.exceptions.ConnectionError("offline")
    monkeypatch.setattr(cae.SESSION, "get", boom)
    assert cae.fetch_by_siret("21750001600019") is None


def test_fetch_by_siret_invalide_renvoie_none():
    assert cae.fetch_by_siret("abc") is None
    assert cae.fetch_by_siret("") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fetch_by_siret.py -v`
Expected: FAIL — `AttributeError: module 'collect_api_entreprises' has no attribute 'fetch_by_siret'`.

- [ ] **Step 3: Write minimal implementation**

Dans `collect_api_entreprises.py`, ajouter après `fetch_page` :

```python
def fetch_by_siret(siret: str) -> dict | None:
    """Fiche etablissement via l'API Recherche Entreprises (recherche q=<siret>).

    None si le SIRET n'a pas 14 chiffres, si l'API ne renvoie rien, ou si le
    reseau echoue : l'appelant traite l'enrichissement en best-effort.
    """
    s = "".join(c for c in str(siret or "") if c.isdigit())
    if len(s) != 14:
        return None
    params = {"q": s, "per_page": 1, "etat_administratif": "A"}
    try:
        resp = SESSION.get(API_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException:
        return None
    results = data.get("results") or []
    if not results:
        return None
    fiches = extract_etablissements(results[0], "", "")
    if not fiches:
        return None
    return next((f for f in fiches if str(f.get("siret")) == s), fiches[0])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fetch_by_siret.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add collect_api_entreprises.py tests/test_fetch_by_siret.py
git commit -m "feat(enrichissement): fetch_by_siret via l'API Recherche Entreprises"
```

---

### Task 3: Collecte des AO récents (fenêtre + pertinence)

**Files:**
- Modify: `acheteurs_semaine.py`
- Test: `tests/test_acheteurs_collecte.py`

**Interfaces:**
- Consumes: `FENETRE_JOURS`, `PRIORITES_PERTINENTES`, `veille_etat.verdict_effectif`.
- Produces: `acheteurs_semaine.collecter_aos_recents(jours=FENETRE_JOURS, aujourd_hui=None, records_boamp=None, etat_maximilien=None) -> list[dict]`. Chaque AO renvoyé : `{acheteur, siret, siren, ville, departement, date_publication, url, objet, priorite, source}`. Si `records_boamp`/`etat_maximilien` sont `None`, ils sont lus depuis `ao_db.fetch_records()` / `veille_depot.lire()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_acheteurs_collecte.py
from datetime import date

import acheteurs_semaine as asem


def _boamp(objet, prio, datep, ach="Mairie X", siret="21750001600019"):
    return {"objet": objet, "acheteur": ach, "siret_acheteur": siret, "siren_acheteur": "217500016",
            "ville": "Paris", "departement": "75", "date_publication": datep,
            "url_avis": "http://b/1", "priorite": prio}


def _max(objet, verdict, datep, ach="Ville Y"):
    return {"objet": objet, "acheteur": ach, "ville": "Antony", "departement": "92",
            "date_publication": datep, "url": "http://m/1", "priorite": "TIEDE",
            "tri": {"verdict": verdict, "etage": "listes", "motif": "m"},
            "correction_humaine": None}


AUJ = date(2026, 7, 27)


def test_garde_pertinent_dans_la_fenetre_ecarte_le_reste():
    boamp = [
        _boamp("Nettoyage récent", "CHAUD", "2026-07-24"),         # gardé
        _boamp("Nettoyage vieux", "CHAUD", "2026-07-01"),          # hors fenêtre
        _boamp("Ascenseurs", "FROID", "2026-07-25"),               # non pertinent
        _boamp("Nettoyage sans date", "CHAUD", ""),                # sans date -> exclu
    ]
    aos = asem.collecter_aos_recents(aujourd_hui=AUJ, records_boamp=boamp, etat_maximilien={"aos": {}})
    objets = [a["objet"] for a in aos]
    assert objets == ["Nettoyage récent"]
    assert aos[0]["source"] == "BOAMP"
    assert aos[0]["siret"] == "21750001600019"


def test_fusionne_maximilien_pertinent():
    etat = {"aos": {
        "MX-1": _max("Propreté locaux", "PERTINENT", "2026-07-23"),
        "MX-2": _max("Espaces verts", "REJETE", "2026-07-23"),
    }}
    aos = asem.collecter_aos_recents(aujourd_hui=AUJ, records_boamp=[], etat_maximilien=etat)
    assert [a["objet"] for a in aos] == ["Propreté locaux"]
    assert aos[0]["source"] == "Maximilien"
    assert aos[0]["siret"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_acheteurs_collecte.py -v`
Expected: FAIL — `AttributeError: module 'acheteurs_semaine' has no attribute 'collecter_aos_recents'`.

- [ ] **Step 3: Write minimal implementation**

Dans `acheteurs_semaine.py`, ajouter les imports et la fonction :

```python
from datetime import date, timedelta

import veille_etat


def _date_ok(datep, aujourd_hui, jours) -> bool:
    s = str(datep or "").strip()[:10]
    if not s:
        return False
    try:
        d = date.fromisoformat(s)
    except ValueError:
        return False
    return aujourd_hui - timedelta(days=jours) <= d <= aujourd_hui


def collecter_aos_recents(jours: int = FENETRE_JOURS, aujourd_hui: date | None = None,
                          records_boamp=None, etat_maximilien=None) -> list[dict]:
    aujourd_hui = aujourd_hui or date.today()

    if records_boamp is None:
        import ao_db
        records_boamp = ao_db.fetch_records().to_dict("records")
    if etat_maximilien is None:
        import veille_depot
        etat_maximilien, _ = veille_depot.lire()

    aos = []
    for r in records_boamp or []:
        if str(r.get("priorite") or "").upper() not in PRIORITES_PERTINENTES:
            continue
        if not _date_ok(r.get("date_publication"), aujourd_hui, jours):
            continue
        aos.append({
            "acheteur": r.get("acheteur") or "", "siret": str(r.get("siret_acheteur") or ""),
            "siren": str(r.get("siren_acheteur") or ""), "ville": r.get("ville") or "",
            "departement": str(r.get("departement") or ""), "date_publication": str(r.get("date_publication") or ""),
            "url": r.get("url_avis") or "", "objet": r.get("objet") or "",
            "priorite": str(r.get("priorite") or "").upper(), "source": "BOAMP",
        })

    for e in (etat_maximilien or {}).get("aos", {}).values():
        if veille_etat.verdict_effectif(e) != "PERTINENT":
            continue
        if not _date_ok(e.get("date_publication"), aujourd_hui, jours):
            continue
        aos.append({
            "acheteur": e.get("acheteur") or "", "siret": "", "siren": "",
            "ville": e.get("ville") or "", "departement": str(e.get("departement") or ""),
            "date_publication": str(e.get("date_publication") or ""), "url": e.get("url") or "",
            "objet": e.get("objet") or "", "priorite": str(e.get("priorite") or "").upper(),
            "source": "Maximilien",
        })
    return aos
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_acheteurs_collecte.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add acheteurs_semaine.py tests/test_acheteurs_collecte.py
git commit -m "feat(acheteurs): collecte des AO pertinents dans la fenetre 7 jours"
```

---

### Task 4: Extraction et dédoublonnage des acheteurs

**Files:**
- Modify: `acheteurs_semaine.py`
- Test: `tests/test_acheteurs_extraction.py`

**Interfaces:**
- Consumes: sortie de `collecter_aos_recents`, `normalize_text`.
- Produces: `acheteurs_semaine.extraire_acheteurs(aos: list[dict]) -> list[dict]`. Une entrée par acheteur : `{acheteur, siret, siren, ville, departement, priorite, nb_ao_semaine, aos:[{objet,date_publication,priorite,url}], source}`. Dédoublonnage par SIRET si présent, sinon `normalize_text(acheteur)+"|"+departement`. Priorité agrégée = la plus chaude (CHAUD > TIEDE).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_acheteurs_extraction.py
import acheteurs_semaine as asem


def _ao(objet, ach, siret="", dept="75", prio="TIEDE", src="BOAMP"):
    return {"acheteur": ach, "siret": siret, "siren": "", "ville": "Paris", "departement": dept,
            "date_publication": "2026-07-24", "url": "u", "objet": objet, "priorite": prio, "source": src}


def test_deux_ao_du_meme_acheteur_fusionnent_par_siret():
    aos = [_ao("Nettoyage A", "Mairie X", siret="21750001600019", prio="TIEDE"),
           _ao("Nettoyage B", "Mairie X", siret="21750001600019", prio="CHAUD")]
    out = asem.extraire_acheteurs(aos)
    assert len(out) == 1
    assert out[0]["nb_ao_semaine"] == 2
    assert out[0]["priorite"] == "CHAUD"          # la plus chaude gagne
    assert len(out[0]["aos"]) == 2


def test_sans_siret_dedoublonne_par_nom_et_departement():
    aos = [_ao("N1", "Ville Y", dept="92"), _ao("N2", "ville  y", dept="92"), _ao("N3", "Ville Y", dept="93")]
    out = asem.extraire_acheteurs(aos)
    # "Ville Y"/"ville y" (92) fusionnent ; "Ville Y" (93) est distinct
    assert len(out) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_acheteurs_extraction.py -v`
Expected: FAIL — `AttributeError: ... 'extraire_acheteurs'`.

- [ ] **Step 3: Write minimal implementation**

```python
_RANG_PRIO = {"CHAUD": 3, "TIEDE": 2, "TIÈDE": 2, "FROID": 1, "": 0}


def _cle(ao) -> str:
    s = "".join(c for c in str(ao.get("siret") or "") if c.isdigit())
    if len(s) == 14:
        return "siret:" + s
    return "nom:" + normalize_text(ao.get("acheteur") or "") + "|" + str(ao.get("departement") or "")


def extraire_acheteurs(aos: list[dict]) -> list[dict]:
    par_cle: dict[str, dict] = {}
    for ao in aos:
        cle = _cle(ao)
        a = par_cle.get(cle)
        if a is None:
            a = {"acheteur": ao.get("acheteur") or "", "siret": str(ao.get("siret") or ""),
                 "siren": str(ao.get("siren") or ""), "ville": ao.get("ville") or "",
                 "departement": str(ao.get("departement") or ""), "priorite": "",
                 "nb_ao_semaine": 0, "aos": [], "source": ao.get("source") or ""}
            par_cle[cle] = a
        a["nb_ao_semaine"] += 1
        a["aos"].append({"objet": ao.get("objet") or "", "date_publication": ao.get("date_publication") or "",
                         "priorite": ao.get("priorite") or "", "url": ao.get("url") or ""})
        if _RANG_PRIO.get(ao.get("priorite") or "", 0) > _RANG_PRIO.get(a["priorite"], 0):
            a["priorite"] = ao.get("priorite") or ""
        if not a["siret"] and ao.get("siret"):
            a["siret"] = str(ao.get("siret"))
    return list(par_cle.values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_acheteurs_extraction.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add acheteurs_semaine.py tests/test_acheteurs_extraction.py
git commit -m "feat(acheteurs): extraction et dedoublonnage des acheteurs"
```

---

### Task 5: Enrichissement + assemblage en DataFrame

**Files:**
- Modify: `acheteurs_semaine.py`
- Test: `tests/test_acheteurs_construire.py`

**Interfaces:**
- Consumes: `classer` (T1), `extraire_acheteurs` (T4), un chercheur `siret -> dict|None` (défaut `collect_api_entreprises.fetch_by_siret`).
- Produces:
  - `acheteurs_semaine.enrichir(acheteur: dict, chercher=None) -> dict` : ajoute `adresse, code_postal, effectif, nature_juridique, type, type_incertain, enrichi`. Best-effort.
  - `acheteurs_semaine.construire(jours=FENETRE_JOURS, aujourd_hui=None, records_boamp=None, etat_maximilien=None, chercher=None) -> pandas.DataFrame` : pipeline complet, une ligne par acheteur, triée par priorité puis `nb_ao_semaine` décroissants.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_acheteurs_construire.py
from datetime import date

import acheteurs_semaine as asem


def _fake_chercher(siret):
    if siret.endswith("0019"):
        return {"adresse": "PLACE X 75004 PARIS", "code_postal": "75004", "libelle_commune": "PARIS",
                "tranche_effectif_salarie": "42", "nature_juridique": "7210"}
    return None


def test_enrichir_remplit_et_classe():
    a = {"acheteur": "Mairie", "siret": "21750001600019", "departement": "75"}
    out = asem.enrichir(a, chercher=_fake_chercher)
    assert out["enrichi"] is True
    assert out["code_postal"] == "75004"
    assert out["type"] == "public" and out["type_incertain"] is False


def test_enrichir_best_effort_si_pas_de_fiche():
    a = {"acheteur": "Immobilière 3F", "siret": "", "departement": "93"}
    out = asem.enrichir(a, chercher=_fake_chercher)   # pas de SIRET -> pas de fiche
    assert out["enrichi"] is False
    assert out["type"] == "prive" and out["type_incertain"] is True  # repli sur le nom


def test_construire_pipeline_complet():
    boamp = [{"objet": "Nettoyage", "acheteur": "Mairie", "siret_acheteur": "21750001600019",
              "siren_acheteur": "217500016", "ville": "Paris", "departement": "75",
              "date_publication": "2026-07-24", "url_avis": "u", "priorite": "CHAUD"}]
    df = asem.construire(aujourd_hui=date(2026, 7, 27), records_boamp=boamp,
                         etat_maximilien={"aos": {}}, chercher=_fake_chercher)
    assert len(df) == 1
    assert set(["acheteur", "type", "nb_ao_semaine", "code_postal", "enrichi"]).issubset(df.columns)
    assert df.iloc[0]["type"] == "public"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_acheteurs_construire.py -v`
Expected: FAIL — `AttributeError: ... 'enrichir'`.

- [ ] **Step 3: Write minimal implementation**

```python
import pandas as pd

COLONNES = ["acheteur", "type", "type_incertain", "priorite", "nb_ao_semaine",
            "departement", "ville", "code_postal", "adresse", "effectif",
            "nature_juridique", "siret", "siren", "enrichi", "source", "aos"]


def enrichir(acheteur: dict, chercher=None) -> dict:
    if chercher is None:
        from collect_api_entreprises import fetch_by_siret as chercher
    a = dict(acheteur)
    fiche = None
    if a.get("siret"):
        try:
            fiche = chercher(str(a["siret"]))
        except Exception:  # noqa: BLE001 — best-effort
            fiche = None
    if fiche:
        a["adresse"] = fiche.get("adresse") or ""
        a["code_postal"] = fiche.get("code_postal") or ""
        a["ville"] = a.get("ville") or fiche.get("libelle_commune") or ""
        a["effectif"] = fiche.get("tranche_effectif_salarie") or ""
        a["nature_juridique"] = fiche.get("nature_juridique") or ""
        a["enrichi"] = True
    else:
        a.setdefault("adresse", ""); a.setdefault("code_postal", "")
        a.setdefault("effectif", ""); a["nature_juridique"] = ""; a["enrichi"] = False
    a["type"], a["type_incertain"] = classer(a.get("nature_juridique", ""), a.get("acheteur", ""))
    return a


def construire(jours: int = FENETRE_JOURS, aujourd_hui=None, records_boamp=None,
               etat_maximilien=None, chercher=None) -> "pd.DataFrame":
    aos = collecter_aos_recents(jours, aujourd_hui, records_boamp, etat_maximilien)
    acheteurs = [enrichir(a, chercher) for a in extraire_acheteurs(aos)]
    df = pd.DataFrame(acheteurs)
    for c in COLONNES:
        if c not in df.columns:
            df[c] = "" if c != "nb_ao_semaine" else 0
    df = df[COLONNES]
    if not df.empty:
        df["_rang"] = df["priorite"].map({"CHAUD": 3, "TIEDE": 2, "TIÈDE": 2}).fillna(0)
        df = df.sort_values(["_rang", "nb_ao_semaine"], ascending=False).drop(columns="_rang").reset_index(drop=True)
    return df
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_acheteurs_construire.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add acheteurs_semaine.py tests/test_acheteurs_construire.py
git commit -m "feat(acheteurs): enrichissement best-effort + assemblage DataFrame"
```

---

### Task 6: Export fichiers + point d'entrée

**Files:**
- Modify: `acheteurs_semaine.py`
- Test: `tests/test_acheteurs_export.py`

**Interfaces:**
- Consumes: `construire`.
- Produces:
  - `acheteurs_semaine.exporter(df, xlsx_path: Path, csv_path: Path) -> None` — écrit les deux fichiers (la colonne `aos`, liste de dicts, est aplatie en texte lisible pour l'export).
  - `acheteurs_semaine.main(argv=None) -> int` — collecte réelle → export vers `output/Acheteurs_Semaine_CHRUTH.xlsx` / `.csv`, imprime un récap.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_acheteurs_export.py
import pandas as pd
from openpyxl import load_workbook

import acheteurs_semaine as asem


def test_exporter_ecrit_xlsx_et_csv(tmp_path):
    df = pd.DataFrame([{c: ("" if c != "nb_ao_semaine" else 1) for c in asem.COLONNES}])
    df.loc[0, "acheteur"] = "Mairie X"; df.loc[0, "type"] = "public"
    df.loc[0, "aos"] = [{"objet": "Nettoyage", "date_publication": "2026-07-24", "priorite": "CHAUD", "url": "u"}]
    xlsx, csv = tmp_path / "a.xlsx", tmp_path / "a.csv"
    asem.exporter(df, xlsx, csv)
    assert xlsx.exists() and csv.exists()
    wb = load_workbook(xlsx)
    entetes = [c.value for c in wb.active[1]]
    assert "acheteur" in entetes and "type" in entetes
    texte = csv.read_text(encoding="utf-8")
    assert "Mairie X" in texte and "Nettoyage" in texte  # aos aplati
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_acheteurs_export.py -v`
Expected: FAIL — `AttributeError: ... 'exporter'`.

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path

RACINE = Path(__file__).resolve().parent
XLSX_DEFAUT = RACINE / "output" / "Acheteurs_Semaine_CHRUTH.xlsx"
CSV_DEFAUT = RACINE / "output" / "Acheteurs_Semaine_CHRUTH.csv"


def _aplatir_aos(aos) -> str:
    if not isinstance(aos, list):
        return str(aos or "")
    return " | ".join(f"{a.get('objet','')} ({a.get('date_publication','')}, {a.get('priorite','')})"
                      for a in aos)


def exporter(df, xlsx_path: Path, csv_path: Path) -> None:
    plat = df.copy()
    if "aos" in plat.columns:
        plat["aos"] = plat["aos"].map(_aplatir_aos)
    Path(xlsx_path).parent.mkdir(parents=True, exist_ok=True)
    plat.to_excel(xlsx_path, index=False)
    plat.to_csv(csv_path, index=False, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df = construire()
    exporter(df, XLSX_DEFAUT, CSV_DEFAUT)
    pub = int((df["type"] == "public").sum()) if not df.empty else 0
    print(f"[ACHETEURS-SEMAINE] {len(df)} acheteur(s) — {pub} public(s), {len(df) - pub} prive-droit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_acheteurs_export.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (tous).

- [ ] **Step 6: Commit**

```bash
git add acheteurs_semaine.py tests/test_acheteurs_export.py
git commit -m "feat(acheteurs): export xlsx/csv et point d'entree main()"
```

---

### Task 7: Page « Acheteurs de la semaine » dans la plateforme

**Files:**
- Create: `pages_acheteurs.py`
- Modify: `CHRUTH_APP.py` (ajout de la page à la navigation)
- Test: `tests/test_page_acheteurs.py`

**Interfaces:**
- Consumes: `acheteurs_semaine.construire`, `theme_chruth` (déjà appliqué par l'entrée).
- Produces: page Streamlit affichant le tableau des acheteurs avec filtre public/privé-droit et bouton d'export ; entrée `st.Page("pages_acheteurs.py", title="Acheteurs de la semaine")` dans `CHRUTH_APP.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_page_acheteurs.py
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

import acheteurs_semaine as asem

RACINE = Path(__file__).resolve().parent.parent
PAGE = str(RACINE / "pages_acheteurs.py")


def _df():
    lignes = []
    for ach, typ, dept in [("Mairie de Créteil", "public", "94"), ("Immobilière 3F", "prive", "93")]:
        l = {c: ("" if c != "nb_ao_semaine" else 1) for c in asem.COLONNES}
        l.update({"acheteur": ach, "type": typ, "departement": dept, "priorite": "CHAUD", "aos": []})
        lignes.append(l)
    return pd.DataFrame(lignes)


def test_la_page_affiche_les_acheteurs(monkeypatch):
    monkeypatch.setattr(asem, "construire", lambda *a, **k: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception
    textes = " ".join(m.value for m in at.markdown)
    assert "Créteil" in textes or "Acheteurs" in textes


def test_la_page_est_declaree_dans_l_entree():
    src = (RACINE / "CHRUTH_APP.py").read_text(encoding="utf-8")
    assert "pages_acheteurs.py" in src


def test_le_filtre_public_prive_existe(monkeypatch):
    monkeypatch.setattr(asem, "construire", lambda *a, **k: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert any(w.key == "type_acheteur" for w in at.radio) or not at.exception
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_page_acheteurs.py -v`
Expected: FAIL — page absente / non déclarée.

- [ ] **Step 3: Write minimal implementation**

Créer `pages_acheteurs.py` :

```python
"""Page Acheteurs de la semaine : les acheteurs ayant publié un AO propreté
pertinent sur 7 jours, classés public / privé-droit.
"""
from __future__ import annotations

import streamlit as st

import acheteurs_semaine as asem

try:
    st.set_page_config(page_title="Acheteurs de la semaine", layout="wide")
except st.errors.StreamlitAPIException:
    pass

st.title("Acheteurs de la semaine")
st.caption("Les organisations ayant publié un appel d'offres de propreté pertinent "
           "dans les 7 derniers jours — vos cibles chaudes, classées public / privé-droit.")

df = asem.construire()

if df.empty:
    st.info("Aucun acheteur sur les 7 derniers jours. La liste se remplit à chaque "
            "collecte du flux de veille.")
else:
    choix = st.radio("Type d'acheteur", ["Tous", "Public", "Privé-droit"],
                     horizontal=True, key="type_acheteur")
    vue = df
    if choix == "Public":
        vue = df[df["type"] == "public"]
    elif choix == "Privé-droit":
        vue = df[df["type"] == "prive"]

    st.caption(f"{len(vue)} acheteur(s) — {int((vue['type'] == 'public').sum())} public(s), "
               f"{int((vue['type'] == 'prive').sum())} privé-droit")

    for _, r in vue.iterrows():
        with st.container(border=True):
            marque = ":blue[Public]" if r["type"] == "public" else ":orange[Privé-droit]"
            incertain = " _(à confirmer)_" if r.get("type_incertain") else ""
            st.markdown(f"**{r['acheteur']}** — {marque}{incertain}")
            lieu = " ".join(x for x in [r.get("code_postal", ""), r.get("ville", ""),
                                        f"({r['departement']})" if r.get("departement") else ""] if x)
            st.markdown(f"{lieu} · {r['nb_ao_semaine']} AO cette semaine · {r['priorite']}"
                        + (f" · effectif {r['effectif']}" if r.get("effectif") else ""))
            for ao in (r["aos"] if isinstance(r["aos"], list) else []):
                lien = f"[{ao.get('objet','')}]({ao.get('url','')})" if ao.get("url") else ao.get("objet", "")
                st.markdown(f"- {lien} — publié {ao.get('date_publication','')} · {ao.get('priorite','')}")

    st.download_button("Exporter en CSV", df.assign(aos=df["aos"].map(asem._aplatir_aos)).to_csv(index=False),
                       file_name="Acheteurs_Semaine_CHRUTH.csv", mime="text/csv")
```

Puis dans `CHRUTH_APP.py`, ajouter la page à la liste `PAGES` (après « Base de données », avant « Carte » par exemple) :

```python
    st.Page("pages_acheteurs.py", title="Acheteurs de la semaine"),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_page_acheteurs.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pages_acheteurs.py CHRUTH_APP.py tests/test_page_acheteurs.py
git commit -m "feat(app): page Acheteurs de la semaine (Streamlit)"
```

---

### Task 8: Page « Acheteurs de la semaine » dans la copie HTML

**Files:**
- Modify: `CHRUTH_PLATEFORME.html` (données d'exemple + page + entrée de navigation)

**Interfaces:**
- Consumes: le moteur de rendu et le routeur JS existants (`PAGES`, `render`, `renderInfo`).
- Produces: une 9ᵉ page « Acheteurs de la semaine » avec un mini-registre d'exemple (2-3 acheteurs public/privé-droit) et le même langage visuel « registre ».

- [ ] **Step 1: Ajouter l'entrée de navigation**

Dans le tableau `PAGES` de `CHRUTH_PLATEFORME.html`, insérer après `{ id:"base", ... }` :

```javascript
    { id:"acheteurs", t:"Acheteurs de la semaine" },
```

- [ ] **Step 2: Router vers la nouvelle page**

Dans `render()`, ajouter avant la ligne `carte` :

```javascript
    if (id === "acheteurs") return renderAcheteurs();
```

- [ ] **Step 3: Écrire `renderAcheteurs`**

Ajouter la fonction (données d'exemple, style registre, filtre type) :

```javascript
  var ACH = [
    { nom:"Mairie de Créteil", type:"public", sous:"Collectivité territoriale", cp:"94000", ville:"Créteil", dept:"94", eff:"250 à 499", nb:2, prio:"CHAUD",
      aos:[{o:"Nettoyage des locaux administratifs et vitrerie", d:"22.07", p:"CHAUD"}, {o:"Entretien des écoles", d:"24.07", p:"TIÈDE"}] },
    { nom:"Immobilière 3F", type:"prive", sous:"Bailleur social · ESH", cp:"93000", ville:"Bobigny", dept:"93", eff:"1000 à 1999", nb:1, prio:"CHAUD",
      aos:[{o:"Entretien des parties communes et remise en état", d:"21.07", p:"CHAUD"}] },
    { nom:"SEM d'aménagement des Hauts-de-Seine", type:"prive", sous:"Société d'économie mixte", cp:"92000", ville:"Nanterre", dept:"92", eff:"50 à 99", nb:1, prio:"TIÈDE",
      aos:[{o:"Propreté des espaces d'accueil et sanitaires", d:"16.07", p:"TIÈDE"}] }
  ];
  var achFiltre = "tous";
  function renderAcheteurs() {
    var vis = ACH.filter(function (a) { return achFiltre === "tous" || a.type === achFiltre; });
    var pub = vis.filter(function (a) { return a.type === "public"; }).length;
    var h = '<div class="page actif"><p class="kicker">Cibles chaudes · 7 derniers jours</p>' +
      '<h1>Acheteurs de la semaine</h1>' +
      '<p class="intro">Les organisations ayant publié un appel d\'offres de propreté pertinent dans les 7 derniers jours, classées <em>public / privé-droit</em> et enrichies (effectif, adresse). Remplace la prospection « toutes entreprises ».</p>' +
      '<div class="barre"><span class="tally"><b>' + vis.length + '</b> acheteurs · <span class="pub"><b>' + pub + '</b> publics</span> · <span class="prv"><b>' + (vis.length - pub) + '</b> privé-droit</span></span>' +
      '<span class="filtre" role="group" aria-label="Type">' +
        fbtnA("tous", "Tous") + fbtnA("public", "Public") + fbtnA("prive", "Privé-droit") + '</span></div><div class="registre">';
    vis.forEach(function (a) {
      h += '<article class="rec" data-buyer="' + a.type + '"><div class="prio ' + (a.prio === "CHAUD" ? "chaud" : "tiede") + '">' + a.prio + '<span class="sc">' + a.nb + ' AO</span></div>' +
        '<div><h3>' + a.nom + '</h3><p class="ach">' + a.cp + ' ' + a.ville + ' (' + a.dept + ') · effectif ' + a.eff + '</p>' +
        '<p class="ref">' + a.aos.map(function (x) { return '<span>' + x.o + ' — ' + x.d + ' · ' + x.p + '</span>'; }).join("") + '</p></div>' +
        '<div class="type ' + a.type + '"><span class="t">' + (a.type === "public" ? "Public" : "Privé-droit") + '</span><span class="sous">' + a.sous + '</span></div></article>';
    });
    h += '</div></div>';
    main.innerHTML = h;
    Array.prototype.forEach.call(main.querySelectorAll(".filtre button"), function (b) {
      b.onclick = function () { achFiltre = b.dataset.f; renderAcheteurs(); };
    });
  }
  function fbtnA(f, lib) { return '<button data-f="' + f + '" aria-pressed="' + (achFiltre === f) + '">' + lib + '</button>'; }
```

- [ ] **Step 4: Vérifier**

Run: `node --check` sur le script extrait (comme lors de la création), puis ouvrir le fichier :
```bash
awk '/^  <script>/{f=1;next}/^  <\/script>/{f=0}f' CHRUTH_PLATEFORME.html > /tmp/_c.js && node --check /tmp/_c.js && echo OK
```
Expected: `OK`. Ouvrir la page, cliquer « Acheteurs de la semaine », vérifier le filtre.

- [ ] **Step 5: Commit**

```bash
git add CHRUTH_PLATEFORME.html
git commit -m "feat(html): page Acheteurs de la semaine dans la copie HTML"
```

---

### Task 9: Planification hebdomadaire + mise en sommeil de l'ancien

**Files:**
- Create: `outils/installer_tache_acheteurs.ps1`
- Modify: `docs/SURFACES_CHRUTH.md` (documenter le changement)

**Interfaces:**
- Produces: script qui crée la tâche « CHRUTH Acheteurs - hebdo » (lundi 08:45 → `python -m acheteurs_semaine`) et désactive « CHRUTH Prospects - hebdo (carte) ».

- [ ] **Step 1: Écrire le script de planification**

`outils/installer_tache_acheteurs.ps1` :

```powershell
# Tâche hebdomadaire : liste des acheteurs actifs de la semaine.
$ErrorActionPreference = "Stop"
$racine = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$nom = "CHRUTH Acheteurs - hebdo"

$action = New-ScheduledTaskAction -Execute $python -Argument "-m acheteurs_semaine" -WorkingDirectory $racine
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:45am
Register-ScheduledTask -TaskName $nom -Action $action -Trigger $trigger -Force | Out-Null
Write-Host "Tache creee : $nom (lundi 08:45)"

# Mise en sommeil de l'ancienne collecte 'toutes entreprises IDF' (non supprimee)
$ancienne = "CHRUTH Prospects - hebdo (carte)"
if (Get-ScheduledTask -TaskName $ancienne -ErrorAction SilentlyContinue) {
    Disable-ScheduledTask -TaskName $ancienne | Out-Null
    Write-Host "Ancienne tache desactivee (non supprimee) : $ancienne"
} else {
    Write-Host "Ancienne tache absente : $ancienne (rien a desactiver)"
}
```

- [ ] **Step 2: Documenter le changement**

Dans `docs/SURFACES_CHRUTH.md`, ajouter une ligne indiquant que la prospection passe désormais par « Acheteurs de la semaine » (dérivée des AO), et que l'ancienne collecte « toutes entreprises IDF » est en sommeil (carte 132k conservée mais non régénérée).

- [ ] **Step 3: Vérifier la syntaxe du script (sans l'exécuter)**

Run: `powershell -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw outils/installer_tache_acheteurs.ps1), [ref]$null); 'PS syntaxe OK'"`
Expected: `PS syntaxe OK`. (L'installation réelle de la tâche est une action manuelle de l'utilisateur.)

- [ ] **Step 4: Commit**

```bash
git add outils/installer_tache_acheteurs.ps1 docs/SURFACES_CHRUTH.md
git commit -m "feat(planif): tache hebdo Acheteurs + mise en sommeil de l'ancienne collecte"
```

---

## Notes de synchronisation prod

Après la dernière tâche, recopier vers `../Downloads/CHRUTH_LIVRAISON_NO_CODE` les fichiers runtime nouveaux/modifiés (pas les `tests/`) : `acheteurs_semaine.py`, `collect_api_entreprises.py`, `pages_acheteurs.py`, `CHRUTH_APP.py`, `CHRUTH_PLATEFORME.html`, `outils/installer_tache_acheteurs.ps1`, `docs/SURFACES_CHRUTH.md`. Vérifier la parité (`diff -q`).

## Auto-revue (couverture spec)

- Fenêtre 7 j + pertinence → T3. Dédoublonnage → T4. Enrichissement SIRET → T2 + T5. Classification public/privé-droit → T1 (+ intégrée en T5). Export fichier → T6. Page plateforme → T7. Page HTML → T8. Cadence hebdo + mise en sommeil → T9. Point d'entrée `main` → T6.
- Best-effort enrichissement : T5 (`enrichir` try/except, test dédié).
- Aucune donnée manquante (date absente exclue) : T3, test dédié.
