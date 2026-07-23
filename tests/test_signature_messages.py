"""La signature traverse les deux generateurs de messages."""
import ao_messages
import prospect_messages as pm

FICHE = ("## Coordonnées\n- Site : https://www.exemple-chruth.fr\n"
         "- Email : contact@chruth.fr\n- Téléphone : 01 23 45 67 89\n")


class FauxClient:
    def __init__(self, reponse):
        self.reponse = reponse

    def llm_disponible(self):
        return True

    def generer(self, prompt, system="", **kw):
        return self.reponse


def _ao():
    return {"id_ao": "MX-1", "objet": "Nettoyage des locaux", "acheteur": "Mairie",
            "ville": "STAINS", "date_limite": "2026-09-28", "priorite": "CHAUD"}


def test_le_message_ao_genere_porte_la_signature():
    client = FauxClient('{"email": "Bonjour,", "script": "Allo,"}')
    msg = ao_messages.generer_message_ao(_ao(), client=client, fiche=FICHE)
    assert "contact@chruth.fr" in msg["email"]
    assert "contact@chruth.fr" in msg["script"]


def test_le_repli_deterministe_porte_aussi_la_signature():
    """Sans moteur, le message part quand meme : il doit etre signe pareil."""
    class Indisponible(FauxClient):
        def llm_disponible(self):
            return False

    msg = ao_messages.generer_message_ao(_ao(), client=Indisponible(""), fiche=FICHE)
    assert "01 23 45 67 89" in msg["email"]


def test_sans_coordonnees_aucun_message_n_invente():
    client = FauxClient('{"email": "Bonjour,", "script": "Allo,"}')
    msg = ao_messages.generer_message_ao(_ao(), client=client, fiche="")
    assert "@" not in msg["email"]


def test_le_prompt_interdit_au_modele_d_ecrire_des_coordonnees():
    _, prompt = ao_messages.prompt_ao(_ao(), fiche=FICHE)
    assert "coordonn" in prompt.lower()


def test_le_rendu_prospect_porte_la_signature():
    rendu = pm.rendre("Bonjour {denomination},", {"denomination": "ACME"}, fiche=FICHE)
    assert "ACME" in rendu
    assert "contact@chruth.fr" in rendu


def test_le_rendu_prospect_sans_fiche_reste_inchange():
    """Anti-regression : la fiche livree est vide, les tests existants ne bougent pas."""
    assert pm.rendre("Bonjour {denomination},", {"denomination": "ACME"}, fiche="") == "Bonjour ACME,"
