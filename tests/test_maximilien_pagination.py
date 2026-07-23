"""Pagination de la recherche publique Maximilien.

HTML synthetique : on teste la boucle de pagination, pas le rendu du site.
"""
import ao_maximilien_scrape as mx


def _html(total: int, cids: list[int]) -> str:
    """HTML minimal reproduisant la structure lue par _parse_resultats."""
    lignes = "".join(
        f'<div class="ligne">'
        f'<div class="objet-line">REF{c} | Nettoyage des locaux {c}</div>'
        f'<a href="/entreprise/consultation/{c}?orgAcronyme=org1">voir</a>'
        f'<span class="cons_procedure">MAPA</span>'
        f'<span class="cons_dateEnd">14 Avril 2026 12:00</span>'
        f'</div>'
        for c in cids
    )
    return f"<html><body>resultats : {total} {lignes}</body></html>"


def test_nb_resultats_lit_le_total_annonce():
    assert mx.nb_resultats(_html(14, [1])) == 14


def test_nb_resultats_zero_si_absent():
    assert mx.nb_resultats("<html><body>rien</body></html>") == 0


def test_pages_resultats_parcourt_toutes_les_pages(monkeypatch):
    # 24 resultats annonces pour une taille de page de 20 -> deux pages.
    pages = {1: _html(24, list(range(1, 21))), 2: _html(24, [21, 22, 23, 24])}
    demandees = []

    def faux_rechercher(session, keyword, page=1, page_size=mx.PAGE_SIZE):
        demandees.append(page)
        return pages[page]

    monkeypatch.setattr(mx, "_rechercher", faux_rechercher)
    htmls = list(mx._pages_resultats(None, "nettoyage"))

    assert demandees == [1, 2]
    assert len(htmls) == 2


def test_pages_resultats_borne_au_cap_de_securite(monkeypatch):
    monkeypatch.setattr(mx, "_rechercher",
                        lambda session, keyword, page=1, page_size=mx.PAGE_SIZE: _html(100000, [page]))
    htmls = list(mx._pages_resultats(None, "nettoyage"))
    assert len(htmls) == mx.MAX_PAGES


def test_pages_resultats_une_seule_page_si_peu_de_resultats(monkeypatch):
    monkeypatch.setattr(mx, "_rechercher",
                        lambda session, keyword, page=1, page_size=mx.PAGE_SIZE: _html(3, [1, 2, 3]))
    assert len(list(mx._pages_resultats(None, "nettoyage"))) == 1
