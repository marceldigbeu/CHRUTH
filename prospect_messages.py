"""Mission 3 : génération de brouillons de prospection (email + script d'appel)
par segment (catégorie × priorité) pour les prospects activables CHAUDE/TIEDE.

Hybride : 1 template par segment (IA via llm_client, ou repli déterministe),
puis insertion des variables par prospect. Aucun envoi (brouillons only).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

import signature

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
CACHE_PATH = OUTPUT_DIR / "segments_messages.json"
VARIANTES_CACHE_PATH = OUTPUT_DIR / "segments_variantes.json"
PRIORITES_ACTIVABLES = ("CHAUDE", "TIEDE")

# Placeholder du template -> colonne du dataframe prospect.
CHAMPS = {"denomination": "denomination", "ville": "libelle_commune", "effectif": "effectif_label"}

FICHE_PATH = Path(__file__).resolve().parent / "config_chruth" / "fiche_chruth.md"


def fiche_chruth(path: Path | str = FICHE_PATH) -> str:
    """Profil CHRUTH injecte dans les prompts (style SEKOIA _get_company_profile).

    Lit la fiche, retire les commentaires <!-- ... --> et les titres de section
    restes vides. Renvoie "" si aucune source ne contient de fait rempli
    (=> comportement generique conserve).

    Les reglages partages priment sur le fichier. Sans cela, la fiche saisie
    dans la page Reglages etait ecrite dans les reglages et relue depuis le
    fichier : la remplir depuis l'application n'avait aucun effet, et les
    messages partaient sans coordonnees ni signature.

    Une fiche vide cote reglages n'est pas une decision mais l'etat par defaut :
    on laisse alors le fichier parler, ce qui garde utilisable l'edition directe
    de `config_chruth/fiche_chruth.md`.
    """
    depuis_reglages = ""
    try:
        import reglages
        depuis_reglages = str(reglages.lire().get("fiche_chruth") or "")
    except Exception:  # noqa: BLE001 — hors ligne : le fichier prend le relais
        depuis_reglages = ""

    # On juge la vacuite sur le contenu NETTOYE, pas sur la chaine brute : le
    # gabarit livre fait 787 caracteres de titres et de commentaires, donc
    # « non vide » au sens d'une chaine, alors qu'il ne porte aucun fait. Sans
    # cette distinction, un gabarit stocke dans les reglages empeche a jamais
    # le fichier de servir.
    if _faits_de(depuis_reglages):
        return _faits_de(depuis_reglages)
    try:
        return _faits_de(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return ""


def _faits_de(brut: str) -> str:
    """Contenu utile d'une fiche : sans commentaires, sans section vide."""
    sans_com = re.sub(r"<!--.*?-->", "", brut or "", flags=re.DOTALL)
    lignes = sans_com.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lignes):
        titre = lignes[i].strip()
        if titre.startswith("#"):
            j, contenu = i + 1, []
            while j < len(lignes) and not lignes[j].strip().startswith("#"):
                if lignes[j].strip():
                    contenu.append(lignes[j].strip())
                j += 1
            if contenu:              # on ne garde un titre que s'il a du contenu
                out.append(titre)
                out.extend(contenu)
            i = j
        else:
            if titre:
                out.append(titre)
            i += 1
    return "\n".join(out).strip()


def segments_activables(df: pd.DataFrame, priorites=PRIORITES_ACTIVABLES) -> list[tuple[str, str]]:
    prio = df["priorite"].astype(str).str.upper()
    sous = df[prio.isin(priorites)]
    paires = sous[["categorie_chruth", "priorite"]].astype(str)
    vus, out = set(), []
    for cat, pr in zip(paires["categorie_chruth"], paires["priorite"].str.upper()):
        cle = (cat, pr)
        if cle not in vus:
            vus.add(cle)
            out.append(cle)
    return out


