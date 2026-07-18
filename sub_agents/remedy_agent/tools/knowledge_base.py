from .. import db

# Seeded once, on first init_db() call, with a small set of well-known,
# commonly-cited traditional remedies for common, clearly non-emergency
# complaints — spanning Ayurveda and Traditional Chinese Medicine (TCM).
# Deliberately no specific dosages: general traditional-use descriptions
# only, with real, commonly-cited cautions. This is a seed, not a
# complete reference — save_remedy grows it over time from vetted live
# search results.
_STARTER_REMEDIES = [
    # (ailment, tradition, remedy_name, description, cautions, source)
    (
        "cold_and_cough",
        "Ayurveda",
        "Tulsi (Holy Basil) tea",
        "Fresh or dried tulsi leaves steeped as a hot tea, often with "
        "ginger and honey, traditionally used to ease cough and cold "
        "symptoms.",
        "May interact with blood-thinning or diabetes medication; avoid "
        "high doses in pregnancy. Don't give honey to infants under 1 "
        "year (risk of infant botulism).",
        "NCCIH Herbs at a Glance; Ministry of AYUSH consumer guidance",
    ),
    (
        "cold_and_cough",
        "TCM",
        "Ban Lan Gen (Isatis root)",
        "A bitter herbal preparation (tea or granules) traditionally "
        "taken at the very first sign of a cold/sore throat.",
        "Traditionally used short-term only; avoid in those with a "
        "cold/deficient constitution per TCM theory, and in pregnancy "
        "without practitioner guidance.",
        "NCCIH Traditional Chinese Medicine overview",
    ),
    (
        "sore_throat",
        "General",
        "Warm salt water gargle",
        "Gargling warm water with a small amount of dissolved salt, "
        "several times a day.",
        "Not for young children who can't safely gargle without "
        "swallowing.",
        "MedlinePlus self-care guidance",
    ),
    (
        "gastric_indigestion",
        "Ayurveda",
        "Ginger (Adrak)",
        "Fresh ginger tea, or ginger chewed with a pinch of salt before "
        "meals, traditionally used to stimulate digestion and ease "
        "gas/bloating.",
        "May interact with blood-thinning medication (e.g. warfarin) and "
        "diabetes medication; avoid large amounts with gallstones.",
        "NCCIH Herbs at a Glance: Ginger",
    ),
    (
        "gastric_indigestion",
        "Ayurveda",
        "Triphala",
        "A traditional three-fruit herbal blend, usually taken as a "
        "powder or tablet, used for general digestive support.",
        "Can have a laxative effect; not recommended during pregnancy or "
        "for those with active diarrhea.",
        "Ministry of AYUSH National List of Essential AYUSH Medicines",
    ),
    (
        "gastric_indigestion",
        "General",
        "Peppermint tea",
        "Peppermint leaf steeped as a tea after meals, traditionally used "
        "to ease indigestion and bloating.",
        "May worsen acid reflux/GERD symptoms in some people; avoid with "
        "hiatal hernia.",
        "NCCIH Herbs at a Glance: Peppermint Oil",
    ),
    (
        "nausea",
        "General",
        "Ginger",
        "Ginger tea, candied ginger, or ginger chews, widely used "
        "traditionally (and studied) for nausea including motion "
        "sickness and mild pregnancy-related nausea.",
        "Consult a doctor before use for pregnancy-related nausea beyond "
        "mild cases; may interact with blood thinners.",
        "NCCIH Herbs at a Glance: Ginger",
    ),
    (
        "headache",
        "TCM",
        "Chrysanthemum (Ju Hua) tea",
        "Dried chrysanthemum flowers steeped as tea, traditionally used "
        "for headaches associated with eye strain or what TCM describes "
        "as 'excess heat'.",
        "Possible allergic reaction in those sensitive to ragweed/daisy "
        "family plants.",
        "NCCIH Traditional Chinese Medicine overview",
    ),
    (
        "mild_insomnia",
        "Ayurveda",
        "Ashwagandha",
        "Root powder or extract, traditionally used to support sleep and "
        "the body's response to stress.",
        "Avoid in pregnancy, with thyroid disorders, or alongside "
        "sedative/thyroid medication without medical guidance.",
        "NCCIH Herbs at a Glance: Ashwagandha",
    ),
    (
        "mild_insomnia",
        "General",
        "Chamomile tea",
        "Chamomile flowers steeped as a tea before bed, traditionally "
        "used as a mild calming aid.",
        "Avoid if allergic to ragweed/daisy family plants; may interact "
        "with blood-thinning medication.",
        "NCCIH Herbs at a Glance: Chamomile",
    ),
    (
        "joint_pain_inflammation",
        "Ayurveda",
        "Turmeric (Haldi)",
        "Turmeric in food, or as a warm 'golden milk' preparation, "
        "traditionally used for mild joint discomfort and inflammation.",
        "May interact with blood-thinning medication; avoid high doses "
        "with gallbladder disease.",
        "NCCIH Herbs at a Glance: Turmeric",
    ),
    (
        "minor_cuts_wounds",
        "Ayurveda",
        "Turmeric paste",
        "A paste of turmeric with water, traditionally applied to minor, "
        "clean cuts and scrapes.",
        "For minor wounds only — deep, dirty, or non-healing wounds need "
        "medical care, not a home remedy.",
        "Ministry of AYUSH consumer guidance",
    ),
]


