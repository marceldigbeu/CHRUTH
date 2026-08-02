"""Les identifiants d'envoi se modifient depuis l'app, sans jamais partir en ligne."""
from __future__ import annotations

import json

import identifiants_smtp as ids


def _fichier(tmp_path):
    return tmp_path / "alertes_secrets.json"


def test_un_fichier_absent_ne_casse_rien(tmp_path):
    chemin = _fichier(tmp_path)
    assert ids.lire(chemin) == {}
    assert ids.expediteur(chemin) == ""
    assert ids.mot_de_passe_defini(chemin) is False


def test_un_fichier_corrompu_ne_casse_rien(tmp_path):
    chemin = _fichier(tmp_path)
    chemin.write_text("{ceci n'est pas du json", encoding="utf-8")
    assert ids.lire(chemin) == {}


def test_l_expediteur_s_enregistre_et_se_relit(tmp_path):
    chemin = _fichier(tmp_path)
    ids.ecrire({"smtp_user": "envoi@chruth.fr"}, chemin)
    assert ids.expediteur(chemin) == "envoi@chruth.fr"


def test_le_mot_de_passe_n_est_jamais_renvoye(tmp_path):
    """On ne sait que s'il existe : le reafficher dans un champ le met a portee
    de la premiere capture d'ecran."""
    chemin = _fichier(tmp_path)
    ids.ecrire({"smtp_password": "abcdefghijklmnop"}, chemin)
    assert ids.mot_de_passe_defini(chemin) is True
    assert not hasattr(ids, "mot_de_passe")


def test_les_espaces_d_un_mot_de_passe_google_sont_retires(tmp_path):
    """Google affiche « abcd efgh ijkl mnop » : colle tel quel, l'envoi echoue."""
    chemin = _fichier(tmp_path)
    ids.ecrire({"smtp_password": "abcd efgh ijkl mnop"}, chemin)
    assert json.loads(chemin.read_text(encoding="utf-8"))["smtp_password"] == "abcdefghijklmnop"


def test_un_champ_laisse_vide_ne_efface_pas_l_existant(tmp_path):
    """Le cas courant : on ne modifie que l'expediteur, on laisse le champ mot
    de passe vide. L'effacer obligerait a le retaper a chaque changement."""
    chemin = _fichier(tmp_path)
    ids.ecrire({"smtp_user": "a@b.fr", "smtp_password": "secret-en-place"}, chemin)
    ids.ecrire({"smtp_user": "nouveau@b.fr", "smtp_password": ""}, chemin)
    assert ids.expediteur(chemin) == "nouveau@b.fr"
    assert ids.mot_de_passe_defini(chemin) is True


def test_on_peut_effacer_explicitement_un_mot_de_passe(tmp_path):
    chemin = _fichier(tmp_path)
    ids.ecrire({"smtp_password": "secret"}, chemin)
    ids.oublier("smtp_password", chemin)
    assert ids.mot_de_passe_defini(chemin) is False


def test_les_autres_valeurs_du_fichier_sont_preservees(tmp_path):
    chemin = _fichier(tmp_path)
    chemin.write_text(json.dumps({"destinataire": "client@x.fr", "autre": "garde"}),
                      encoding="utf-8")
    ids.ecrire({"smtp_user": "a@b.fr"}, chemin)
    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    assert contenu["destinataire"] == "client@x.fr"
    assert contenu["autre"] == "garde"


def test_le_mot_de_passe_ne_passe_jamais_par_les_reglages_partages():
    """Garde-fou : `reglages` est ecrit dans l'etat de veille, pousse sur une
    branche GitHub. Un mot de passe ecrit la serait publie."""
    import reglages
    assert "smtp_password" in reglages.CLES_INTERDITES
    assert "smtp_password" not in reglages.DEFAUTS


def test_le_module_ecrit_bien_dans_le_fichier_ignore_par_git():
    from pathlib import Path
    racine = Path(__file__).resolve().parent.parent
    regles = (racine / ".gitignore").read_text(encoding="utf-8")
    assert "alertes_secrets.json" in regles