def template_par_defaut(categorie: str, priorite: str, variante: str = "A") -> dict:
    if str(variante).upper() == "B":
        email = (
            "Objet : Des locaux toujours impeccables, sans y penser\n\n"
            "Bonjour,\n\n"
            "Et si l'entretien des locaux de {denomination} à {ville} devenait un "
            "sujet que vous n'avez plus à gérer ?\n\n"
            "CHRUTH prend en charge le nettoyage et la propreté de structures de "
            "votre taille ({effectif}) avec un interlocuteur unique et des "
            "prestations régulières et fiables.\n\n"
            "Quand seriez-vous disponible pour un échange de 15 minutes ?\n\n"
            "Cordialement,\nL'équipe CHRUTH"
        )
        script = (
            "Bonjour, CHRUTH à l'appareil. Nous aidons des structures comme "
            "{denomination} à {ville} ({effectif}) à garder des locaux impeccables "
            "sans avoir à s'en occuper. Puis-je échanger avec la personne en charge "
            "de l'entretien des locaux ?"
        )
        return {"email": email, "script": script}
    accroche = ("Je me permets de vous contacter directement"
                if str(priorite).upper() == "CHAUDE"
                else "Je me permets de vous écrire")
    email = (
        "Objet : Entretien et propreté de vos locaux\n\n"
        "Bonjour,\n\n"
        f"{accroche} au sujet de l'entretien des locaux de {{denomination}} "
        "à {ville}.\n\n"
        "CHRUTH accompagne les structures comme la vôtre (effectif {effectif}) sur le "
        "nettoyage, la propreté et l'entretien régulier de leurs espaces, avec des "
        "prestations adaptées à votre activité.\n\n"
        "Seriez-vous disponible pour un échange rapide afin d'évaluer vos besoins ?\n\n"
        "Cordialement,\nL'équipe CHRUTH"
    )
    script = (
        "Bonjour, je vous appelle de la part de CHRUTH, spécialiste de la propreté et "
        "de l'entretien des locaux. Je contacte {denomination} à {ville} car nous "
        "accompagnons des structures de votre taille ({effectif}) sur l'entretien de "
        "leurs espaces. Pourrais-je échanger avec la personne en charge des services "
        "généraux ou des locaux ?"
    )
    return {"email": email, "script": script}


def rendre(texte: str, row, fiche: str | None = None) -> str:
    """Substitue les placeholders puis appose la signature CHRUTH.

    `fiche=None` charge la fiche du projet ; passer `""` desactive la signature
    (utile en test et pour les usages qui composent leur propre pied de message).
    """
    out = str(texte)
    for ph, col in CHAMPS.items():
        val = row.get(col)
        val = "" if val is None or (isinstance(val, float) and pd.isna(val)) else str(val)
        out = out.replace("{" + ph + "}", val)
    if fiche is None:
        fiche = fiche_chruth()
    return signature.apposer(out, fiche)


_PLACEHOLDERS = ("{denomination}", "{ville}", "{effectif}")


def _template_valide(data: dict | None) -> bool:
    """Un template est exploitable si {denomination} apparaît quelque part (email ou
    script, pour personnaliser la société) ET si l'email contient au moins un
    placeholder (sinon l'email n'est pas personnalisé du tout)."""
    if not data:
        return False
    email, script = data.get("email", ""), data.get("script", "")
    if "{denomination}" not in (email + " " + script):
        return False
    return any(ph in email for ph in _PLACEHOLDERS)


def _cle(categorie: str, priorite: str) -> str:
    return f"{categorie}|{priorite}"


def cle_var(categorie: str, priorite: str, variante: str) -> str:
    return f"{categorie}|{priorite}|{variante}"


