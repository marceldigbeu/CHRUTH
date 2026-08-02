"""Thème visuel sobre et fonctionnel de la plateforme CHRUTH."""
from __future__ import annotations

import streamlit as st

CLE_MODE_NUIT = "chruth_mode_nuit"

PALETTES = {
    "jour": {
        "fond": "#F5F7F8",
        "surface": "#FFFFFF",
        "sidebar": "#EEF3F3",
        "texte": "#17242D",
        "secondaire": "#5E6B73",
        "bordure": "#D6DFE2",
        "champ": "#FFFFFF",
        "accent": "#08766D",
        "accent_fort": "#075B55",
        "bleu": "#246B9E",
        "orange": "#B66B12",
        "rouge": "#B34A3C",
        "vert": "#147A55",
        "ombre": "0 2px 10px rgba(28, 54, 62, 0.07)",
    },
    "nuit": {
        "fond": "#0D171E",
        "surface": "#15242D",
        "sidebar": "#111F27",
        "texte": "#E5ECEF",
        "secondaire": "#A8B5BC",
        "bordure": "#31434D",
        "champ": "#182A34",
        "accent": "#4BC8B9",
        "accent_fort": "#79D8CD",
        "bleu": "#72B5E3",
        "orange": "#E9A74F",
        "rouge": "#EF8B7D",
        "vert": "#63C89E",
        "ombre": "0 2px 12px rgba(0, 0, 0, 0.22)",
    },
}


def _nuit_par_defaut() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:  # AppTest et anciennes versions de Streamlit
        return False


