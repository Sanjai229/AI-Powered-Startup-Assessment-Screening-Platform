"""
Contradiction checker for the MamakScore AI engine.

Compares what a pitch deck CLAIMS against what the founder's own spreadsheet
SUPPORTS, and flags anything that does not add up.

The client's own example: the deck says 100,000 customers, the financial
model implies 5,000. The system should flag that rather than quietly
picking one number.

Everything here is plain code. No AI decides whether two numbers disagree —
arithmetic does. The only judgement call is the threshold, and that is a
setting at the top of this file, not a rule buried in the logic.

Usage:
    from contradiction_checker import check_claims
    findings = check_claims(deck_text, financial_figures)
"""

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Settings. Asked the client 28 Aug 2026, awaiting answer.
# Until then these are the documented defaults.
# ---------------------------------------------------------------------------

# How far apart two numbers must be before we call it a contradiction.
# 0.20 means the claim has to be more than 20% out. Below that we assume
# rounding or a different reporting date, not an exaggeration.
DIFFERENCE_THRESHOLD = 0.20

# A claim this many times larger than reality is reported as major rather
# than moderate. Ten times out is a different kind of problem to 30% out.
MAJOR_MULTIPLE = 3.0


@dataclass
class Finding:
    metric: str          # what was being claimed
    claimed: float       # the number in the deck
    implied: float       # what the spreadsheet supports
    difference: float    # as a fraction, 0.5 means 50% out
    severity: str        # "moderate" or "major"
    quote: str           # the founder's own sentence, word for word

    def describe(self):
        direction = "higher" if self.claimed > self.implied else "lower"
        # A margin is a fraction, so showing it to no decimal places would
        # print "claims 1, supports 1" for 85% against 70%.
        if self.metric == "gross_margin":
            claimed = f"{self.claimed:.0%}"
            implied = f"{self.implied:.0%}"
        else:
            claimed = f"{self.claimed:,.0f}"
            implied = f"{self.implied:,.0f}"
        return (
            f"[{self.severity}] {self.metric}: deck claims "
            f"{claimed}, spreadsheet supports {implied} "
            f"({self.difference:.0%} {direction})\n"
            f"    \"{self.quote.strip()}\""
        )


@dataclass
class CheckResult:
    findings: list = field(default_factory=list)
    checked: list = field(default_factory=list)   # metrics we could compare
    skipped: list = field(default_factory=list)   # claims we could not match

    @property
    def is_clean(self):
        return not self.findings


# ---------------------------------------------------------------------------
# Recognising what a number in the deck refers to
#
# Each metric has words that identify it, and words that rule it out.
# The exclusions matter: "25,000 salons in Australia" is the size of the
# market, not the number of customers. Without that rule the checker would
# flag every market slide in existence.
# ---------------------------------------------------------------------------

# Order matters. The most specific metric is tested first and the vaguest
# last. "Lifetime value per salon is $840" contains the word "salon", so if
# customers were tested first it would be read as a customer count.
CLAIM_TYPES = {
    "ltv": {
        "includes": ["lifetime value", "ltv", "worth over their lifetime"],
        "excludes": [],
    },
    "cac": {
        "includes": ["cost us", "costs us", "acquisition cost", "cac",
                     "to sign up", "to win a", "to acquire"],
        "excludes": [],
    },
    "runway_months": {
        "includes": ["runway", "months of cash"],
        "excludes": [],
    },
    "burn_monthly": {
        "includes": ["burn", "losing", "monthly spend", "spend per month"],
        "excludes": [],
    },
    "revenue_monthly": {
        "includes": ["revenue", "sales", "turnover", "mrr", "arr", "generating"],
        "excludes": ["market", "industry", "worth", "tam"],
    },
    "gross_margin": {
        "includes": ["margin"],
        "excludes": [],
    },
    "cash": {
        "includes": ["in the bank", "cash in", "bank balance", "cash on hand"],
        "excludes": ["raising", "raise", "seeking", "asking"],
    },
    "customers": {
        "includes": ["customer", "salon", "user", "subscriber", "account",
                     "client", "merchant"],
        "excludes": ["market", "there are", "total", "tam", "industry",
                     "nationwide", "addressable", "potential", "worth",
                     "pays", "per month", "flat", "each month", "charge"],
    },
}

# A customer count is a plain number of things. If the number carries a
# currency symbol or a unit of time, it is a price or a duration, not a
# headcount. Without this, "book in under 30 seconds" reads as 30 customers.
COUNT_ONLY_METRICS = ["customers"]
UNIT_WORDS = ["second", "minute", "hour", "day", "week", "month", "year"]

# Words that mean the number covers a year, not a month
ANNUAL_WORDS = ["a year", "per year", "annual", "annually", "arr", "p.a."]

# Metrics we hold as monthly. An annual claim gets divided by twelve
# before comparison, otherwise every annual revenue figure looks like a
# twelve-fold exaggeration.
MONTHLY_METRICS = ["revenue_monthly", "burn_monthly"]


