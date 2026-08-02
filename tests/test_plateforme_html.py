"""Le miroir HTML doit porter les vraies donnees, et aucune adresse email."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd
import pytest

import plateforme_html as ph

AUJOURD_HUI = date.today()


def _dans(jours: int) -> str:
    return (AUJOURD_HUI + timedelta(days=jours)).isoformat()


def _base(lignes=None) -> pd.DataFrame:
    return pd.DataFrame(lignes if lignes is not None else [
        {"id_ao": "26-1", "objet": "Nettoyage des ecoles", "acheteur": "Mairie de Creteil",
         "ville": "Creteil", "departement": "94", "source": "BOAMP", "procedure": "MAPA",
         "date_publication": "2026-07-22", "date_limite": _dans(40), "priorite": "CHAUD",
         "score_chruth": "72.4", "secteur": "Mairie", "categorie": "Batiments",
         "verdict_tri": "PERTINENT", "motif_tri": "mot-cle nettoyage",
         "url_avis": "https://boamp.fr/1"},
        {"id_ao": "26-2", "objet": "Vitrerie", "acheteur": "SA Immobiliere",
         "ville": "Paris", "departement": "75", "source": "BOAMP", "procedure": "AOO",
         "date_publication": "2026-07-24", "date_limite": _dans(10), "priorite": "TIEDE",
         "score_chruth": "51.0", "secteur": "Autre", "categorie": "Vitres",
         "verdict_tri": "", "motif_tri": "", "url_avis": ""},
        {"id_ao": "26-3", "objet": "Marche expire", "acheteur": "Ville de X",
         "ville": "X", "departement": "93", "source": "BOAMP", "procedure": "",
         "date_publication": "2026-05-01", "date_limite": _dans(-3), "priorite": "CHAUD",
         "score_chruth": "90.0", "secteur": "Mairie", "categorie": "Batiments",
         "verdict_tri": "PERTINENT", "motif_tri": "", "url_avis": ""},
    ])


# --- Conversion d'un AO -----------------------------------------------------

def test_un_ao_prend_la_forme_attendue_par_le_javascript():
    ao = ph.ao_vers_miroir(_base().to_dict("records")[0])
    assert ao["id"] == "26-1"
    assert ao["prio"] == "chaud"
    assert ao["score"] == 72.4
    assert ao["publie"] == "22.07"
    assert ao["limite"].count(".") == 2


def test_le_score_garde_sa_decimale():
    """Le miroir doit dire la meme chose que l'application, au dixieme pres."""
    ao = ph.ao_vers_miroir({"score_chruth": "68.3"})
    assert ao["score"] == 68.3


def test_un_score_illisible_ne_casse_pas_la_conversion():
    assert ph.ao_vers_miroir({"score_chruth": "a verifier"})["score"] == 0.0
    assert ph.ao_vers_miroir({})["score"] == 0.0


def test_une_mairie_est_reconnue_comme_acheteur_public():
    assert ph.ao_vers_miroir({"acheteur": "Mairie de Creteil"})["buyer"] == "public"
    assert ph.ao_vers_miroir({"acheteur": "Ville de Stains"})["buyer"] == "public"
    assert ph.ao_vers_miroir({"acheteur": "Centre hospitalier Sud"})["buyer"] == "public"


def test_un_acheteur_prive_n_est_pas_classe_public():
    assert ph.ao_vers_miroir({"acheteur": "SA Immobiliere du Nord"})["buyer"] == "prive"


def test_un_ao_non_trie_le_dit_au_lieu_de_rester_vide():
    assert ph.ao_vers_miroir({"verdict_tri": ""})["verdict"] == "NON TRIE"


def test_une_date_absente_ou_cassee_donne_une_chaine_vide():
    ao = ph.ao_vers_miroir({"date_publication": "", "date_limite": "a preciser"})
    assert ao["publie"] == "" and ao["limite"] == ""


# --- Selection --------------------------------------------------------------

