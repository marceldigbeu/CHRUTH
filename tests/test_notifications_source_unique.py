"""Un seul interrupteur pour les alertes, quelle que soit la surface.

Deux commutateurs coexistaient pour la meme question — « les emails
partent-ils ? » :

- `alertes_actives.flag`, ecrit et lu par le classeur Excel, le cockpit et
  `outils/set_notifications.py` ;
- `reglages.notifications`, ecrit et lu par Streamlit et le veilleur.

Or `ao_alertes.notifications_ouvertes`, qui decide de l'envoi reel, lit les
reglages et ne retombe sur le drapeau qu'en cas d'erreur. Couper les alertes
depuis Excel ne les coupait donc pas : le classeur affichait OFF, et les
emails continuaient de partir.
"""
from __future__ import annotations

import json

import pytest

import ao_config


@pytest.fixture
def poste(tmp_path, monkeypatch):
    """Drapeau et reglages rediriges vers des copies jetables.

    Sans cette redirection, la suite eteindrait pour de bon les notifications
    du poste en ecrivant les vrais fichiers.
    """
    drapeau = tmp_path / "alertes_actives.flag"
    etat = tmp_path / "veille.json"
    etat.write_text(json.dumps({"version": 1, "aos": {}, "guide_messages": "",
                                "reglages": {"notifications": True}}),
                    encoding="utf-8")
    monkeypatch.setattr(ao_config, "ALERTE_ACTIVE_FILE", drapeau)
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(etat))
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")

    import reglages
    reglages.invalider()
    yield {"drapeau": drapeau, "etat": etat}
    reglages.invalider()


def _reglages_disent(etat_path, actif: bool) -> None:
    import reglages
    data = json.loads(etat_path.read_text(encoding="utf-8"))
    data.setdefault("reglages", {})["notifications"] = actif
    etat_path.write_text(json.dumps(data), encoding="utf-8")
    reglages.invalider()


def test_couper_depuis_excel_coupe_vraiment_les_alertes(poste):
    """Le scenario qui faisait partir des emails apres une coupure.

    On passe par `appliquer`, le chemin qu'emprunte reellement le bouton VBA
    du classeur — et non par `ao_config.set_notifications`, qui n'ecrit que le
    drapeau local.
    """
    import ao_alertes
    from outils import set_notifications

    set_notifications.appliquer(False)

    assert ao_config.notifications_actives() is False, "le classeur doit afficher OFF"
    assert ao_alertes.notifications_ouvertes() is False, \
        "couper dans Excel doit reellement arreter les envois"


def test_activer_depuis_excel_active_partout(poste):
    import ao_alertes
    import veille_etat
    from outils import set_notifications

    _reglages_disent(poste["etat"], False)
    set_notifications.appliquer(True)

    assert ao_config.notifications_actives() is True
    assert ao_alertes.notifications_ouvertes() is True
    etat = json.loads(poste["etat"].read_text(encoding="utf-8"))
    assert veille_etat.notifications_actives(etat) is True, \
        "Streamlit doit voir le meme etat que le classeur"


def test_couper_depuis_streamlit_se_voit_dans_excel(poste):
    """L'autre sens : le classeur affichait ON apres une coupure dans l'app."""
    _reglages_disent(poste["etat"], False)

    assert ao_config.notifications_actives() is False, \
        "le classeur doit refleter les reglages partages"


def test_les_reglages_font_autorite_sur_le_drapeau(poste):
    """En cas de desaccord, la source unique tranche — sinon le bug revient."""
    poste["drapeau"].write_text("ON", encoding="utf-8")
    _reglages_disent(poste["etat"], False)

    assert ao_config.notifications_actives() is False


def test_sans_reglages_lisibles_le_drapeau_prend_le_relais(poste, monkeypatch):
    """Hors ligne ou etat illisible, le poste doit rester pilotable."""
    poste["etat"].write_text("{ceci n'est pas du json", encoding="utf-8")
    import reglages
    monkeypatch.setattr(reglages, "lire", lambda: (_ for _ in ()).throw(RuntimeError("hors ligne")))

    poste["drapeau"].write_text("OFF", encoding="utf-8")
    assert ao_config.notifications_actives() is False
    poste["drapeau"].write_text("ON", encoding="utf-8")
    assert ao_config.notifications_actives() is True