NUMBER_PATTERN = re.compile(
    r"""
    (?P<currency>[$£€]|rm\s?|myr\s?|aud\s?)?   # optional currency marker
    (?P<number>\d[\d,]*(?:\.\d+)?)             # the digits
    \s*
    (?P<suffix>%|k\b|m\b|million\b|bn\b|billion\b)?   # optional scale
    """,
    re.VERBOSE | re.IGNORECASE,
)


def parse_number(match):
    """Turn a matched number into a float, applying any k/m/% scaling."""
    raw = match.group("number").replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None, False

    suffix = (match.group("suffix") or "").lower().strip()
    is_percent = suffix == "%"

    if suffix in ("k",):
        value *= 1_000
    elif suffix in ("m", "million"):
        value *= 1_000_000
    elif suffix in ("bn", "billion"):
        value *= 1_000_000_000

    if is_percent:
        value = value / 100

    return value, is_percent


def classify(sentence, is_percent, has_currency=False, trailing=""):
    """
    Work out which metric a number in this sentence refers to.

    Returns None when nothing matches, which is the common case — most
    numbers in a pitch deck are not claims we can check.
    """
    lowered = sentence.lower()
    trailing = (trailing or "").lower()

    for metric, rules in CLAIM_TYPES.items():
        # A percentage can only be a margin, and a margin is always a percentage
        if is_percent and metric != "gross_margin":
            continue
        if not is_percent and metric == "gross_margin":
            continue

        if metric in COUNT_ONLY_METRICS:
            # A price, not a headcount
            if has_currency:
                continue
            # A duration, not a headcount
            if any(unit in trailing for unit in UNIT_WORDS):
                continue

        if any(word in lowered for word in rules["excludes"]):
            continue
        if any(word in lowered for word in rules["includes"]):
            return metric

    return None


def split_sentences(text):
    """Break the deck text into sentences, keeping the original wording."""
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("---"):
            continue
        for part in re.split(r"(?<=[.!?])\s+", line):
            if part.strip():
                lines.append(part.strip())
    return lines


def check_claims(deck_text, figures, threshold=DIFFERENCE_THRESHOLD):
    """
    Compare every checkable claim in the deck against the spreadsheet.

    deck_text: the text extracted from the pitch deck
    figures:   the output of the financial engine, plus the reader's raw
               values for things the engine does not calculate
    """
    result = CheckResult()

    for sentence in split_sentences(deck_text):
        for match in NUMBER_PATTERN.finditer(sentence):
            claimed, is_percent = parse_number(match)
            if claimed is None:
                continue

            has_currency = bool(match.group("currency"))
            trailing = sentence[match.end():match.end() + 20]
            metric = classify(sentence, is_percent, has_currency, trailing)
            if metric is None:
                continue

            implied = figures.get(metric)
            if implied is None:
                result.skipped.append((metric, sentence))
                continue

            # An annual figure has to be brought back to a monthly one
            # before it can be compared with a monthly figure.
            comparable = claimed
            if metric in MONTHLY_METRICS:
                if any(word in sentence.lower() for word in ANNUAL_WORDS):
                    comparable = claimed / 12

            if implied == 0:
                # Cannot express a percentage difference from zero.
                if comparable != 0:
                    result.findings.append(Finding(
                        metric=metric, claimed=comparable, implied=implied,
                        difference=1.0, severity="major", quote=sentence,
                    ))
                continue

            difference = abs(comparable - implied) / abs(implied)
            result.checked.append(metric)

            if difference <= threshold:
                continue

            multiple = max(comparable, implied) / max(min(comparable, implied), 1e-9)
            severity = "major" if multiple >= MAJOR_MULTIPLE else "moderate"

            result.findings.append(Finding(
                metric=metric, claimed=comparable, implied=implied,
                difference=difference, severity=severity, quote=sentence,
            ))

    return result


def describe(result):
    """Plain English summary."""
    if result.is_clean:
        return (f"No contradictions found. {len(set(result.checked))} "
                f"claim types checked.")

    lines = [f"{len(result.findings)} contradiction(s) found:"]
    for finding in result.findings:
        lines.append(finding.describe())
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from excel_reader import read_financial_model
    from financial_engine import calculate

    deck_path = sys.argv[1]
    excel_path = sys.argv[2]

    with open(deck_path, encoding="utf-8") as handle:
        deck_text = handle.read()

    extracted = read_financial_model(excel_path)
    financial = calculate(extracted.values)

    # The checker compares against both the calculated figures and the
    # raw inputs the founder typed in.
    figures = dict(extracted.values)
    figures.update(financial.figures)

    print(f"Deck:        {deck_path}")
    print(f"Spreadsheet: {excel_path}")
    print()
    print(describe(check_claims(deck_text, figures)))