def css_theme(nuit: bool) -> str:
    """Renvoie la feuille de style de la palette active."""
    p = PALETTES["nuit" if nuit else "jour"]
    return f"""
    <style>
    :root {{
        --chruth-fond: {p["fond"]};
        --chruth-surface: {p["surface"]};
        --chruth-sidebar: {p["sidebar"]};
        --chruth-texte: {p["texte"]};
        --chruth-secondaire: {p["secondaire"]};
        --chruth-bordure: {p["bordure"]};
        --chruth-champ: {p["champ"]};
        --chruth-accent: {p["accent"]};
        --chruth-accent-fort: {p["accent_fort"]};
        --chruth-bleu: {p["bleu"]};
        --chruth-orange: {p["orange"]};
        --chruth-rouge: {p["rouge"]};
        --chruth-vert: {p["vert"]};
    }}

    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background: var(--chruth-fond);
        color: var(--chruth-texte);
    }}
    [data-testid="stMainBlockContainer"] {{
        max-width: 1440px;
        padding-top: 2rem;
        padding-bottom: 3.5rem;
    }}
    [data-testid="stHeader"] {{
        background-color: color-mix(in srgb, var(--chruth-fond) 94%, transparent);
    }}

    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
        background: var(--chruth-sidebar);
        color: var(--chruth-texte);
    }}
    [data-testid="stSidebarContent"] {{
        border-right: 1px solid var(--chruth-bordure);
    }}
    .chruth-brand {{
        padding: .72rem .8rem;
        margin: 0 0 .7rem;
        border-left: 3px solid var(--chruth-accent);
        background: var(--chruth-surface);
        box-shadow: {p["ombre"]};
    }}
    .chruth-brand strong {{
        display: block;
        color: var(--chruth-texte);
        font-size: 1rem;
        letter-spacing: .08em;
    }}
    .chruth-brand span {{
        display: block;
        margin-top: .18rem;
        color: var(--chruth-secondaire);
        font-size: .73rem;
        line-height: 1.35;
    }}

    [data-testid="stSidebarNav"] a {{
        border-radius: .4rem;
        margin: .08rem 0;
        transition: background-color 120ms ease, color 120ms ease;
    }}
    [data-testid="stSidebarNav"] a:hover {{
        background: color-mix(in srgb, var(--chruth-accent) 9%, transparent);
        color: var(--chruth-accent-fort);
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: var(--chruth-accent);
        color: white !important;
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] * {{
        color: white !important;
        font-weight: 650;
    }}

    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stMetric"],
    [data-testid="stExpander"] {{
        background: var(--chruth-surface);
        border: 1px solid var(--chruth-bordure) !important;
        border-radius: .55rem !important;
        box-shadow: {p["ombre"]};
    }}
    [data-testid="stMetric"] {{
        min-height: 6.7rem;
        padding: .9rem 1rem;
        border-top: 3px solid var(--chruth-accent) !important;
    }}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] {{
        border-top-color: var(--chruth-orange) !important;
    }}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] {{
        border-top-color: var(--chruth-bleu) !important;
    }}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] {{
        border-top-color: var(--chruth-rouge) !important;
    }}
    [data-testid="stMetricValue"] {{
        color: var(--chruth-texte) !important;
        font-weight: 720;
        letter-spacing: -.025em;
    }}

    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label,
    [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
        color: var(--chruth-texte);
    }}
    .stApp h1 {{
        font-weight: 740;
        letter-spacing: -.035em;
        line-height: 1.08;
    }}
    .stApp h2, .stApp h3 {{ letter-spacing: -.018em; }}
    [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] p {{
        color: var(--chruth-secondaire);
    }}

    .chruth-kicker {{
        width: fit-content;
        margin-bottom: .45rem;
        padding-left: .55rem;
        border-left: 3px solid var(--chruth-accent);
        color: var(--chruth-accent-fort);
        font-size: .73rem;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
    }}
    .chruth-badge {{
        display: inline-block;
        padding: .18rem .45rem;
        margin-bottom: .4rem;
        border: 1px solid currentColor;
        border-radius: .3rem;
        font-size: .72rem;
        font-weight: 650;
    }}
    .chruth-badge--red {{ color: var(--chruth-rouge); }}
    .chruth-badge--orange {{ color: var(--chruth-orange); }}
    .chruth-badge--green {{ color: var(--chruth-vert); }}

    .chruth-status-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .75rem;
        margin: .2rem 0 .5rem;
    }}
    .chruth-status {{
        padding: .8rem .9rem;
        border: 1px solid var(--chruth-bordure);
        border-left: 3px solid var(--chruth-bleu);
        border-radius: .45rem;
        background: var(--chruth-surface);
        box-shadow: {p["ombre"]};
    }}
    .chruth-status span {{ display: block; color: var(--chruth-secondaire); font-size: .75rem; }}
    .chruth-status strong {{ display: block; margin-top: .2rem; color: var(--chruth-texte); font-size: .98rem; }}
    .chruth-status strong.on {{ color: var(--chruth-vert); }}
    .chruth-status strong.off {{ color: var(--chruth-secondaire); }}

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div,
    textarea, input {{
        background: var(--chruth-champ) !important;
        border-color: var(--chruth-bordure) !important;
        color: var(--chruth-texte) !important;
    }}
    div[data-baseweb="popover"], div[data-baseweb="menu"], [role="listbox"] {{
        background: var(--chruth-surface) !important;
        color: var(--chruth-texte) !important;
    }}
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        border: 1px solid var(--chruth-bordure);
        border-radius: .5rem;
        overflow: hidden;
    }}

    .stButton > button, .stFormSubmitButton > button {{
        min-height: 2.5rem;
        border-radius: .45rem;
        background: var(--chruth-surface);
        border-color: var(--chruth-bordure);
        color: var(--chruth-texte);
        font-weight: 620;
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{
        border-color: var(--chruth-accent);
        color: var(--chruth-accent-fort);
    }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
        background: var(--chruth-accent);
        border-color: var(--chruth-accent);
        color: white !important;
    }}
    [data-testid="stPageLink"] a {{ color: var(--chruth-accent-fort); font-weight: 650; }}
    [data-baseweb="tab-list"] {{ border-bottom: 1px solid var(--chruth-bordure); }}
    [aria-selected="true"][data-baseweb="tab"] {{ color: var(--chruth-accent-fort); font-weight: 650; }}
    [data-testid="stAlert"] {{ border-radius: .45rem; border-width: 1px; }}
    [data-testid="stCheckbox"] label > div:first-child {{ background: var(--chruth-bordure) !important; }}
    [data-testid="stCheckbox"] label:has(input[aria-checked="true"]) > div:first-child {{ background: var(--chruth-accent) !important; }}
    hr {{ border-color: var(--chruth-bordure) !important; }}

    @media (max-width: 760px) {{
        [data-testid="stMainBlockContainer"] {{ padding: 1.2rem 1rem 3rem; }}
        .stApp h1 {{ font-size: 2rem; }}
        .chruth-status-grid {{ grid-template-columns: 1fr; }}
        [data-testid="stMetric"] {{ min-height: 6rem; }}
    }}
    </style>
    """


def appliquer() -> bool:
    if CLE_MODE_NUIT not in st.session_state:
        st.session_state[CLE_MODE_NUIT] = _nuit_par_defaut()

    with st.sidebar:
        st.markdown(
            '<div class="chruth-brand"><strong>CHRUTH</strong>'
            '<span>Veille des marchés publics en Île-de-France</span></div>',
            unsafe_allow_html=True,
        )
        nuit = st.toggle("Mode nuit", key=CLE_MODE_NUIT,
                         help="Adapter le contraste à votre écran")
        st.divider()

    st.markdown(css_theme(nuit), unsafe_allow_html=True)
    return nuit