def _seed_if_empty(conn) -> None:
    count = conn.execute("SELECT COUNT(*) FROM remedies").fetchone()[0]
    if count > 0:
        return
    conn.executemany(
        "INSERT INTO remedies "
        "(ailment, tradition, remedy_name, description, cautions, source, added_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(*row, db.now_iso()) for row in _STARTER_REMEDIES],
    )


def search_remedy_knowledge_base(query: str) -> dict:
    """Searches the local curated remedy knowledge base.

    Always check this before doing a live web search — it's faster and
    already vetted. If nothing relevant comes back, fall back to
    web_search against reputable sources, and consider save_remedy
    afterward to grow this for next time.

    Args:
        query: Ailment or keyword, e.g. "gastric", "cold and cough",
            "headache". Matches loosely against ailment and remedy name.

    Returns:
        dict: {"status": "success", "remedies": [{"ailment", "tradition",
        "remedy_name", "description", "cautions", "source"}, ...]}.
    """
    db.init_db()
    with db.lock(), db.connect() as conn:
        _seed_if_empty(conn)
        conn.commit()
        # Ailment keys are stored "snake_case" (e.g. "cold_and_cough");
        # normalize both sides to spaces so a natural-language query like
        # "cold and cough" still matches.
        like = f"%{' '.join(query.strip().lower().split())}%"
        rows = conn.execute(
            "SELECT ailment, tradition, remedy_name, description, cautions, source "
            "FROM remedies "
            "WHERE REPLACE(lower(ailment), '_', ' ') LIKE ? "
            "OR lower(remedy_name) LIKE ? OR lower(description) LIKE ?",
            (like, like, like),
        ).fetchall()

    return {"status": "success", "remedies": [dict(r) for r in rows]}


def save_remedy(
    ailment: str,
    tradition: str,
    remedy_name: str,
    description: str,
    cautions: str,
    source: str,
) -> dict:
    """Saves a vetted remedy to the local knowledge base for future queries.

    Only call this for something found via a reputable source (NCCIH,
    MedlinePlus, Ministry of AYUSH, Mayo Clinic, PubMed/NCBI, or
    similar) — never save an unverified claim from an untrustworthy
    site. Always include real cautions if the source mentions any; if it
    genuinely mentions none, say so explicitly rather than leaving it
    blank.

    Args:
        ailment: Normalized ailment/category, e.g. "gastric_indigestion".
        tradition: "Ayurveda", "TCM", or "General".
        remedy_name: The remedy's common name.
        description: General traditional-use description — no specific
            dosages; point to consulting a practitioner/product labeling
            for dosing.
        cautions: Known contraindications, interactions, or who should
            avoid it.
        source: Where this was found (site/publication name).

    Returns:
        dict: {"status": "success", "id": <row id>} or
        {"status": "error", "error_message": "..."}.
    """
    db.init_db()
    try:
        with db.lock(), db.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO remedies "
                "(ailment, tradition, remedy_name, description, cautions, source, added_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ailment, tradition, remedy_name, description, cautions, source, db.now_iso()),
            )
            return {"status": "success", "id": cursor.lastrowid}
    except Exception:
        return {
            "status": "error",
            "error_message": "Could not save that remedy locally.",
        }
