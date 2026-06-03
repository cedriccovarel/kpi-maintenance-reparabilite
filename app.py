
import io
import re
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)


APP_TITLE = "Prototype KPI maintenance, réparabilité et carbone"


# -----------------------------
# Paramètres et bibliothèque test
# -----------------------------

DOCUMENT_SLOTS = {
    "cctp_dpgf": {
        "label": "1. CCTP / DPGF / descriptif technique",
        "help": "Permet d'identifier les lots, les matériaux, les quantités, les prix unitaires et les choix techniques."
    },
    "fdes_pep": {
        "label": "2. FDES / PEP / fiches environnementales",
        "help": "Permet d'extraire l'impact carbone, la durée de vie de référence et les modules ACV."
    },
    "notices_entretien": {
        "label": "3. Notices d'entretien / maintenance fabricant",
        "help": "Permet d'identifier les conditions d'entretien, la fréquence de maintenance et les pièces remplaçables."
    },
    "doe_gmao": {
        "label": "4. DOE / historique GMAO / exploitation",
        "help": "Permet de comparer les hypothèses avec les interventions réelles, si le bâtiment existe déjà."
    },
    "devis_variantes": {
        "label": "5. Devis / variantes / offres entreprises",
        "help": "Permet de comparer plusieurs solutions sur le coût, le carbone, la durée de vie et la maintenance."
    },
}

# Coefficients simples pour le PER.
# Le but du prototype est de rattacher automatiquement un produit à une famille
# par mots-clés, sans notation manuelle complexe.
PRODUCT_LIBRARY = [
    {
        "famille": "Dalles de sol plombantes / amovibles",
        "keywords": ["dalle plombante", "dalles plombantes", "dalle moquette", "dalles moquette", "pose libre", "plombante"],
        "coef_remplacement": 0.10,
        "commentaire": "Remplacement localisé généralement possible."
    },
    {
        "famille": "Sol souple collé en lés",
        "keywords": ["sol souple", "pvc collé", "lés collés", "lés pvc", "revêtement collé", "linoleum collé", "lino collé"],
        "coef_remplacement": 1.00,
        "commentaire": "Dépose souvent destructive ou remplacement par zone complète."
    },
    {
        "famille": "Faux plafond démontable",
        "keywords": ["faux plafond démontable", "dalles plafond", "plafond démontable", "ossature apparente"],
        "coef_remplacement": 0.10,
        "commentaire": "Accès et remplacement localisé généralement favorables."
    },
    {
        "famille": "Plafond plaque de plâtre",
        "keywords": ["plaque de plâtre", "plafond ba13", "plafond placo", "plafond fixe"],
        "coef_remplacement": 0.50,
        "commentaire": "Réparation partielle possible mais intervention plus lourde."
    },
    {
        "famille": "Bardage fixé mécaniquement",
        "keywords": ["bardage vissé", "bardage fixé", "fixation mécanique", "ossature secondaire", "vissé"],
        "coef_remplacement": 0.25,
        "commentaire": "Remplacement partiel par module généralement envisageable."
    },
    {
        "famille": "Enduit ou revêtement adhérent de façade",
        "keywords": ["enduit", "rpe", "revêtement plastique épais", "ite enduite", "sous-enduit"],
        "coef_remplacement": 0.50,
        "commentaire": "Réparation partielle possible mais homogénéité et reprise souvent sensibles."
    },
    {
        "famille": "Menuiserie avec vitrage remplaçable",
        "keywords": ["vitrage remplaçable", "menuiserie aluminium", "menuiserie bois", "menuiserie pvc", "double vitrage"],
        "coef_remplacement": 0.25,
        "commentaire": "Sous-composants généralement remplaçables si profils standards."
    },
    {
        "famille": "Porte standard",
        "keywords": ["bloc-porte", "porte intérieure", "porte palière", "porte coupe-feu", "huisserie"],
        "coef_remplacement": 0.35,
        "commentaire": "Réparation partielle possible selon quincaillerie, parement, huisserie."
    },
    {
        "famille": "PAC / équipement CVC",
        "keywords": ["pompe à chaleur", "pac", "groupe froid", "vrv", "drv"],
        "coef_remplacement": 0.25,
        "commentaire": "Remplacement de composants souvent possible, à vérifier avec notice fabricant."
    },
    {
        "famille": "CTA / ventilation modulaire",
        "keywords": ["centrale de traitement d'air", "cta", "ventilation double flux", "caisson de ventilation"],
        "coef_remplacement": 0.20,
        "commentaire": "Maintenance par composants généralement possible."
    },
]