def test_les_marches_expires_sont_exclus():
    """Dans un fichier consulte en mobilite, ils occupent l'ecran sans servir."""
    objets = [a["objet"] for a in ph.donnees_aos(_base())]
    assert "Marche expire" not in objets


def test_les_mieux_notes_arrivent_en_tete():
    scores = [a["score"] for a in ph.donnees_aos(_base())]
    assert scores == sorted(scores, reverse=True)


def test_la_liste_est_plafonnee():
    lignes = [{"id_ao": str(i), "score_chruth": str(i), "date_limite": _dans(30)}
              for i in range(300)]
    assert len(ph.donnees_aos(pd.DataFrame(lignes), limite=50)) == 50


def test_une_base_vide_donne_une_liste_vide():
    assert ph.donnees_aos(pd.DataFrame()) == []
    assert ph.donnees_aos(None) == []


# --- Reglages ---------------------------------------------------------------

def test_les_destinataires_ne_sortent_jamais():
    """Le fichier est fait pour etre envoye : y embarquer des adresses
    reviendrait a les publier."""
    propres = ph.reglages_publics({
        "destinataires": ["client@chruth.fr", "moi@gmail.com"],
        "expediteur": "envoi@gmail.com", "notifications": True})
    assert propres["destinataires"] == []
    assert "expediteur" not in propres
    assert "smtp_password" not in propres


def test_les_interrupteurs_sont_conserves():
    propres = ph.reglages_publics({"notifications": False, "collecte": True,
                                   "mots_cles_rh_actifs": False})
    assert propres["notifications"] is False
    assert propres["collecte"] is True
    assert propres["rh"] is False


def test_la_fiche_chruth_est_conservee():
    """Elle decrit l'entreprise, ce n'est pas une donnee personnelle."""
    propres = ph.reglages_publics({"fiche_chruth": "Nettoyage en Ile-de-France."})
    assert "Ile-de-France" in propres["fiche"]


def test_des_reglages_absents_ne_cassent_rien():
    assert ph.reglages_publics(None)["destinataires"] == []
    assert ph.reglages_publics({})["notifications"] is True


# --- Injection dans le modele -----------------------------------------------

MODELE = """<html><script>
  var AOS = [
    { id:"MX-1", objet:"Exemple [lot 1]" }
  ];
  var ACH = [
    { nom:"Exemple" }
  ];
  var PAGES = [];
</script></html>"""


def test_le_tableau_est_remplace_par_les_donnees_reelles():
    sortie = ph.remplacer_tableau(MODELE, "AOS", [{"id": "26-1", "objet": "Nettoyage"}])
    assert "MX-1" not in sortie
    assert '"id": "26-1"' in sortie
    assert "var ACH = [" in sortie, "les autres tableaux ne doivent pas bouger"


def test_un_crochet_dans_un_intitule_ne_tronque_pas_le_tableau():
    """Les intitules de marches contiennent des crochets : « [lot 1] ». Une
    expression reguliere gourmande couperait le tableau au premier venu."""
    sortie = ph.remplacer_tableau(MODELE, "AOS", [{"objet": "Marche [lot 2]"}])
    assert "var ACH = [" in sortie
    assert "var PAGES = [];" in sortie


def test_un_tableau_absent_du_modele_est_signale():
    with pytest.raises(ValueError, match="introuvable"):
        ph.remplacer_tableau(MODELE, "INEXISTANT", [])


def test_les_accents_et_guillemets_survivent_a_l_injection():
    sortie = ph.remplacer_tableau(MODELE, "AOS",
                                  [{"objet": 'Marché « propreté » de l\'école'}])
    donnees = json.loads(sortie[sortie.index("var AOS = ") + 10: sortie.index(";", sortie.index("var AOS = "))])
    assert donnees[0]["objet"] == 'Marché « propreté » de l\'école'


# --- Garde-fou de sortie ----------------------------------------------------

