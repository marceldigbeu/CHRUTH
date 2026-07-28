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


def test_les_entites_html_sont_decodees_dans_les_champs_texte():
    """BOAMP renvoie du texte encodé HTML (ex. « Mairie d&#039;ANTONY ») : on le décode."""
    boamp = [_boamp("Entretien &amp; propreté", "CHAUD", "2026-07-24",
                    ach="Mairie d&#039;ANTONY")]
    maxi = {"aos": {"MX-1": _max("Nettoyage &#233;coles", "PERTINENT", "2026-07-24",
                                 ach="Ville d&#039;Y")}}
    aos = asem.collecter_aos_recents(aujourd_hui=AUJ, records_boamp=boamp, etat_maximilien=maxi)
    par_source = {a["source"]: a for a in aos}
    assert par_source["BOAMP"]["acheteur"] == "Mairie d'ANTONY"
    assert par_source["BOAMP"]["objet"] == "Entretien & propreté"
    assert par_source["Maximilien"]["acheteur"] == "Ville d'Y"
    assert par_source["Maximilien"]["objet"] == "Nettoyage écoles"


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
