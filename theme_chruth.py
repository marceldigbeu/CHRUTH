"""Thème visuel partagé par toutes les pages de la plateforme CHRUTH."""
from __future__ import annotations

import streamlit as st

CLE_MODE_NUIT = "chruth_mode_nuit"

PALETTES = {
    "jour": {
        "fond": "#F3F7FA", "surface": "#FFFFFF", "surface_alt": "#F8FBFC",
        "sidebar": "#EAF5F3", "texte": "#13232F", "secondaire": "#5B6B78",
        "bordure": "#D7E4E7", "champ": "#FFFFFF", "accent": "#087F73",
        "accent_fort": "#075E57", "bleu": "#2878B8", "corail": "#E96B4C",
        "or": "#E5A82A", "succes": "#168A62",
        "ombre": "0 12px 34px rgba(31, 69, 78, 0.10)",
        "halo": "rgba(8, 127, 115, 0.11)",
    },
    "nuit": {
        "fond": "#07131D", "surface": "#102330", "surface_alt": "#142A38",
        "sidebar": "#0B1D29", "texte": "#E7EEF7", "secondaire": "#A8BBC8",
        "bordure": "#294452", "champ": "#142A38", "accent": "#45D6C2",
        "accent_fort": "#8DE9DD", "bleu": "#69B7F0", "corail": "#FF8A6E",
        "or": "#F7C55B", "succes": "#53D69D",
        "ombre": "0 14px 38px rgba(0, 0, 0, 0.30)",
        "halo": "rgba(69, 214, 194, 0.12)",
    },
}


def _nuit_par_defaut() -> bool:
    """Suit le navigateur au premier affichage, puis laisse l'utilisateur choisir."""
    try:
        return st.context.theme.type == "dark"
    except Exception:  # AppTest et anciennes versions de Streamlit
        return False