def test_le_garde_fou_repere_une_adresse_email():
    assert ph.contient_une_adresse_email("contact: client@chruth.fr ok") is True


def test_le_garde_fou_ne_se_declenche_pas_sur_du_html_ordinaire():
    assert ph.contient_une_adresse_email("<div>Nettoyage des locaux</div>") is False


# --- Acheteurs de la semaine ------------------------------------------------

def _acheteurs_df():
    return pd.DataFrame([{
        "acheteur": "Mairie du Perreux sur Marne", "type": "public",
        "type_incertain": "False", "priorite": "CHAUD", "nb_ao_semaine": "2",
        "departement": "94", "ville": "LE PERREUX SUR MARNE", "code_postal": "94170",
        "effectif": "500 à 999 salariés",
        "aos": [{"objet": "Travaux d'entretien", "date_publication": "2026-07-29",
                 "priorite": "CHAUD", "url": "https://boamp.fr/1"}],
    }])


def test_le_dataframe_des_acheteurs_est_accepte_tel_quel():
    """`acheteurs_semaine.construire` rend un DataFrame : le generateur ne doit
    pas avoir a le convertir lui-meme."""
    sortie = ph.donnees_acheteurs(_acheteurs_df())
    assert sortie[0]["nom"] == "Mairie du Perreux sur Marne"
    assert sortie[0]["nb"] == 2
    assert sortie[0]["aos"][0]["d"] == "29.07"


def test_les_marches_serialises_en_chaine_sont_relus():
    """Apres un aller-retour par CSV, la sous-liste arrive en texte."""
    df = _acheteurs_df()
    df.at[0, "aos"] = str(df.at[0, "aos"])
    assert ph.donnees_acheteurs(df)[0]["aos"][0]["o"] == "Travaux d'entretien"


def test_un_type_incertain_est_signale():
    df = _acheteurs_df()
    df.at[0, "type_incertain"] = "True"
    assert ph.donnees_acheteurs(df)[0]["sous"] == "à confirmer"


def test_des_acheteurs_absents_ne_cassent_rien():
    assert ph.donnees_acheteurs(None) == []
    assert ph.donnees_acheteurs(pd.DataFrame()) == []
    assert ph.donnees_acheteurs([]) == []


def test_les_destinataires_ecrits_en_dur_sont_vides():
    """Ils vivent dans l'objet des reglages, hors de tout `var` : ils
    echappaient au remplacement des tableaux."""
    modele = 'reglages: { notifications:true,\n destinataires:["a@b.fr","c@d.fr"],\n fiche:"x" }'
    sortie = ph.vider_destinataires(modele)
    assert "a@b.fr" not in sortie
    assert "destinataires:[]" in sortie
    assert "notifications:true" in sortie


def test_une_liste_deja_vide_reste_valide():
    assert "destinataires:[]" in ph.vider_destinataires("destinataires:[]")


def test_les_ao_rejetes_par_le_tri_ne_sont_pas_embarques():
    """Le miroir doit dire la meme chose que l'application. Sans ce filtre, un
    marche hors sujet mais bien note arrive en tete de la liste."""
    df = pd.DataFrame([
        {"id_ao": "1", "objet": "Formation discriminations", "score_chruth": "93.5",
         "verdict_tri": "REJETE", "date_limite": _dans(30)},
        {"id_ao": "2", "objet": "Nettoyage des locaux", "score_chruth": "71.0",
         "verdict_tri": "PERTINENT", "date_limite": _dans(30)},
    ])
    objets = [a["objet"] for a in ph.donnees_aos(df)]
    assert objets == ["Nettoyage des locaux"]


def test_un_ao_non_trie_reste_embarque():
    """On cache ce qui est juge hors sujet, pas ce qui n'a pas encore ete juge."""
    df = pd.DataFrame([{"id_ao": "1", "objet": "Nettoyage", "score_chruth": "60",
                        "verdict_tri": "", "date_limite": _dans(30)}])
    assert len(ph.donnees_aos(df)) == 1
