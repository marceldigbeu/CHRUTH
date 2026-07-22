import json
from datetime import datetime

import pytest

import ao_alertes
from ao_db import upsert_records, connect


def _seed(db_path, records):
    upsert_records(records, db_path=db_path)


def _ao(id_ao, priorite, **extra):
    row = {
        "id_ao": id_ao,
        "objet": f"Nettoyage {id_ao}",
        "acheteur": "Ville de Test",
        "secteur": "Mairie",
        "categorie": "Batiments",
        "ville": "Paris",
        "date_publication": "2026-06-14",
        "date_limite": "2099-01-01",
        "budget_annuel_eur": "40000",
        "budget_estime_eur": "40000",
        "url_dce": "https://dce.example/" + id_ao,
        "url_avis": "https://boamp.example/" + id_ao,
        "priorite": priorite,
        "score_chruth": "70",
    }
    row.update(extra)
    return row


@pytest.fixture
def db(tmp_path):
    return tmp_path / "ao.sqlite"


def test_selection_non_alertes(db):
    _seed(db, [_ao("A", "CHAUD"), _ao("B", "TIEDE"), _ao("C", "FROID")])
    ids = {r["id_ao"] for r in ao_alertes.nouveaux_ao_a_alerter(db)}
    assert ids == {"A", "B"}


def test_pas_envoi_si_vide(db, monkeypatch):
    _seed(db, [_ao("C", "FROID")])
    called = {"n": 0}
    monkeypatch.setattr(ao_alertes, "envoyer_email", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    monkeypatch.setattr(ao_alertes, "charger_config_smtp", lambda: {"smtp_user": "u", "smtp_password": "p", "destinataire": "d", "host": "h", "port": 587})
    n = ao_alertes.envoyer_alertes(db_path=db)
    assert n == 0
    assert called["n"] == 0


def test_envoi_puis_marquage_et_idempotence(db, monkeypatch):
    _seed(db, [_ao("A", "CHAUD"), _ao("B", "TIEDE")])
    sent = []
    monkeypatch.setattr(ao_alertes, "envoyer_email", lambda sujet, html, texte, cfg: sent.append(sujet))
    monkeypatch.setattr(ao_alertes, "charger_config_smtp", lambda: {"smtp_user": "u", "smtp_password": "p", "destinataire": "d", "host": "h", "port": 587})
    n1 = ao_alertes.envoyer_alertes(db_path=db, now=datetime(2026, 6, 14, 9, 0))
    assert n1 == 2
    assert len(sent) == 1
    with connect(db) as conn:
        marques = [r[0] for r in conn.execute("SELECT alerte_envoyee FROM ao_records WHERE id_ao IN ('A','B')")]
    assert all(m for m in marques)
    n2 = ao_alertes.envoyer_alertes(db_path=db, now=datetime(2026, 6, 14, 9, 5))
    assert n2 == 0
    assert len(sent) == 1


def test_recollecte_preserve_le_drapeau(db, monkeypatch):
    # Reproduit le cycle reel : collecte -> alerte -> RE-collecte (meme AO) -> alerte.
    # Le drapeau alerte_envoyee doit survivre a l'upsert pour ne pas re-alerter.
    _seed(db, [_ao("A", "CHAUD")])
    monkeypatch.setattr(ao_alertes, "envoyer_email", lambda *a, **k: None)
    monkeypatch.setattr(ao_alertes, "charger_config_smtp", lambda: {"smtp_user": "u", "smtp_password": "p", "destinataire": "d", "host": "h", "port": 587})
    assert ao_alertes.envoyer_alertes(db_path=db, now=datetime(2026, 6, 14, 9, 0)) == 1
    _seed(db, [_ao("A", "CHAUD")])  # BOAMP renvoie le meme AO dans la fenetre de lookback
    assert ao_alertes.envoyer_alertes(db_path=db, now=datetime(2026, 6, 14, 14, 0)) == 0


def test_envoyer_email_starttls_avant_login(monkeypatch):
    # Exerce le vrai envoyer_email avec smtplib.SMTP mocke (jamais de reseau).
    calls = []

    class FakeSMTP:
        def __init__(self, host, port):
            calls.append(("init", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login", user, password))

        def send_message(self, msg):
            calls.append(("send", msg["To"], msg["Bcc"], msg["Subject"]))

    monkeypatch.setattr(ao_alertes, "SMTP", FakeSMTP)
    cfg = {"smtp_user": "u@x", "smtp_password": "pw",
           "destinataires": ["a@chruth.fr", "b@chruth.fr"], "host": "smtp.test", "port": 587}
    ao_alertes.envoyer_email("Sujet", "<p>hi</p>", "hi", cfg)
    assert [c[0] for c in calls] == ["init", "starttls", "login", "send"]
    assert ("login", "u@x", "pw") in calls
    # Tous les destinataires en Cci (sans se voir), expediteur en To.
    send = [c for c in calls if c[0] == "send"][0]
    assert send[1] == "u@x"
    assert "a@chruth.fr" in send[2] and "b@chruth.fr" in send[2]


def test_charger_destinataires_fichier(tmp_path, monkeypatch):
    f = tmp_path / "destinataires.txt"
    f.write_text("# liste\na@chruth.fr\n\nb@chruth.fr\na@chruth.fr\n", encoding="utf-8")
    monkeypatch.setattr(ao_alertes, "ALERTE_DESTINATAIRES_FILE", f)
    dests = ao_alertes.charger_destinataires(secrets={})
    assert dests == ["a@chruth.fr", "b@chruth.fr"]  # commentaire/vide ignores + dedup


def test_charger_destinataires_fallback_secret(tmp_path, monkeypatch):
    monkeypatch.setattr(ao_alertes, "ALERTE_DESTINATAIRES_FILE", tmp_path / "absent.txt")
    monkeypatch.delenv("CHRUTH_ALERTE_DEST", raising=False)
    dests = ao_alertes.charger_destinataires(secrets={"destinataire": "x@chruth.fr, y@chruth.fr"})
    assert dests == ["x@chruth.fr", "y@chruth.fr"]


def test_echec_smtp_pas_de_marquage(db, monkeypatch):
    _seed(db, [_ao("A", "CHAUD")])
    def boom(*a, **k):
        raise RuntimeError("smtp down")
    monkeypatch.setattr(ao_alertes, "envoyer_email", boom)
    monkeypatch.setattr(ao_alertes, "charger_config_smtp", lambda: {"smtp_user": "u", "smtp_password": "p", "destinataire": "d", "host": "h", "port": 587})
    with pytest.raises(RuntimeError):
        ao_alertes.envoyer_alertes(db_path=db)
    with connect(db) as conn:
        m = conn.execute("SELECT alerte_envoyee FROM ao_records WHERE id_ao='A'").fetchone()[0]
    assert not m


def test_construire_email(db):
    records = [dict(_ao("A", "CHAUD"))]
    sujet, html, texte = ao_alertes.construire_email(records, datetime(2026, 6, 14, 9, 0))
    assert "1" in sujet and "matin" in sujet
    assert "https://dce.example/A" in html
    assert "Nettoyage A" in html
    assert texte.strip() != ""


def test_config_incomplete(tmp_path, monkeypatch):
    monkeypatch.delenv("CHRUTH_SMTP_USER", raising=False)
    monkeypatch.delenv("CHRUTH_SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("CHRUTH_ALERTE_DEST", raising=False)
    monkeypatch.setattr(ao_alertes, "ALERTE_SECRETS_FILE", tmp_path / "absent.json")
    with pytest.raises(ValueError):
        ao_alertes.charger_config_smtp()
