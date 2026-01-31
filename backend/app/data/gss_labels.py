"""
GSS Variable Label Mappings

This module contains mappings from numeric codes to human-readable labels
for GSS variables. These are used in persona generation to create natural
language descriptions.
"""

from typing import Optional


# =============================================================================
# DEMOGRAPHICS
# =============================================================================

SEX_LABELS = {
    1: "Male",
    2: "Female"
}

RACE_LABELS = {
    1: "White",
    2: "Black",
    3: "Other"
}

REGION_LABELS = {
    1: "New England",
    2: "Middle Atlantic",
    3: "East North Central",
    4: "West North Central",
    5: "South Atlantic",
    6: "East South Central",
    7: "West South Central",
    8: "Mountain",
    9: "Pacific"
}

DEGREE_LABELS = {
    0: "Less than high school",
    1: "High school",
    2: "Associate/Junior college",
    3: "Bachelor's degree",
    4: "Graduate degree"
}

MARITAL_LABELS = {
    1: "Married",
    2: "Widowed",
    3: "Divorced",
    4: "Separated",
    5: "Never married"
}

WRKSTAT_LABELS = {
    1: "Working full-time",
    2: "Working part-time",
    3: "Temporarily not working",
    4: "Unemployed, laid off",
    5: "Retired",
    6: "In school",
    7: "Keeping house",
    8: "Other"
}

# =============================================================================
# POLITICAL / IDEOLOGICAL
# =============================================================================

POLVIEWS_LABELS = {
    1: "Extremely liberal",
    2: "Liberal",
    3: "Slightly liberal",
    4: "Moderate",
    5: "Slightly conservative",
    6: "Conservative",
    7: "Extremely conservative"
}

POLVIEWS_SIMPLIFIED = {
    1: "Liberal",
    2: "Liberal",
    3: "Liberal",
    4: "Moderate",
    5: "Conservative",
    6: "Conservative",
    7: "Conservative"
}

PARTYID_LABELS = {
    0: "Strong Democrat",
    1: "Not strong Democrat",
    2: "Independent, near Democrat",
    3: "Independent",
    4: "Independent, near Republican",
    5: "Not strong Republican",
    6: "Strong Republican",
    7: "Other party"
}

PARTYID_SIMPLIFIED = {
    0: "Democrat",
    1: "Democrat",
    2: "Democrat-leaning Independent",
    3: "Independent",
    4: "Republican-leaning Independent",
    5: "Republican",
    6: "Republican",
    7: "Other"
}

# =============================================================================
# RELIGION
# =============================================================================

RELIG_LABELS = {
    1: "Protestant",
    2: "Catholic",
    3: "Jewish",
    4: "None",
    5: "Other",
    6: "Buddhism",
    7: "Hinduism",
    8: "Other Eastern",
    9: "Muslim/Islam",
    10: "Orthodox Christian",
    11: "Christian",
    12: "Native American",
    13: "Inter-nondenominational"
}

ATTEND_LABELS = {
    0: "Never",
    1: "Less than once a year",
    2: "Once a year",
    3: "Several times a year",
    4: "Once a month",
    5: "2-3 times a month",
    6: "Nearly every week",
    7: "Every week",
    8: "More than once a week"
}

# =============================================================================
# ATTITUDES / OPINIONS
# =============================================================================

BINARY_FAVOR_OPPOSE = {
    1: "Favor",
    2: "Oppose"
}

BINARY_YES_NO = {
    1: "Yes",
    2: "No"
}

BINARY_LEGAL_ILLEGAL = {
    1: "Legal",
    2: "Not legal"
}

# For questions like HOMOSEX (is homosexual sex wrong?)
MORAL_JUDGMENT = {
    1: "Always wrong",
    2: "Almost always wrong",
    3: "Sometimes wrong",
    4: "Not wrong at all"
}

# For happiness question
HAPPY_LABELS = {
    1: "Very happy",
    2: "Pretty happy",
    3: "Not too happy"
}