# -----------------------------
# Extraction PDF et recherche
# -----------------------------

def extract_pdf_text(uploaded_file) -> str:
    """Extraction texte simple. Les PDF scannés peuvent nécessiter OCR hors prototype."""
    text_chunks = []
    try:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text_chunks.append(page.extract_text() or "")
    except Exception as exc:
        text_chunks.append(f"[ERREUR EXTRACTION PDF: {exc}]")
    return "\n".join(text_chunks)


def normalize_text(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s


def find_first_float(patterns: List[str], text: str) -> Tuple[Optional[float], str]:
    """Retourne la première valeur numérique trouvée avec l'extrait de preuve."""
    for pat in patterns:
        match = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            raw = match.group(1).replace(" ", "").replace(",", ".")
            try:
                value = float(raw)
                start = max(match.start() - 120, 0)
                end = min(match.end() + 120, len(text))
                return value, text[start:end]
            except ValueError:
                pass
    return None, ""


def extract_environmental_values(text: str) -> Dict:
    """Extraction volontairement prudente de valeurs clés."""
    text = normalize_text(text)

    # Durée de vie : formulation variable dans les FDES.
    duree_patterns = [
        r"dur[ée]e de vie de r[ée]f[ée]rence[^0-9]{0,80}([0-9]+(?:[,.][0-9]+)?)\s*ans",
        r"dvr[^0-9]{0,80}([0-9]+(?:[,.][0-9]+)?)\s*ans",
        r"dur[ée]e de vie typique[^0-9]{0,80}([0-9]+(?:[,.][0-9]+)?)\s*ans",
        r"dur[ée]e de vie[^0-9]{0,80}([0-9]+(?:[,.][0-9]+)?)\s*ans",
    ]

    # Impact carbone : on vise le réchauffement climatique / GWP / kg CO2 eq.
    carbone_patterns = [
        r"r[ée]chauffement climatique[^0-9\-]{0,120}([0-9]+(?:[,.][0-9]+)?)\s*kg\s*co2",
        r"gwp[^0-9\-]{0,120}([0-9]+(?:[,.][0-9]+)?)\s*kg\s*co2",
        r"changement climatique[^0-9\-]{0,120}([0-9]+(?:[,.][0-9]+)?)\s*kg\s*co2",
        r"([0-9]+(?:[,.][0-9]+)?)\s*kg\s*co2\s*(?:e|eq|éq)",
    ]

    # Maintenance B2, réparation B3, remplacement B4. Extraction approximative.
    modules = {}
    for module in ["A1-A3", "A4", "A5", "B2", "B3", "B4", "C1", "C2", "C3", "C4", "D"]:
        pat = rf"{re.escape(module)}[^0-9\-]{{0,80}}([\-]?[0-9]+(?:[,.][0-9]+)?)"
        v, ev = find_first_float([pat], text)
        modules[module] = {"value": v, "evidence": ev}

    duree, ev_duree = find_first_float(duree_patterns, text)
    carbone, ev_carbone = find_first_float(carbone_patterns, text)

    return {
        "duree_vie_ans": duree,
        "preuve_duree": ev_duree,
        "carbone_total_kgco2e": carbone,
        "preuve_carbone": ev_carbone,
        "modules": modules,
    }


def extract_cost_values(text: str) -> Dict:
    text = normalize_text(text)
    patterns = [
        r"prix unitaire[^0-9]{0,50}([0-9]+(?:[,.][0-9]+)?)\s*(?:€|eur)",
        r"pu[^0-9]{0,50}([0-9]+(?:[,.][0-9]+)?)\s*(?:€|eur)",
        r"([0-9]+(?:[,.][0-9]+)?)\s*(?:€|eur)\s*/\s*(?:m2|m²|u|ml)",
    ]
    cost, ev = find_first_float(patterns, text)
    return {"cout_unitaire_eur": cost, "preuve_cout": ev}


def detect_products(text: str) -> List[Dict]:
    low = text.lower()
    found = []
    for item in PRODUCT_LIBRARY:
        hits = [kw for kw in item["keywords"] if kw.lower() in low]
        if hits:
            found.append({
                "famille": item["famille"],
                "mots_cles": ", ".join(hits[:5]),
                "coef_remplacement": item["coef_remplacement"],
                "commentaire": item["commentaire"],
            })
    return found


def confidence_label(value) -> str:
    if value is None or value == "":
        return "Non trouvé"
    return "Extrait automatiquement"


# -----------------------------
# Calcul KPI
# -----------------------------

def compute_indicators(row: Dict) -> Dict:
    carbon = row.get("carbone_total_kgco2e")
    life = row.get("duree_vie_ans")
    cost = row.get("cout_unitaire_eur")
    coef = row.get("coef_remplacement")

    ica = None
    if carbon is not None and life not in (None, 0):
        ica = carbon / life

    per_carbone = None
    if carbon is not None and coef is not None:
        per_carbone = carbon * (1 - coef)

    per_eur = None
    if cost is not None and coef is not None:
        per_eur = cost * (1 - coef)

    return {
        "ICA_kgCO2e_par_an": ica,
        "PER_carbone_kgCO2e_evitable": per_carbone,
        "PER_eur_evitable": per_eur,
    }


# -----------------------------
# Rapport PDF
# -----------------------------

def dataframe_to_table_data(df: pd.DataFrame, max_rows: int = 30) -> List[List[str]]:
    if df.empty:
        return [["Aucune donnée exploitable"]]
    small = df.head(max_rows).copy()
    small = small.fillna("")
    data = [list(small.columns)]
    for _, row in small.iterrows():
        data.append([str(x)[:80] for x in row.tolist()])
    return data


def make_pdf_report(summary: Dict, df: pd.DataFrame, missing_docs: List[str]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.2*cm,
        leftMargin=1.2*cm,
        topMargin=1.2*cm,
        bottomMargin=1.2*cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    ))
    story = []

    story.append(Paragraph("Rapport prototype - KPI maintenance, réparabilité et carbone", styles["Title"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["BodyText"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("1. Documents analysés", styles["Heading2"]))
    for slot, info in DOCUMENT_SLOTS.items():
        status = summary.get("docs", {}).get(slot, {}).get("status", "Absent")
        names = summary.get("docs", {}).get(slot, {}).get("files", [])
        text = f"<b>{info['label']}</b> : {status}"
        if names:
            text += " - " + ", ".join(names)
        story.append(Paragraph(text, styles["Small"]))
    story.append(Spacer(1, 0.3*cm))

    if missing_docs:
        story.append(Paragraph("Documents manquants ou non fournis", styles["Heading3"]))
        story.append(Paragraph(", ".join(missing_docs), styles["Small"]))
        story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("2. Indicateurs", styles["Heading2"]))
    explanation = (
        "ICA = impact carbone annualisé, exprimé en kgCO2e par an. "
        "PER carbone = potentiel d'évitement carbone en cas de réparation ou remplacement partiel. "
        "PER euro = potentiel d'évitement financier, calculé si un coût unitaire est trouvé. "
        "Les résultats sont indicatifs et doivent être validés pour une utilisation contractuelle."
    )
    story.append(Paragraph(explanation, styles["Small"]))
    story.append(Spacer(1, 0.2*cm))

    table_data = dataframe_to_table_data(df, max_rows=25)
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)

    story.append(PageBreak())
    story.append(Paragraph("3. Limites de la phase test", styles["Heading2"]))
    limitations = [
        "L'extraction texte peut échouer sur des PDF scannés sans OCR.",
        "Les FDES/PEP n'ont pas toutes le même niveau de détail pour les modules B2, B3 et B4.",
        "Le coefficient de remplacement est issu d'une bibliothèque test par famille d'ouvrage.",
        "L'indicateur ne remplace pas une ACV réglementaire ni une validation technique de conception.",
        "Les documents absents ne bloquent pas le rapport : ils abaissent seulement le niveau de confiance."
    ]
    for item in limitations:
        story.append(Paragraph("- " + item, styles["Small"]))

    doc.build(story)
    return buffer.getvalue()


# -----------------------------
# Interface Streamlit
# -----------------------------

st.set_page_config(page_title=APP_TITLE, layout="wide")

st.title(APP_TITLE)
st.caption("Phase test - dépôt de PDF, extraction automatisée et génération d'un rapport même si le dossier est incomplet.")

with st.expander("Principe des indicateurs", expanded=True):
    st.markdown("""
**ICA - Impact Carbone Annualisé**  
`ICA = impact carbone total / durée de vie de référence`

**PER - Potentiel d'Évitement par Réparation**  
`PER carbone = impact carbone total x (1 - coefficient de remplacement)`  
`PER financier = coût de remplacement complet x (1 - coefficient de remplacement)`

Le coefficient de remplacement provient d'une petite bibliothèque test par famille d'ouvrage.
    """)

st.subheader("Documents nécessaires")
st.write("Ajoute les PDF disponibles. Le rapport peut être lancé même si certains documents sont absents.")

uploads = {}
for slot, meta in DOCUMENT_SLOTS.items():
    uploads[slot] = st.file_uploader(
        meta["label"],
        type=["pdf"],
        accept_multiple_files=True,
        help=meta["help"],
        key=slot,
    )

st.divider()

col_run, col_settings = st.columns([1, 2])
with col_settings:
    st.subheader("Paramètres de phase test")
    use_manual_defaults = st.checkbox(
        "Utiliser des valeurs de secours si certaines données ne sont pas trouvées",
        value=True,
        help="Permet de générer un rapport de démonstration même avec des FDES incomplètes ou non trouvées."
    )
    default_life = st.number_input("Durée de vie par défaut si non trouvée (ans)", min_value=1, max_value=100, value=30)
    default_carbon = st.number_input("Carbone par défaut si non trouvé (kgCO2e/unité)", min_value=0.0, value=0.0)
    default_cost = st.number_input("Coût unitaire par défaut si non trouvé (€)", min_value=0.0, value=0.0)

with col_run:
    st.subheader("Lancement")
    run = st.button("Générer le rapport", type="primary", use_container_width=True)

if run:
    all_text_by_slot = {}
    summary = {"docs": {}}

    with st.spinner("Extraction des PDF et calcul des indicateurs..."):
        for slot, files in uploads.items():
            texts = []
            file_names = []
            if files:
                for f in files:
                    file_names.append(f.name)
                    texts.append(extract_pdf_text(f))
                summary["docs"][slot] = {
                    "status": "Présent",
                    "files": file_names,
                    "chars": sum(len(t) for t in texts),
                }
            else:
                summary["docs"][slot] = {
                    "status": "Absent",
                    "files": [],
                    "chars": 0,
                }
            all_text_by_slot[slot] = "\n\n".join(texts)

        combined_text = "\n\n".join(all_text_by_slot.values())
        env = extract_environmental_values(all_text_by_slot.get("fdes_pep", "") + "\n" + combined_text)
        costs = extract_cost_values(all_text_by_slot.get("cctp_dpgf", "") + "\n" + all_text_by_slot.get("devis_variantes", ""))
        products = detect_products(combined_text)

        if not products:
            products = [{
                "famille": "Famille non reconnue automatiquement",
                "mots_cles": "",
                "coef_remplacement": 1.00,
                "commentaire": "Aucun mot-clé reconnu. Hypothèse prudente : remplacement complet."
            }]

        rows = []
        for p in products:
            row = {
                "Famille détectée": p["famille"],
                "Mots-clés trouvés": p["mots_cles"],
                "Coef remplacement": p["coef_remplacement"],
                "Carbone total kgCO2e": env["carbone_total_kgco2e"],
                "Durée vie ans": env["duree_vie_ans"],
                "Coût unitaire €": costs["cout_unitaire_eur"],
                "Source carbone": confidence_label(env["carbone_total_kgco2e"]),
                "Source durée vie": confidence_label(env["duree_vie_ans"]),
                "Source coût": confidence_label(costs["cout_unitaire_eur"]),
                "Commentaire": p["commentaire"],
            }

            if use_manual_defaults:
                if row["Carbone total kgCO2e"] is None and default_carbon > 0:
                    row["Carbone total kgCO2e"] = default_carbon
                    row["Source carbone"] = "Valeur de secours"
                if row["Durée vie ans"] is None and default_life > 0:
                    row["Durée vie ans"] = default_life
                    row["Source durée vie"] = "Valeur de secours"
                if row["Coût unitaire €"] is None and default_cost > 0:
                    row["Coût unitaire €"] = default_cost
                    row["Source coût"] = "Valeur de secours"

            calc_input = {
                "carbone_total_kgco2e": row["Carbone total kgCO2e"],
                "duree_vie_ans": row["Durée vie ans"],
                "cout_unitaire_eur": row["Coût unitaire €"],
                "coef_remplacement": row["Coef remplacement"],
            }
            indicators = compute_indicators(calc_input)
            row.update({
                "ICA kgCO2e/an": indicators["ICA_kgCO2e_par_an"],
                "PER carbone kgCO2e évitable": indicators["PER_carbone_kgCO2e_evitable"],
                "PER € évitable": indicators["PER_eur_evitable"],
            })
            rows.append(row)

        df = pd.DataFrame(rows)

    st.success("Rapport généré.")

    missing = [DOCUMENT_SLOTS[k]["label"] for k, v in summary["docs"].items() if v["status"] == "Absent"]

    st.subheader("Synthèse des documents")
    doc_status = pd.DataFrame([
        {
            "Document": DOCUMENT_SLOTS[k]["label"],
            "Statut": v["status"],
            "Fichiers": ", ".join(v["files"]),
            "Caractères extraits": v["chars"],
        }
        for k, v in summary["docs"].items()
    ])
    st.dataframe(doc_status, use_container_width=True)

    if missing:
        st.warning("Le rapport est incomplet car certains documents n'ont pas été fournis : " + ", ".join(missing))

    st.subheader("Résultats indicateurs")
    st.dataframe(df, use_container_width=True)

    st.subheader("Preuves d'extraction")
    with st.expander("Voir les extraits utilisés"):
        st.markdown("**Preuve durée de vie**")
        st.code(env["preuve_duree"] or "Non trouvé")
        st.markdown("**Preuve carbone**")
        st.code(env["preuve_carbone"] or "Non trouvé")
        st.markdown("**Preuve coût**")
        st.code(costs["preuve_cout"] or "Non trouvé")

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Télécharger les résultats CSV",
        data=csv_bytes,
        file_name="resultats_kpi_maintenance_reparabilite.csv",
        mime="text/csv",
        use_container_width=True,
    )

    pdf_bytes = make_pdf_report(summary, df, missing)
    st.download_button(
        "Télécharger le rapport PDF",
        data=pdf_bytes,
        file_name="rapport_kpi_maintenance_reparabilite.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    json_bytes = json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        "Télécharger le journal d'analyse JSON",
        data=json_bytes,
        file_name="journal_analyse_kpi.json",
        mime="application/json",
        use_container_width=True,
    )

else:
    st.info("Dépose les PDF disponibles dans les emplacements ci-dessus, puis clique sur 'Générer le rapport'.")
