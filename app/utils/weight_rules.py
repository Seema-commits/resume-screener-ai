"""
Deterministic, keyword-based criteria weighting.

Same philosophy as date_utils.py: plain Python, no LLM, fully
inspectable. Computed ONCE per job description, before any
candidate is scored, so every candidate in a single run is judged
against the identical weight set (apples-to-apples). Different job
descriptions can legitimately produce different weights - that's
the point of "adaptive" - but nothing varies *within* one run.

Base weights sum to 100: Skills 40 / Experience 30 / Education 10
/ Domain 20. Keyword signals nudge category TARGETS within fixed
bounds; Skills always absorbs whatever's left so the total stays
exactly 100, with a floor so Skills never gets squeezed too low.
"""

BASE_WEIGHTS = {
    "Skills": 40,
    "Experience": 30,
    "Education": 10,
    "Domain": 20
}

SKILLS_FLOOR = 20

EDUCATION_SIGNALS = [
    (25, ["phd", "ph.d", "doctorate"],
     "advanced degree explicitly required"),
    (15, ["master's degree required", "master's required",
          "bachelor's degree required", "degree required",
          "must have a degree"],
     "degree explicitly required"),
    (5, ["no degree required", "degree not required",
         "education not required", "self-taught welcome"],
     "JD explicitly says no degree required"),
]

EXPERIENCE_SIGNALS = [
    (40, ["10+ years", "8+ years", "extensive experience required",
          "minimum 7 years"],
     "JD requires significant years of experience"),
    (15, ["fresher", "entry level", "entry-level", "0-1 year",
          "no prior experience required", "graduates welcome",
          "junior welcome"],
     "JD welcomes freshers/entry-level candidates"),
]

DOMAIN_SIGNALS = [
    (25, ["fintech", "healthcare", "hipaa", "pci", "compliance",
          "regulated industry", "payments"],
     "JD emphasizes a specific regulated/specialized domain"),
]


def _matched_phrases(jd_lower, phrases):
    return [p for p in phrases if p in jd_lower]


def derive_criteria_weights(job_description):
    """
    Returns:
    {
        "weights": {"Skills": 40, "Experience": 30, ...},
        "matched_signals": [
            {"category": "Education", "phrase": "phd",
             "reason": "...", "target": 25},
            ...
        ]
    }
    """

    jd_lower = (job_description or "").lower()

    matched_signals = []
    targets = dict(BASE_WEIGHTS)

    for category, signal_list in (
        ("Education", EDUCATION_SIGNALS),
        ("Experience", EXPERIENCE_SIGNALS),
        ("Domain", DOMAIN_SIGNALS),
    ):

        # Use the strongest (highest target) tier that matches -
        # signal_list is defined strongest-first.
        for target, phrases, reason in signal_list:

            hits = _matched_phrases(jd_lower, phrases)

            if hits:

                targets[category] = target

                matched_signals.append({
                    "category": category,
                    "phrase": hits[0],
                    "reason": reason,
                    "target": target
                })

                break  # strongest matching tier wins, stop here

    # Skills absorbs whatever's left of 100
    non_skills_total = (
        targets["Experience"]
        + targets["Education"]
        + targets["Domain"]
    )

    skills_target = 100 - non_skills_total

    if skills_target < SKILLS_FLOOR:

        # Scale the other three down proportionally so Skills
        # never drops below its floor, while keeping the total
        # at exactly 100.
        scale = (100 - SKILLS_FLOOR) / non_skills_total

        targets["Experience"] = round(targets["Experience"] * scale)
        targets["Education"] = round(targets["Education"] * scale)
        targets["Domain"] = round(targets["Domain"] * scale)

        skills_target = 100 - (
            targets["Experience"]
            + targets["Education"]
            + targets["Domain"]
        )

    targets["Skills"] = skills_target

    return {
        "weights": targets,
        "matched_signals": matched_signals
    }