def prompt_segment(categorie: str, priorite: str) -> tuple[str, str]:
    # Prompt valide dans CHRUTH_Prompt_Playground.ipynb (style SEKOIA :
    # role expert + variables obligatoires + garde-fous anti-hallucination).
    system = (
        "Tu es un expert en prospection commerciale B2B pour CHRUTH, societe "
        "francaise specialisee dans le nettoyage et la proprete des locaux. "
        "Tu ecris un francais professionnel, clair et concis. Tu reponds "
        'UNIQUEMENT par un objet JSON valide {"email": "...", "script": "..."}, '
        "sans aucun texte autour."
    )
    prompt = (
        "Genere un email de prospection et un script d'appel telephonique pour ce segment.\n\n"
        f"SEGMENT : categorie={categorie}, priorite={priorite}\n\n"
        "VARIABLES OBLIGATOIRES (a ecrire TEXTUELLEMENT, avec les accolades, sans les remplacer) :\n"
        "- L'EMAIL doit contenir {denomination} (ex: commencer par \"A l'attention de "
        "{denomination},\") ET {ville}.\n"
        "- Le SCRIPT doit contenir {denomination} ET {ville}.\n"
        "- Utilise aussi {effectif} si pertinent.\n\n"
        "CONSIGNES DE GENERATION :\n"
        "- Adapte l'accroche et les arguments au SECTEUR (ex: cabinet de sante => hygiene/"
        "desinfection ; bureaux => espaces de travail ; commerce => surfaces clients/vitrines).\n"
        "- Email : un objet court + un corps de 90 a 130 mots, signe \"L'equipe CHRUTH\".\n"
        "- Script d'appel : 3 a 5 phrases, ton oral naturel, finissant par une demande de RDV.\n\n"
        "GARDE-FOUS (IMPORTANT) :\n"
        "- N'invente AUCUNE reference client, certification, prix ni chiffre.\n"
        "- Reste credible et factuel : CHRUTH = nettoyage / proprete / entretien des locaux.\n"
        "- Pas de promesses exagerees.\n\n"
        'FORMAT : un seul objet JSON {"email": "...", "script": "..."}.'
    )
    return system, prompt


def _objets_json(texte: str) -> list[str]:
    """Extrait toutes les sous-chaines {...} a accolades equilibrees (ignore les
    fences markdown). Gere le cas des modeles qui sortent plusieurs blocs JSON."""
    objs, depth, start = [], 0, None
    for i, ch in enumerate(texte):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                objs.append(texte[start:i + 1])
                start = None
    return objs


