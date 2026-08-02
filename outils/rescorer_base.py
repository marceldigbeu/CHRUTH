"""Recalcule score, priorite et raisons de tous les AO deja en base.

A lancer une fois apres un changement de bareme : les AO collectes avant
gardent sinon leur ancien score, et la base melange deux echelles — ce qui se
voit immediatement dans un tri.

Usage :  python outils/rescorer_base.py [--simuler]
"""
from __future__ import annotations

import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ao_config import AO_DB_PATH  # noqa: E402
from ao_scoring import compute_ao_score  # noqa: E402


def rescorer(db_path: Path, simuler: bool = False) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    lignes = conn.execute("SELECT * FROM ao_records").fetchall()

    maj, changements_priorite = [], Counter()
    for ligne in lignes:
        row = dict(ligne)
        ancien_score = str(row.get("score_chruth") or "")
        ancienne_prio = str(row.get("priorite") or "")
        score, priorite, raisons = compute_ao_score(row)
        if priorite != ancienne_prio:
            changements_priorite[f"{ancienne_prio or '?'} -> {priorite}"] += 1
        maj.append((str(score), priorite, raisons, row["id_ao"]))
        del ancien_score

    if not simuler:
        conn.executemany(
            "UPDATE ao_records SET score_chruth = ?, priorite = ?, raisons_scoring = ? "
            "WHERE id_ao = ?", maj)
        conn.commit()

    scores = [float(m[0]) for m in maj]
    conn.close()
    return {"total": len(maj), "distincts": len(set(scores)),
            "priorites": Counter(m[1] for m in maj),
            "changements": changements_priorite,
            "min": min(scores, default=0), "max": max(scores, default=0)}


CHAMPS_HUMAINS = ("correction_humaine", "traitement", "lu", "notifie_le", "vu_le")


def fusionner_travail_humain(avant: dict, apres: dict) -> dict:
    """Reinjecte dans `apres` ce qu'un humain avait pose dans `avant`.

    Le veilleur ne rescore que les AO qu'il ne connait pas encore : pour forcer
    un recalcul complet on lui presente un etat vide, ce qui ferait disparaitre
    les verdicts corriges a la main, les statuts de suivi et les marques de
    lecture. On les remet ici, et on garde les AO que Maximilien a depublies
    entre-temps plutot que de les perdre.
    """
    for id_ao, ancienne in avant.items():
        nouvelle = apres.get(id_ao)
        if nouvelle is None:
            apres[id_ao] = ancienne          # delistee : mieux vaut la garder
            continue
        for champ in CHAMPS_HUMAINS:
            if ancienne.get(champ) not in (None, "", False):
                nouvelle[champ] = ancienne[champ]
    return apres


def rescorer_etat(etat_path: Path) -> dict:
    """Recalcule le score de tous les AO de l'etat de veille, travail humain intact."""
    import veille_etat
    import veille_depot
    import ao_maximilien_veille

    etat = veille_etat.charger(etat_path)
    avant = dict(etat.get("aos", {}))
    etat["aos"] = {}
    veille_etat.enregistrer(etat, etat_path)

    ao_maximilien_veille.veiller(etat_path=etat_path, envoyer=False)

    etat = veille_etat.charger(etat_path)
    etat["aos"] = fusionner_travail_humain(avant, etat.get("aos", {}))
    veille_etat.enregistrer(etat, etat_path)
    del veille_depot
    return {"avant": len(avant), "apres": len(etat["aos"])}


def main(argv: list[str]) -> int:
    simuler = "--simuler" in argv
    if "--etat" in argv:
        from veille_depot import chemin_local
        r = rescorer_etat(Path(chemin_local()))
        print(f"Etat de veille rescore : {r['avant']} AO avant, {r['apres']} apres")
        return 0
    r = rescorer(Path(AO_DB_PATH), simuler=simuler)
    print("SIMULATION (rien n'est ecrit)" if simuler else "Base mise a jour")
    print(f"  {r['total']} AO rescores, {r['distincts']} valeurs de score distinctes")
    print(f"  score de {r['min']} a {r['max']}")
    print(f"  priorites : {dict(r['priorites'])}")
    if r["changements"]:
        print(f"  changements de priorite : {dict(r['changements'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
