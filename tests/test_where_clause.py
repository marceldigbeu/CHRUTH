from datetime import date

from ao_collect_boamp import build_where_clause


def test_structure():
    clause = build_where_clause(["nettoyage", "proprete"], 14, today=date(2026, 6, 8))
    assert '"nettoyage"' in clause
    assert '"proprete"' in clause
    assert " OR " in clause
    assert "dateparution >= date'2026-05-25'" in clause


def test_dedup_and_order():
    clause = build_where_clause(["nettoyage", "nettoyage", "menage"], 7, today=date(2026, 6, 8))
    assert clause.count('"nettoyage"') == 1
    assert "date'2026-06-01'" in clause


def test_escapes_double_quotes():
    clause = build_where_clause(['a"b'], 1, today=date(2026, 6, 8))
    assert '"a\\"b"' in clause