def _aplatir(v) -> str:
    """Aplatit une valeur en texte lisible : si le modele renvoie un objet/liste
    (ex. script = {intro:..., demande:...}) au lieu d'une chaine, on joint les
    valeurs ligne par ligne plutot que d'afficher un repr de dict."""
    if isinstance(v, dict):
        return "\n".join(_aplatir(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return "\n".join(_aplatir(x) for x in v)
    return str(v) if v is not None else ""


def _parser_reponse(texte: str) -> dict | None:
    if not texte:
        return None
    # strict=False : tolere sauts de ligne/tabs bruts dans les chaines (petits modeles).
    # On fusionne les cles de tous les objets JSON trouves (email et script peuvent
    # arriver dans deux blocs distincts).
    merge: dict = {}
    for blob in _objets_json(texte):
        try:
            data = json.loads(blob, strict=False)
        except Exception:
            continue
        if isinstance(data, dict):
            merge.update(data)
    email, script = _aplatir(merge.get("email")), _aplatir(merge.get("script"))
    if not email.strip() or not script.strip():
        return None
    return {"email": email, "script": script}


def _charger_cache(cache_path: Path) -> dict:
    try:
        return json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sauver_cache(cache: dict, cache_path: Path) -> None:
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    Path(cache_path).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def generer_templates(segments, refresh: bool = False, cache_path: Path = CACHE_PATH,
                      client=None) -> dict:
    if client is None:
        import llm_client as client  # backend reel par defaut
    cache = {} if refresh else _charger_cache(cache_path)
    try:
        dispo = client.llm_disponible()
    except Exception:
        dispo = False
    for cat, prio in segments:
        cle = _cle(cat, prio)
        if cle in cache:
            continue
        data = None
        if dispo:
            try:
                system, prompt = prompt_segment(cat, prio)
                # timeout large : modele CPU a froid (chargement + inference) > 120s.
                data = _parser_reponse(client.generer(prompt, system, timeout=300))
                if not _template_valide(data):
                    data = None  # template non personnalisable => repli
            except Exception:
                data = None
        if data:
            cache[cle] = {**data, "source": "ia", "categorie": cat, "priorite": prio}
        else:
            d = template_par_defaut(cat, prio)
            cache[cle] = {**d, "source": "defaut", "categorie": cat, "priorite": prio}
    _sauver_cache(cache, cache_path)
    return cache


def appliquer_sur(df: pd.DataFrame, templates: dict) -> pd.DataFrame:
    """Ajoute les colonnes brouillon_email/brouillon_script a un dataframe
    (typiquement un sous-ensemble : CHAUDE, Top_Cibles). Lignes non activables -> vide."""
    df = df.copy()
    df["brouillon_email"] = ""
    df["brouillon_script"] = ""
    if df.empty:
        return df
    prio = df["priorite"].astype(str).str.upper()
    cat = df["categorie_chruth"].astype(str)
    for idx in df.index:
        tpl = templates.get(_cle(cat[idx], prio[idx]))
        if tpl is None:
            continue  # FROIDE / segment non activable -> vide
        df.at[idx, "brouillon_email"] = rendre(tpl["email"], df.loc[idx])
        df.at[idx, "brouillon_script"] = rendre(tpl["script"], df.loc[idx])
    return df


def table_templates(templates: dict) -> pd.DataFrame:
    return pd.DataFrame([
        {"categorie": v["categorie"], "priorite": v["priorite"],
         "source": v["source"], "email": v["email"], "script": v["script"]}
        for v in templates.values()
    ], columns=["categorie", "priorite", "source", "email", "script"])


def generer_pour_df(df: pd.DataFrame, refresh: bool = False, cache_path: Path = CACHE_PATH,
                    client=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    segments = segments_activables(df)
    templates = generer_templates(segments, refresh=refresh, cache_path=cache_path, client=client)
    return appliquer_sur(df, templates), table_templates(templates)


def generer_variantes(segments, variantes: tuple[str, ...] = ("A", "B"),
                      refresh: bool = False, cache_path: Path = VARIANTES_CACHE_PATH,
                      client=None, utiliser_ia: bool = True) -> dict:
    """Comme generer_templates mais produit N variantes par segment, keyees
    categorie|priorite|variante. Sert le test A/B (Mission 3 - perf).

    utiliser_ia=True (defaut) : tente un appel LLM via client (ou llm_client si None).
    utiliser_ia=False : utilise uniquement les templates deterministes A/B ; aucun
        appel LLM ni import de llm_client — chemin rapide et garanti distinct A != B.
    """
    if utiliser_ia:
        if client is None:
            import llm_client as client
        try:
            dispo = client.llm_disponible()
        except Exception:
            dispo = False
    else:
        dispo = False
    cache = {} if refresh else _charger_cache(cache_path)
    for cat, prio in segments:
        for var in variantes:
            cle = cle_var(cat, prio, var)
            if cle in cache:
                continue
            data = None
            if dispo:
                try:
                    system, prompt = prompt_segment(cat, prio)
                    data = _parser_reponse(client.generer(prompt, system, timeout=300))
                    if not _template_valide(data):
                        data = None
                except Exception:
                    data = None
            if data:
                cache[cle] = {**data, "source": "ia", "categorie": cat,
                              "priorite": prio, "variante": var}
            else:
                d = template_par_defaut(cat, prio, var)
                cache[cle] = {**d, "source": "defaut", "categorie": cat,
                              "priorite": prio, "variante": var}
    _sauver_cache(cache, cache_path)
    return cache
