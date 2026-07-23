"""Etage 2 du tri : arbitrage IA des cas ambigus. Aucun appel reseau."""
import ao_pertinence as ap
from ao_pertinence import PERTINENT, REJETE


class FauxClient:
    """Client LLM injecte : aucun appel reseau."""

    def __init__(self, reponse: str, disponible: bool = True):
        self.reponse = reponse
        self.disponible = disponible
        self.prompts: list[str] = []

    def moteur_auto(self):
        return "groq" if self.disponible else None

    def generer(self, prompt, system="", timeout=60, temperature=0.1, **kw):
        self.prompts.append(prompt)
        return self.reponse


def test_cas_net_ne_consulte_jamais_l_ia():
    client = FauxClient('{"verdict": "PERTINENT", "motif": "x"}')
    v = ap.trier("Nettoyage des locaux du MAC VAL", client=client)
    assert v.etage == "listes"
    assert client.prompts == []


def test_cas_ambigu_arbitre_par_l_ia():
    client = FauxClient(
        '{"verdict": "NON_PERTINENT", "motif": "conservation d\'archives, pas d\'entretien de locaux"}'
    )
    v = ap.trier("Reconditionnement de reserves documentaires",
                 detail="inclut une prestation de nettoyage", client=client)
    assert v.verdict == REJETE
    assert v.etage == "ia"
    assert "archives" in v.motif
    assert len(client.prompts) == 1


def test_reponse_ia_entouree_de_fences_est_lue():
    client = FauxClient('```json\n{"verdict": "PERTINENT", "motif": "entretien de locaux"}\n```')
    assert ap.trier("Marche de services divers", client=client).verdict == PERTINENT


def test_sans_moteur_le_doute_profite_a_l_ao():
    client = FauxClient("", disponible=False)
    v = ap.trier("Marche de services divers", client=client)
    assert v.verdict == PERTINENT
    assert "indisponible" in v.motif


def test_reponse_illisible_le_doute_profite_a_l_ao():
    client = FauxClient("je ne sais pas repondre en JSON")
    v = ap.trier("Marche de services divers", client=client)
    assert v.verdict == PERTINENT
    assert "illisible" in v.motif


def test_panne_du_moteur_ne_casse_pas_la_veille():
    class ClientEnPanne(FauxClient):
        def generer(self, *a, **kw):
            raise RuntimeError("timeout")

    v = ap.trier("Marche de services divers", client=ClientEnPanne(""))
    assert v.verdict == PERTINENT


def test_le_guide_est_injecte_dans_le_prompt():
    client = FauxClient('{"verdict": "PERTINENT", "motif": "ok"}')
    ap.trier("Marche de services divers", guide="CHRUTH nettoie des bureaux en IDF.",
             client=client)
    assert "CHRUTH nettoie des bureaux en IDF." in client.prompts[0]


def test_les_corrections_humaines_sont_injectees_comme_exemples():
    client = FauxClient('{"verdict": "PERTINENT", "motif": "ok"}')
    ap.trier("Marche de services divers",
             corrections=[{"objet": "Elagage des arbres", "verdict": REJETE}],
             client=client)
    assert "Elagage des arbres" in client.prompts[0]