def test_sans_drapeau_ni_reglages_les_alertes_restent_actives(poste, monkeypatch):
    """Un etat muet ne doit pas eteindre silencieusement la veille."""
    import reglages
    monkeypatch.setattr(reglages, "lire", lambda: (_ for _ in ()).throw(RuntimeError("hors ligne")))
    assert ao_config.notifications_actives() is True


# --- Collecte : meme motif que les notifications ----------------------------

def test_couper_la_collecte_depuis_streamlit_arrete_la_pipeline(poste):
    """`ao_alertes_run` et la mise a jour hebdomadaire interrogent
    `collecte_active`. Si elle ignore les reglages, couper la collecte dans
    l'application laisse la pipeline continuer d'interroger le reseau."""
    import reglages
    data = json.loads(poste["etat"].read_text(encoding="utf-8"))
    data.setdefault("reglages", {})["collecte"] = False
    poste["etat"].write_text(json.dumps(data), encoding="utf-8")
    reglages.invalider()

    assert ao_config.collecte_active() is False


def test_la_collecte_garde_un_repli_hors_ligne(poste, monkeypatch, tmp_path):
    import reglages
    monkeypatch.setattr(reglages, "lire",
                        lambda: (_ for _ in ()).throw(RuntimeError("hors ligne")))
    drapeau = tmp_path / "collecte_active.flag"
    monkeypatch.setattr(ao_config, "COLLECTE_ACTIVE_FILE", drapeau)
    drapeau.write_text("OFF", encoding="utf-8")
    assert ao_config.collecte_active() is False
    drapeau.write_text("ON", encoding="utf-8")
    assert ao_config.collecte_active() is True


# --- Fiche CHRUTH : remplie dans l'app, ignoree a la redaction --------------

FICHE = "## Coordonnées\n- Email : contact@chruth.fr\n- Téléphone : 01 23 45 67 89\n"


def test_la_fiche_remplie_dans_l_app_sert_a_la_redaction(poste):
    """Elle etait ecrite dans les reglages et relue depuis le fichier : la
    remplir depuis la page Reglages n'avait donc aucun effet sur les messages,
    qui partaient sans coordonnees ni signature."""
    import prospect_messages
    import reglages
    import signature

    data = json.loads(poste["etat"].read_text(encoding="utf-8"))
    data.setdefault("reglages", {})["fiche_chruth"] = FICHE
    poste["etat"].write_text(json.dumps(data), encoding="utf-8")
    reglages.invalider()

    lue = prospect_messages.fiche_chruth()
    assert "contact@chruth.fr" in lue
    assert "01 23 45 67 89" in signature.bloc(lue), \
        "la signature doit reprendre les coordonnees saisies dans l'app"


def test_la_fiche_du_fichier_sert_de_repli(poste, monkeypatch, tmp_path):
    """Le fichier reste utilisable seul : poste hors ligne, ou fiche editee
    directement dans `config_chruth/fiche_chruth.md`."""
    import prospect_messages
    import reglages

    monkeypatch.setattr(reglages, "lire",
                        lambda: (_ for _ in ()).throw(RuntimeError("hors ligne")))
    fichier = tmp_path / "fiche.md"
    fichier.write_text("## Coordonnées\n- Email : depuis.le.fichier@chruth.fr\n",
                       encoding="utf-8")
    assert "depuis.le.fichier@chruth.fr" in prospect_messages.fiche_chruth(fichier)


def test_une_fiche_vide_dans_les_reglages_laisse_le_fichier_parler(poste, tmp_path):
    """Les reglages font autorite, mais une fiche vide n'est pas une decision :
    c'est l'etat par defaut. Le fichier doit alors pouvoir servir."""
    import prospect_messages
    import reglages

    data = json.loads(poste["etat"].read_text(encoding="utf-8"))
    data.setdefault("reglages", {})["fiche_chruth"] = "   "
    poste["etat"].write_text(json.dumps(data), encoding="utf-8")
    reglages.invalider()

    fichier = tmp_path / "fiche.md"
    fichier.write_text("## Coordonnées\n- Email : depuis.le.fichier@chruth.fr\n",
                       encoding="utf-8")
    assert "depuis.le.fichier@chruth.fr" in prospect_messages.fiche_chruth(fichier)
