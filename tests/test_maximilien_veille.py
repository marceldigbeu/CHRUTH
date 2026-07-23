"""Veilleur Maximilien : email dedie par AO, idempotence, tracabilite."""
import ao_maximilien_veille as mv
from ao_pertinence import PERTINENT, REJETE, Verdict


def _ao(id_ao="MX-939252", objet="Nettoyage des locaux du MAC VAL"):
    return {"id_ao": id_ao, "objet": objet, "acheteur": "Departement 94", "ville": "VITRY",
            "departement": "94", "date_limite": "2026-09-28", "procedure": "MAPA",
            "url": "https://marches.maximilien.fr/entreprise/consultation/939252",
            "score": 65, "priorite": "CHAUD"}


def test_l_email_porte_l_essentiel_dans_son_objet():
    sujet, html, texte = mv.construire_email_ao(_ao(), Verdict(PERTINENT, "listes", "ok"))
    assert sujet.startswith("[Maximilien]")
    assert "VITRY" in sujet


def test_l_email_contient_le_lien_et_le_motif_du_tri():
    _, html, texte = mv.construire_email_ao(
        _ao(), Verdict(PERTINENT, "ia", "entretien de locaux publics"))
    assert "consultation/939252" in html
    assert "entretien de locaux publics" in html
    assert "entretien de locaux publics" in texte
    assert "2026-09-28" in texte


def test_un_ao_rejete_n_est_pas_notifie(tmp_path, monkeypatch):
    monkeypatch.setattr(mv, "collecter", lambda: [_ao(objet="Elagage des arbres communaux")])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))

    assert mv.veiller(etat_path=tmp_path / "veille.json") == 0
    assert envoyes == []


def test_un_ao_pertinent_declenche_un_email(tmp_path, monkeypatch):
    monkeypatch.setattr(mv, "collecter", lambda: [_ao()])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))

    assert mv.veiller(etat_path=tmp_path / "veille.json") == 1
    assert len(envoyes) == 1


def test_un_email_par_ao(tmp_path, monkeypatch):
    monkeypatch.setattr(mv, "collecter",
                        lambda: [_ao("MX-1"), _ao("MX-2", "Nettoyage des ecoles")])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))

    assert mv.veiller(etat_path=tmp_path / "veille.json") == 2
    assert len(envoyes) == 2


def test_le_second_passage_ne_renotifie_rien(tmp_path, monkeypatch):
    """L'idempotence est la propriete vitale : la veille tourne toutes les 30 min."""
    monkeypatch.setattr(mv, "collecter", lambda: [_ao()])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))
    etat = tmp_path / "veille.json"

    assert mv.veiller(etat_path=etat) == 1
    assert mv.veiller(etat_path=etat) == 0
    assert len(envoyes) == 1


def test_un_echec_smtp_permet_un_reessai_au_run_suivant(tmp_path, monkeypatch):
    monkeypatch.setattr(mv, "collecter", lambda: [_ao()])

    def envoi_casse(s, h, t):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(mv, "_envoyer", envoi_casse)
    etat = tmp_path / "veille.json"
    assert mv.veiller(etat_path=etat) == 0

    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))
    assert mv.veiller(etat_path=etat) == 1


def test_collecter_rattache_le_detail_a_l_ao(monkeypatch):
    """_to_ao ne produit que des colonnes de base : sans ce rattachement, le tri
    recevrait toujours un detail vide."""
    import ao_maximilien_scrape as scrape

    brut = {"cid": "1", "org": "org1", "reference": "R", "intitule": "Nettoyage des locaux",
            "objet_desc": "entretien courant des bureaux", "organisme": "Mairie",
            "cp": "93000", "ville": "STAINS", "procedure": "MAPA",
            "date_limite_txt": "14 Avril 2026", "url": "https://x/1"}
    monkeypatch.setattr(scrape, "_session", lambda: None)
    monkeypatch.setattr(scrape, "KEYWORDS", ["nettoyage"])
    monkeypatch.setattr(scrape, "_pages_resultats", lambda session, kw: iter(["<html></html>"]))
    monkeypatch.setattr(scrape, "_parse_resultats", lambda html: [brut])

    aos = mv.collecter()
    assert aos[0]["objet_desc"] == "entretien courant des bureaux"


def test_collecter_expose_url_et_score_sous_les_noms_de_l_etat(monkeypatch):
    """_to_ao nomme ses champs comme les colonnes de la base (url_avis / score_chruth).
    L'email et l'etat lisent url / score : sans alias, le lien et le score sont vides."""
    import ao_maximilien_scrape as scrape

    brut = {"cid": "1", "org": "org1", "reference": "R", "intitule": "Nettoyage des locaux",
            "objet_desc": "", "organisme": "Mairie", "cp": "93000", "ville": "STAINS",
            "procedure": "MAPA", "date_limite_txt": "14 Avril 2026",
            "url": "https://marches.maximilien.fr/entreprise/consultation/1"}
    monkeypatch.setattr(scrape, "_session", lambda: None)
    monkeypatch.setattr(scrape, "KEYWORDS", ["nettoyage"])
    monkeypatch.setattr(scrape, "_pages_resultats", lambda session, kw: iter(["<html></html>"]))
    monkeypatch.setattr(scrape, "_parse_resultats", lambda html: [brut])

    ao = mv.collecter()[0]
    assert ao["url"] == brut["url"]
    assert str(ao["score"]) == str(ao["score_chruth"])

    _, html, _ = mv.construire_email_ao(ao, Verdict(PERTINENT, "listes", "ok"))
    assert "consultation/1" in html


def test_l_ao_rejete_est_quand_meme_trace(tmp_path, monkeypatch):
    """Rejete ne veut pas dire invisible : l'app doit pouvoir le montrer et le corriger."""
    import veille_etat as ve
    monkeypatch.setattr(mv, "collecter", lambda: [_ao(objet="Elagage des arbres")])
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: None)
    etat_path = tmp_path / "veille.json"
    mv.veiller(etat_path=etat_path)

    etat = ve.charger(etat_path)
    assert etat["aos"]["MX-939252"]["tri"]["verdict"] == REJETE
