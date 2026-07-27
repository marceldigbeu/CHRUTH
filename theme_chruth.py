"""Theme visuel partage par toutes les pages de la plateforme CHRUTH."""
from __future__ import annotations

import streamlit as st

CLE_MODE_NUIT = "chruth_mode_nuit"

PALETTES = {
    "jour": {
        "fond": "#F5F8FA",
        "surface": "#FFFFFF",
        "sidebar": "#EDF4F3",
        "texte": "#17212B",
        "secondaire": "#586674",
        "bordure": "#D6E1E5",
        "champ": "#FFFFFF",
        "accent": "#0F766E",
        "ombre": "0 8px 24px rgba(20, 50, 60, 0.07)",
    },
    "nuit": {
        "fond": "#08111F",
        "surface": "#101C2E",
        "sidebar": "#0C1727",
        "texte": "#E7EEF7",
        "secondaire": "#A7B5C7",
        "bordure": "#293B52",
        "champ": "#15243A",
        "accent": "#45D0BE",
        "ombre": "0 10px 28px rgba(0, 0, 0, 0.28)",
    },
}


def _nuit_par_defaut() -> bool:
    """Suit le navigateur au premier affichage, puis laisse l'utilisateur choisir."""
    try:
        return st.context.theme.type == "dark"
    except Exception:  # AppTest et anciennes versions de Streamlit
        return False


def css_theme(nuit: bool) -> str:
    """CSS de la palette active, garde dans une fonction testable sans navigateur."""
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
    }}

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        background-color: var(--chruth-fond);
        color: var(--chruth-texte);
    }}

    [data-testid="stHeader"] {{
        background-color: color-mix(in srgb, var(--chruth-fond) 92%, transparent);
    }}

    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"] {{
        background-color: var(--chruth-sidebar);
        color: var(--chruth-texte);
    }}

    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stMetric"],
    [data-testid="stExpander"] {{
        background-color: var(--chruth-surface);
        border-color: var(--chruth-bordure) !important;
        box-shadow: {p["ombre"]};
    }}

    .stApp h1, .stApp h2, .stApp h3,
    .stApp p, .stApp label,
    [data-testid="stMarkdownContainer"],
    [data-testid="stCaptionContainer"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {{
        color: var(--chruth-texte);
    }}

    [data-testid="stCaptionContainer"],
    [data-testid="stWidgetLabel"] p {{
        color: var(--chruth-secondaire);
    }}

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div,
    textarea,
    input {{
        background-color: var(--chruth-champ) !important;
        border-color: var(--chruth-bordure) !important;
        color: var(--chruth-texte) !important;
    }}

    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    [role="listbox"] {{
        background-color: var(--chruth-surface) !important;
        color: var(--chruth-texte) !important;
    }}

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {{
        border: 1px solid var(--chruth-bordure);
        border-radius: 0.6rem;
        overflow: hidden;
    }}

    .stButton > button,
    .stFormSubmitButton > button {{
        background-color: var(--chruth-surface);
        border-color: var(--chruth-bordure);
        color: var(--chruth-texte);
    }}

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {{
        border-color: var(--chruth-accent);
        color: var(--chruth-accent);
    }}

    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {{
        background-color: var(--chruth-accent);
        border-color: var(--chruth-accent);
    }}

    [data-testid="stCheckbox"] label > div:first-child {{
        background-color: var(--chruth-bordure) !important;
    }}

    [data-testid="stCheckbox"] label:has(input[aria-checked="true"]) > div:first-child {{
        background-color: var(--chruth-accent) !important;
    }}

    hr {{
        border-color: var(--chruth-bordure) !important;
    }}
    </style>
    """


def appliquer() -> bool:
    """Affiche le selecteur commun et applique la palette. Renvoie le mode actif."""
    if CLE_MODE_NUIT not in st.session_state:
        st.session_state[CLE_MODE_NUIT] = _nuit_par_defaut()

    with st.sidebar:
        st.subheader("Affichage")
        nuit = st.toggle("Mode nuit", key=CLE_MODE_NUIT)
        st.caption("Palette sombre" if nuit else "Palette claire")
        st.divider()

    st.markdown(css_theme(nuit), unsafe_allow_html=True)
    return nuit
