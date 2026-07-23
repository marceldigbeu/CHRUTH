"""La date de publication vient du listing, pas de l'horloge.

Le listing Maximilien affiche une colonne « Publié le » (bloc .date-min dans
.cons_ref). Le collecteur y ecrivait la date du jour : tout AO paraissait publie
le jour de sa collecte, ce qui fausse le classement par fraicheur et le Top 20
de la semaine (ao_semaine).
"""
from datetime import datetime, timezone

import ao_maximilien_scrape as mx


def _ligne(publie: str = '<div class="date date-min"><span class="day">14</span>'
                        '<span class="month-year">Avril 2026</span></div>') -> str:
    return (
        '<html><body>resultats : 1'
        '<div class="ligne">'
        f'  <div class="col-md-2 top cons_ref">'
        f'    <span class="cons_procedure">MAPA</span>'
        f'    <span class="cons_categorie">Services</span>{publie}'
        f'  </div>'
        '  <div class="objet-line">REF-1 | Nettoyage des locaux</div>'
        '  <a href="/entreprise/consultation/1?orgAcronyme=org1">voir</a>'
        '  <div class="col-md-1 top cons_dateEnd">'
        '    <div class="date clearfix">31 Dec. 2026 12:00</div>'
        '  </div>'
        '</div></body></html>'
    )


def test_le_parsing_capte_la_date_de_publication():
    brut = mx._parse_resultats(_ligne())[0]
    assert brut["date_publication_txt"].strip() == "14 Avril 2026"


def test_l_ao_porte_la_date_de_publication_du_listing():
    ao = mx._to_ao(mx._parse_resultats(_ligne())[0])
    assert ao["date_publication"] == "2026-04-14"


def test_sans_date_affichee_on_retombe_sur_aujourd_hui():
    """Ne jamais laisser la date vide : le tri par fraicheur perdrait l'AO."""
    ao = mx._to_ao(mx._parse_resultats(_ligne(publie=""))[0])
    assert ao["date_publication"] == datetime.now(timezone.utc).strftime("%Y-%m-%d")


def test_la_date_de_cloture_n_est_pas_confondue_avec_la_publication():
    brut = mx._parse_resultats(_ligne())[0]
    assert "31" not in brut["date_publication_txt"]
    assert mx._parse_date_fr(brut["date_limite_txt"]) == "2026-12-31"
