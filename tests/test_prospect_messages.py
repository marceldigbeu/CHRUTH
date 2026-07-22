import pandas as pd

import prospect_messages as pm


def _df():
    return pd.DataFrame([
        {"denomination": "Alpha", "libelle_commune": "Paris", "effectif_label": "10 a 19",
         "categorie_chruth": "PRIV_BUREAU", "priorite": "CHAUDE"},
        {"denomination": "Beta", "libelle_commune": "Lyon", "effectif_label": "1 a 2",
         "categorie_chruth": "PRIV_COMMERCE", "priorite": "FROIDE"},
        {"denomination": "Gamma", "libelle_commune": "Nice", "effectif_label": "20 a 49",
         "categorie_chruth": "PRIV_BUREAU", "priorite": "CHAUDE"},
    ])


class _FakeClient:
    def __init__(self, dispo=True, reponse=""):
        self._dispo, self._reponse, self.appels = dispo, reponse, 0

    def llm_disponible(self):
        return self._dispo

    def generer(self, prompt, system="", **kw):
        self.appels += 1
        return self._reponse


# --- Task 2 : segments / repli / rendu ---

def test_segments_activables_exclut_froide_et_dedup():
    segs = pm.segments_activables(_df())
    assert ("PRIV_BUREAU", "CHAUDE") in segs
    assert ("PRIV_COMMERCE", "FROIDE") not in segs
    assert len(segs) == len(set(segs))


def test_template_par_defaut_contient_placeholders():
    t = pm.template_par_defaut("PRIV_BUREAU", "CHAUDE")
    assert "{denomination}" in t["email"]
    assert t["email"].strip() and t["script"].strip()


def test_rendre_insere_variables_sans_exception():
    row = {"denomination": "Alpha", "libelle_commune": "Paris", "effectif_label": "10 a 19"}
    txt = pm.rendre("Bonjour {denomination} a {ville} ({effectif})", row)
    assert txt == "Bonjour Alpha a Paris (10 a 19)"


def test_rendre_placeholder_manquant_donne_vide():
    txt = pm.rendre("X {denomination} {ville}", {"denomination": "Alpha"})
    assert txt == "X Alpha "


# --- Task 3 : generation templates + cache ---

def test_generer_templates_repli_si_indisponible(tmp_path):
    client = _FakeClient(dispo=False)
    cache = tmp_path / "c.json"
    res = pm.generer_templates([("PRIV_BUREAU", "CHAUDE")], cache_path=cache, client=client)
    t = res["PRIV_BUREAU|CHAUDE"]
    assert t["source"] == "defaut"
    assert "{denomination}" in t["email"]
    assert client.appels == 0


def test_generer_templates_ia_et_cache(tmp_path):
    bonne_reponse = '{"email": "Bonjour {denomination} a {ville}", "script": "Appel {denomination}"}'
    client = _FakeClient(dispo=True, reponse=bonne_reponse)
    cache = tmp_path / "c.json"
    res1 = pm.generer_templates([("PRIV_BUREAU", "CHAUDE")], cache_path=cache, client=client)
    assert res1["PRIV_BUREAU|CHAUDE"]["source"] == "ia"
    assert client.appels == 1
    res2 = pm.generer_templates([("PRIV_BUREAU", "CHAUDE")], cache_path=cache, client=client)
    assert client.appels == 1
    assert res2["PRIV_BUREAU|CHAUDE"]["email"].startswith("Bonjour")


def test_parser_tolere_fences_et_sauts_de_ligne():
    # cas frequent des petits modeles : fence markdown + newlines bruts dans les strings
    txt = '```json\n{"email": "Bonjour {denomination},\nvoici notre offre.", "script": "Appel {denomination}"}\n```'
    data = pm._parser_reponse(txt)
    assert data is not None
    assert "{denomination}" in data["email"]
    assert "voici notre offre" in data["email"]


def test_parser_aplatit_objet_imbrique():
    # certains modeles renvoient script comme un objet {etape: phrase} au lieu d'une chaine
    txt = ('{"email": "Bonjour {denomination} a {ville}", '
           '"script": {"intro": "Bonjour, CHRUTH a l\'appareil", "demande": "Quelles pieces ?"}}')
    data = pm._parser_reponse(txt)
    assert data is not None
    assert isinstance(data["script"], str)
    assert "Bonjour, CHRUTH a l'appareil" in data["script"]
    assert "Quelles pieces ?" in data["script"]
    assert "{" not in data["script"]  # pas de repr de dict


def test_parser_fusionne_objets_json_separes():
    # certains modeles sortent email et script dans 2 blocs JSON distincts
    txt = ('```json\n{"email": "Bonjour {denomination} a {ville}"}\n```\n'
           '```json\n{"script": "Appel {denomination}"}\n```')
    data = pm._parser_reponse(txt)
    assert data is not None
    assert "{denomination}" in data["email"]
    assert data["script"].startswith("Appel")


def test_template_valide_accepte_placeholder_reparti():
    # {denomination} dans le script + {ville} dans l'email = personnalise => valide
    assert pm._template_valide({"email": "Bonjour, vos locaux a {ville}.",
                                "script": "Appel {denomination} a {ville}"}) is True


def test_template_valide_refuse_sans_placeholder():
    assert pm._template_valide({"email": "Bonjour generique", "script": "Appel generique"}) is False
    # {denomination} present mais email non personnalise => refuse
    assert pm._template_valide({"email": "Bonjour generique", "script": "Appel {denomination}"}) is False


def test_generer_templates_accepte_placeholder_reparti(tmp_path):
    rep = '{"email": "Bonjour, vos locaux a {ville}.", "script": "Appel {denomination} a {ville}"}'
    client = _FakeClient(dispo=True, reponse=rep)
    res = pm.generer_templates([("PRIV_BUREAU", "CHAUDE")], cache_path=tmp_path / "c.json", client=client)
    assert res["PRIV_BUREAU|CHAUDE"]["source"] == "ia"


def test_generer_templates_repli_si_reponse_invalide(tmp_path):
    client = _FakeClient(dispo=True, reponse="pas du json sans placeholder")
    cache = tmp_path / "c.json"
    res = pm.generer_templates([("PRIV_BUREAU", "CHAUDE")], cache_path=cache, client=client)
    assert res["PRIV_BUREAU|CHAUDE"]["source"] == "defaut"


# --- Task 4 : orchestrateur ---

def test_generer_pour_df_ajoute_brouillons_aux_activables(tmp_path):
    client = _FakeClient(dispo=False)  # repli deterministe
    cache = tmp_path / "c.json"
    df2, templates = pm.generer_pour_df(_df(), cache_path=cache, client=client)
    assert "brouillon_email" in df2.columns and "brouillon_script" in df2.columns
    alpha = df2[df2["denomination"] == "Alpha"].iloc[0]
    beta = df2[df2["denomination"] == "Beta"].iloc[0]
    assert "Alpha" in alpha["brouillon_email"]
    assert beta["brouillon_email"] == ""
    assert set(templates["categorie"]) == {"PRIV_BUREAU"}
    assert {"categorie", "priorite", "email", "script", "source"}.issubset(templates.columns)