# For national spending questions (NATENVIR, NATHEAL, etc.)
SPENDING_LABELS = {
    1: "Too little",
    2: "About right",
    3: "Too much"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_label(variable: str, code: int) -> Optional[str]:
    """
    Get human-readable label for a GSS variable code.

    Args:
        variable: Variable name (e.g., 'sex', 'polviews')
        code: Numeric code from GSS

    Returns:
        Human-readable label, or None if not found
    """
    mapping = VARIABLE_MAPPINGS.get(variable.lower())
    if mapping:
        return mapping.get(code)
    return None


def format_value(variable: str, code: int, simplified: bool = False) -> str:
    """
    Format a GSS value for display in persona generation.

    Args:
        variable: Variable name
        code: Numeric code
        simplified: Use simplified labels if available

    Returns:
        Formatted string
    """
    var_lower = variable.lower()

    # Use simplified mappings if requested and available
    if simplified:
        if var_lower == 'polviews':
            return POLVIEWS_SIMPLIFIED.get(code, "Unknown")
        elif var_lower == 'partyid':
            return PARTYID_SIMPLIFIED.get(code, "Unknown")

    # Use standard mapping
    label = get_label(variable, code)
    return label if label else f"Code {code}"


# =============================================================================
# MASTER MAPPING REGISTRY
# =============================================================================

VARIABLE_MAPPINGS = {
    # Demographics
    'sex': SEX_LABELS,
    'race': RACE_LABELS,
    'region': REGION_LABELS,
    'degree': DEGREE_LABELS,
    'marital': MARITAL_LABELS,
    'wrkstat': WRKSTAT_LABELS,

    # Political
    'polviews': POLVIEWS_LABELS,
    'partyid': PARTYID_LABELS,

    # Religion
    'relig': RELIG_LABELS,
    'attend': ATTEND_LABELS,

    # Attitudes
    'happy': HAPPY_LABELS,
    'cappun': BINARY_FAVOR_OPPOSE,      # Death penalty
    'gunlaw': BINARY_FAVOR_OPPOSE,      # Gun permits
    'abany': BINARY_YES_NO,              # Abortion for any reason
    'grass': BINARY_LEGAL_ILLEGAL,       # Marijuana
    'homosex': MORAL_JUDGMENT,           # Homosexual relations

    # National spending (all use same scale)
    'natenvir': SPENDING_LABELS,
    'natheal': SPENDING_LABELS,
    'natfare': SPENDING_LABELS,
    'nateduc': SPENDING_LABELS,
    'natcity': SPENDING_LABELS,
    'natrace': SPENDING_LABELS,
}


# =============================================================================
# AGE AND INCOME HELPERS
# =============================================================================

def get_age_group(age: int) -> str:
    """Categorize age into groups."""
    if age < 30:
        return "18-29"
    elif age < 45:
        return "30-44"
    elif age < 65:
        return "45-64"
    else:
        return "65+"


def format_income_bracket(income_code: int) -> str:
    """
    Convert income16 code to readable bracket.

    Note: Income codes in GSS use different schemes in different years.
    This uses the 2016+ coding scheme (income16).
    """
    # This is simplified - actual codes vary by year
    # Consult GSS codebook for exact mappings
    brackets = {
        1: "Under $1,000",
        2: "$1,000-$2,999",
        3: "$3,000-$3,999",
        4: "$4,000-$4,999",
        5: "$5,000-$5,999",
        6: "$6,000-$6,999",
        7: "$7,000-$7,999",
        8: "$8,000-$9,999",
        9: "$10,000-$12,499",
        10: "$12,500-$14,999",
        11: "$15,000-$17,499",
        12: "$17,500-$19,999",
        13: "$20,000-$22,499",
        14: "$22,500-$24,999",
        15: "$25,000-$29,999",
        16: "$30,000-$34,999",
        17: "$35,000-$39,999",
        18: "$40,000-$49,999",
        19: "$50,000-$59,999",
        20: "$60,000-$74,999",
        21: "$75,000-$89,999",
        22: "$90,000-$109,999",
        23: "$110,000-$129,999",
        24: "$130,000-$149,999",
        25: "$150,000 or more",
    }
    return brackets.get(income_code, "Unknown")
