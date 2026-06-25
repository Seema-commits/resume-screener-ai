"""
Deterministic integrity checks for parsed resume profiles.

This intentionally contains NO LLM calls. These are simple, explainable
rules run in plain Python against the structured profile (roles,
dates, education, skills) extracted in Stage 1 - more reliable and
easier to demo/justify than asking an LLM to "notice" these buried in
resume text.

Rules implemented (kept deliberately simple, per assignment guidance
that 3-4 simple rules are enough):

1. date_overlap                    - two roles overlap in time
2. contradictory_dates             - a role's end_date is before its start_date
3. senior_title_little_experience  - senior-sounding title, little total experience
4. skill_without_experience        - skills listed but no work history at all
"""

from datetime import date


SENIORITY_KEYWORDS = (
    "senior", "lead", "principal", "staff",
    "head", "director", "architect"
)

SENIOR_TITLE_EXPERIENCE_THRESHOLD_MONTHS = 24


def parse_month(date_str):
    """
    Parse a "YYYY-MM" string (or "present"/"current"/"now") into a
    date object representing the 1st of that month. Returns None if
    the value is missing or unparseable.
    """

    if not date_str:
        return None

    s = str(date_str).strip().lower()

    if s in ("present", "current", "now", "ongoing", "till date"):
        today = date.today()
        return date(today.year, today.month, 1)

    # "YYYY-MM"
    try:
        year_str, month_str = s.split("-")
        return date(int(year_str), int(month_str), 1)
    except ValueError:
        pass

    # "YYYY" only
    try:
        return date(int(s), 1, 1)
    except ValueError:
        return None


def _role_field(role, field):
    """Support both RoleEntry objects and plain dicts."""
    if isinstance(role, dict):
        return role.get(field)
    return getattr(role, field, None)


def _months_between(start, end):
    return (
        (end.year - start.year) * 12
        + (end.month - start.month)
        + 1
    )


def total_experience_months(roles):
    """
    Total experience as the UNION of all valid role date ranges
    (overlapping roles are not double-counted).
    """

    intervals = []

    for role in roles:
        start = parse_month(_role_field(role, "start_date"))
        end = parse_month(_role_field(role, "end_date"))
        if start and end and start <= end:
            intervals.append((start, end))

    if not intervals:
        return 0

    intervals.sort(key=lambda iv: iv[0])

    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return sum(_months_between(s, e) for s, e in merged)


# ---------------------------------------------------
# RULE 1: date overlap
# ---------------------------------------------------

def detect_date_overlaps(roles):

    parsed = []

    for role in roles:

        start = parse_month(_role_field(role, "start_date"))
        end = parse_month(_role_field(role, "end_date"))

        if start and end and start <= end:
            parsed.append((role, start, end))

    parsed.sort(key=lambda item: item[1])

    flags = []

    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):

            role_a, start_a, end_a = parsed[i]
            role_b, start_b, end_b = parsed[j]

            latest_start = max(start_a, start_b)
            earliest_end = min(end_a, end_b)

            if latest_start > earliest_end:
                continue

            overlap_months = _months_between(latest_start, earliest_end)

            # Same-month transitions (left old job and started new
            # one in the same calendar month) register as a
            # 1-month "overlap" due to month-only date resolution -
            # this is normal, not embellishment. Only flag genuine
            # multi-month concurrent employment.
            if overlap_months <= 1:
                continue

            title_a = _role_field(role_a, "title") or "Unknown role"
            company_a = _role_field(role_a, "company") or "Unknown company"
            title_b = _role_field(role_b, "title") or "Unknown role"
            company_b = _role_field(role_b, "company") or "Unknown company"

            flags.append({
                "flag_type": "date_overlap",
                "severity": "high" if overlap_months >= 3 else "medium",
                "description": (
                    f"'{title_a}' at {company_a} overlaps with "
                    f"'{title_b}' at {company_b} by "
                    f"{overlap_months} month(s)"
                ),
                "evidence": (
                    f"{_role_field(role_a, 'start_date')} - "
                    f"{_role_field(role_a, 'end_date')} vs "
                    f"{_role_field(role_b, 'start_date')} - "
                    f"{_role_field(role_b, 'end_date')}"
                )
            })

    return flags


# ---------------------------------------------------
# RULE 2: contradictory dates (end before start)
# ---------------------------------------------------

def detect_contradictory_dates(roles):

    flags = []

    for role in roles:

        start = parse_month(_role_field(role, "start_date"))
        end = parse_month(_role_field(role, "end_date"))

        if start and end and end < start:

            title = _role_field(role, "title") or "Unknown role"
            company = _role_field(role, "company") or "Unknown company"

            flags.append({
                "flag_type": "contradictory_dates",
                "severity": "high",
                "description": (
                    f"'{title}' at {company} has an end date before "
                    f"its start date"
                ),
                "evidence": (
                    f"{_role_field(role, 'start_date')} - "
                    f"{_role_field(role, 'end_date')}"
                )
            })

    return flags


# ---------------------------------------------------
# RULE 3: senior title, little total experience
# ---------------------------------------------------

def detect_senior_title_little_experience(roles):

    total_months = total_experience_months(roles)

    if total_months >= SENIOR_TITLE_EXPERIENCE_THRESHOLD_MONTHS:
        return []

    flags = []
    seen_titles = set()

    for role in roles:

        title = (_role_field(role, "title") or "").strip()
        title_lower = title.lower()

        if not title or title_lower in seen_titles:
            continue

        if any(kw in title_lower for kw in SENIORITY_KEYWORDS):

            seen_titles.add(title_lower)

            flags.append({
                "flag_type": "senior_title_little_experience",
                "severity": "medium",
                "description": (
                    f"Title '{title}' suggests seniority, but total "
                    f"computed experience is only "
                    f"{total_months} month(s)"
                ),
                "evidence": f"Total experience: {total_months} months"
            })

    return flags


# ---------------------------------------------------
# RULE 4: skill claimed, no work history to back it up
# ---------------------------------------------------

def detect_skill_without_experience(profile_skills, roles):

    if profile_skills and not roles:

        return [{
            "flag_type": "skill_without_experience",
            "severity": "medium",
            "description": (
                f"{len(profile_skills)} skill(s) listed but no work "
                f"history found to evidence them"
            ),
            "evidence": ", ".join(profile_skills[:8])
        }]

    return []


# ---------------------------------------------------
# RUN ALL RULES
# ---------------------------------------------------

def run_integrity_checks(profile):
    """
    profile: a ParsedProfile object or equivalent dict with
    'roles' and 'skills'. Returns a combined list of flag dicts
    from all deterministic rules.
    """

    if isinstance(profile, dict):
        roles = profile.get("roles", [])
        skills = profile.get("skills", [])
    else:
        roles = profile.roles
        skills = profile.skills

    roles_as_dicts = [
        r.model_dump() if hasattr(r, "model_dump") else r
        for r in roles
    ]

    flags = []
    flags += detect_date_overlaps(roles_as_dicts)
    flags += detect_contradictory_dates(roles_as_dicts)
    flags += detect_senior_title_little_experience(roles_as_dicts)
    flags += detect_skill_without_experience(skills, roles_as_dicts)

    return flags