def css_theme(nuit: bool) -> str:
    """CSS de la palette active, gardé dans une fonction testable sans navigateur."""
    p = PALETTES["nuit" if nuit else "jour"]
    return f"""
    <style>
    :root {{
        --chruth-fond: {p["fond"]}; --chruth-surface: {p["surface"]};
        --chruth-surface-alt: {p["surface_alt"]}; --chruth-sidebar: {p["sidebar"]};
        --chruth-texte: {p["texte"]}; --chruth-secondaire: {p["secondaire"]};
        --chruth-bordure: {p["bordure"]}; --chruth-champ: {p["champ"]};
        --chruth-accent: {p["accent"]}; --chruth-accent-fort: {p["accent_fort"]};
        --chruth-bleu: {p["bleu"]}; --chruth-corail: {p["corail"]};
        --chruth-or: {p["or"]}; --chruth-succes: {p["succes"]};
        --chruth-halo: {p["halo"]}; --chruth-rayon: 1rem;
    }}

    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background: radial-gradient(circle at 92% 3%, var(--chruth-halo), transparent 26rem),
                    radial-gradient(circle at 8% 84%, color-mix(in srgb, var(--chruth-bleu) 8%, transparent), transparent 30rem),
                    var(--chruth-fond);
        color: var(--chruth-texte);
    }}
    [data-testid="stMainBlockContainer"] {{
        max-width: 1480px; padding-top: 2.2rem; padding-bottom: 4rem;
    }}
    [data-testid="stHeader"] {{
        background-color: color-mix(in srgb, var(--chruth-fond) 82%, transparent);
        backdrop-filter: blur(14px);
    }}

    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
        background: linear-gradient(180deg, var(--chruth-sidebar),
                    color-mix(in srgb, var(--chruth-sidebar) 78%, var(--chruth-fond)));
        color: var(--chruth-texte);
    }}
    [data-testid="stSidebarContent"] {{
        border-right: 1px solid var(--chruth-bordure); padding-top: .55rem;
    }}
    .chruth-brand {{
        position: relative; overflow: hidden; padding: 1rem; margin: 0 0 .85rem;
        border: 1px solid color-mix(in srgb, var(--chruth-accent) 24%, var(--chruth-bordure));
        border-radius: 1rem; background: linear-gradient(135deg, var(--chruth-accent), var(--chruth-bleu));
        color: white; box-shadow: 0 12px 28px color-mix(in srgb, var(--chruth-accent) 22%, transparent);
    }}
    .chruth-brand::after {{
        content: ""; position: absolute; width: 7rem; height: 7rem; right: -2.5rem;
        top: -3.5rem; border-radius: 50%; background: rgba(255,255,255,.15);
    }}
    .chruth-brand strong {{ display: block; color: white; font-size: 1.25rem; letter-spacing: .08em; }}
    .chruth-brand span {{ display: block; margin-top: .2rem; color: rgba(255,255,255,.86); font-size: .76rem; line-height: 1.35; }}

    [data-testid="stSidebarNav"] a {{
        border-radius: .72rem; margin: .1rem 0; padding-top: .5rem; padding-bottom: .5rem;
        transition: transform 160ms ease, background-color 160ms ease, color 160ms ease;
    }}
    [data-testid="stSidebarNav"] a:hover {{
        background: color-mix(in srgb, var(--chruth-accent) 12%, transparent);
        color: var(--chruth-accent-fort); transform: translateX(3px);
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: linear-gradient(100deg, var(--chruth-accent), var(--chruth-bleu));
        color: white !important; box-shadow: 0 7px 20px color-mix(in srgb, var(--chruth-accent) 22%, transparent);
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] * {{ color: white !important; font-weight: 650; }}

    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stMetric"], [data-testid="stExpander"] {{
        background-color: var(--chruth-surface); border: 1px solid var(--chruth-bordure) !important;
        border-radius: var(--chruth-rayon) !important; box-shadow: {p["ombre"]};
        transition: box-shadow 180ms ease, border-color 180ms ease;
    }}
    [data-testid="stVerticalBlockBorderWrapper"]:hover, [data-testid="stExpander"]:hover {{
        border-color: color-mix(in srgb, var(--chruth-accent) 44%, var(--chruth-bordure)) !important;
        box-shadow: 0 16px 38px color-mix(in srgb, var(--chruth-accent) 12%, transparent);
    }}
    [data-testid="stMetric"] {{ position: relative; overflow: hidden; min-height: 7.2rem; padding: 1rem 1.1rem; }}
    [data-testid="stMetric"]::before {{
        content: ""; position: absolute; inset: 0 auto 0 0; width: .28rem;
        background: linear-gradient(180deg, var(--chruth-accent), var(--chruth-bleu));
    }}
    [data-testid="stMetric"]::after {{
        content: ""; position: absolute; width: 5.5rem; height: 5.5rem; right: -2.4rem;
        top: -2.8rem; border-radius: 50%; background: var(--chruth-halo);
    }}
    [data-testid="stMetricValue"] {{ color: var(--chruth-accent-fort) !important; font-weight: 760; letter-spacing: -.035em; }}
    [data-testid="stMetricDelta"] {{ border-radius: 999px; padding: .16rem .48rem; background: color-mix(in srgb, var(--chruth-succes) 11%, transparent); }}

    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label,
    [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{ color: var(--chruth-texte); }}
    .stApp h1 {{ font-weight: 780; letter-spacing: -.045em; line-height: 1.04; margin-bottom: .45rem; }}
    .stApp h2, .stApp h3 {{ letter-spacing: -.025em; }}
    [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] p {{ color: var(--chruth-secondaire); }}

    .chruth-kicker {{
        display: inline-flex; align-items: center; gap: .45rem; width: fit-content; margin-bottom: .45rem;
        padding: .32rem .68rem; border-radius: 999px;
        background: color-mix(in srgb, var(--chruth-accent) 12%, var(--chruth-surface));
        color: var(--chruth-accent-fort); font-size: .74rem; font-weight: 760;
        letter-spacing: .09em; text-transform: uppercase;
    }}
    .chruth-kicker::before {{
        content: ""; width: .48rem; height: .48rem; border-radius: 50%; background: var(--chruth-succes);
        box-shadow: 0 0 0 .25rem color-mix(in srgb, var(--chruth-succes) 13%, transparent);
    }}
    .chruth-badge {{ display: inline-flex; padding: .22rem .58rem; margin-bottom: .45rem; border-radius: 999px; font-size: .73rem; font-weight: 720; }}
    .chruth-badge--red {{ background: color-mix(in srgb, var(--chruth-corail) 14%, transparent); color: var(--chruth-corail); }}
    .chruth-badge--orange {{ background: color-mix(in srgb, var(--chruth-or) 16%, transparent); color: var(--chruth-or); }}
    .chruth-badge--green {{ background: color-mix(in srgb, var(--chruth-succes) 14%, transparent); color: var(--chruth-succes); }}

    .chruth-status-grid {{ display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: .9rem; margin: .25rem 0 .55rem; }}
    .chruth-status {{
        padding: .9rem 1rem; border: 1px solid var(--chruth-bordure); border-radius: .9rem;
        background: linear-gradient(145deg, var(--chruth-surface), var(--chruth-surface-alt)); box-shadow: {p["ombre"]};
    }}
    .chruth-status span {{ display: block; color: var(--chruth-secondaire); font-size: .76rem; }}
    .chruth-status strong {{ display: block; margin-top: .25rem; color: var(--chruth-texte); font-size: 1.03rem; }}
    .chruth-status strong.on {{ color: var(--chruth-succes); }} .chruth-status strong.off {{ color: var(--chruth-secondaire); }}

    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div, textarea, input {{
        background-color: var(--chruth-champ) !important; border-color: var(--chruth-bordure) !important;
        color: var(--chruth-texte) !important; border-radius: .72rem !important;
    }}
    div[data-baseweb="popover"], div[data-baseweb="menu"], [role="listbox"] {{
        background-color: var(--chruth-surface) !important; color: var(--chruth-texte) !important;
    }}
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        border: 1px solid var(--chruth-bordure); border-radius: var(--chruth-rayon);
        overflow: hidden; box-shadow: {p["ombre"]};
    }}

    .stButton > button, .stFormSubmitButton > button {{
        background-color: var(--chruth-surface); border-color: var(--chruth-bordure); color: var(--chruth-texte);
        min-height: 2.65rem; border-radius: .78rem; font-weight: 650;
        transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{
        border-color: var(--chruth-accent); color: var(--chruth-accent); transform: translateY(-1px);
        box-shadow: 0 9px 22px color-mix(in srgb, var(--chruth-accent) 13%, transparent);
    }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
        background: linear-gradient(105deg, var(--chruth-accent), var(--chruth-bleu));
        border-color: transparent; color: white !important;
        box-shadow: 0 10px 24px color-mix(in srgb, var(--chruth-accent) 20%, transparent);
    }}
    [data-testid="stPageLink"] a {{ border-radius: .75rem; color: var(--chruth-accent-fort); font-weight: 700; }}
    [data-testid="stPageLink"] a:hover {{ color: var(--chruth-bleu); }}

    [data-baseweb="tab-list"] {{ gap: .35rem; padding: .3rem; border-radius: .9rem; background: color-mix(in srgb, var(--chruth-sidebar) 72%, transparent); }}
    [data-baseweb="tab"] {{ border-radius: .65rem; padding-left: 1rem; padding-right: 1rem; }}
    [aria-selected="true"][data-baseweb="tab"] {{
        background: var(--chruth-surface); color: var(--chruth-accent-fort);
        box-shadow: 0 5px 16px color-mix(in srgb, var(--chruth-accent) 10%, transparent);
    }}
    [data-testid="stAlert"] {{ border-radius: .9rem; border-width: 1px; box-shadow: 0 8px 22px color-mix(in srgb, var(--chruth-accent) 7%, transparent); }}
    [data-testid="stProgress"] > div > div {{ background: linear-gradient(90deg, var(--chruth-accent), var(--chruth-bleu), var(--chruth-corail)); }}
    [data-testid="stCheckbox"] label > div:first-child {{ background-color: var(--chruth-bordure) !important; }}
    [data-testid="stCheckbox"] label:has(input[aria-checked="true"]) > div:first-child {{ background-color: var(--chruth-accent) !important; }}
    hr {{ border-color: var(--chruth-bordure) !important; }}
    * {{ scrollbar-color: color-mix(in srgb, var(--chruth-accent) 45%, var(--chruth-bordure)) transparent; scrollbar-width: thin; }}

    @media (max-width: 760px) {{
        [data-testid="stMainBlockContainer"] {{ padding: 1.2rem 1rem 3rem; }}
        .stApp h1 {{ font-size: 2rem; }} .chruth-status-grid {{ grid-template-columns: 1fr; }}
        [data-testid="stMetric"] {{ min-height: 6.2rem; }}
    }}
    @media (prefers-reduced-motion: no-preference) {{
        [data-testid="stMainBlockContainer"] > div {{ animation: chruth-entree 280ms ease-out both; }}
        @keyframes chruth-entree {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    }}
    </style>
    """


def appliquer() -> bool:
    """Affiche le sélecteur commun et applique la palette. Renvoie le mode actif."""
    if CLE_MODE_NUIT not in st.session_state:
        st.session_state[CLE_MODE_NUIT] = _nuit_par_defaut()

    with st.sidebar:
        st.markdown(
            '<div class="chruth-brand"><strong>CHRUTH</strong>'
            '<span>Veille intelligente · Marchés publics · Île-de-France</span></div>',
            unsafe_allow_html=True,
        )
        nuit = st.toggle("Mode nuit", key=CLE_MODE_NUIT,
                         help="Adapter le contraste à votre écran")
        st.divider()

    st.markdown(css_theme(nuit), unsafe_allow_html=True)
    return nuit
