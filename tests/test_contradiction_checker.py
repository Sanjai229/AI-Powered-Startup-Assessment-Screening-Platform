"""
Tests for the contradiction checker.

Two things have to be true for this component to be useful:

    1. It catches real contradictions.
    2. It does NOT flag numbers that are perfectly fine.

The second is the harder one. A checker that flags everything is worse than
no checker at all, because the team stops reading its output. So half the
tests below are numbers that must NOT be flagged.

Run:  python3 test_contradiction_checker.py
"""

from contradiction_checker import check_claims

# What BookFast's spreadsheet actually supports.
TRUTH = {
    "customers": 500,
    "arpu": 40,
    "gross_margin": 0.70,
    "opex_monthly": 25000,
    "cash": 180000,
    "cac": 220,
    "lifetime_months": 30,
    "revenue_monthly": 20000,
    "gross_profit_monthly": 14000,
    "burn_monthly": 11000,
    "runway_months": 16.36,
    "ltv": 840,
}

results = []


def expect_flagged(name, sentence, metric):
    """This sentence contradicts the spreadsheet and must be caught."""
    found = check_claims(sentence, TRUTH).findings
    ok = any(f.metric == metric for f in found)
    results.append((ok, name, "flagged" if found else "not flagged", "flagged"))


def expect_clean(name, sentence):
    """This sentence is fine and must NOT be caught."""
    found = check_claims(sentence, TRUTH).findings
    ok = not found
    detail = "clean" if ok else f"flagged as {found[0].metric}"
    results.append((ok, name, detail, "clean"))


# ===========================================================================
# MUST BE CAUGHT — the deck contradicts the spreadsheet
# ===========================================================================
expect_flagged("Customer count inflated tenfold",
               "Over 5,000 salons are now on BookFast across Australia.",
               "customers")

expect_flagged("Margin overstated",
               "Gross margin is 85% after hosting and card fees.",
               "gross_margin")

expect_flagged("Revenue overstated tenfold",
               "We are currently generating $200,000 in monthly revenue.",
               "revenue_monthly")

expect_flagged("Runway overstated",
               "We have 30 months of runway at our current spend.",
               "runway_months")

expect_flagged("Annual revenue that still does not add up",
               "We are on track for $1,000,000 in revenue a year.",
               "revenue_monthly")

expect_flagged("Burn understated",
               "Our monthly burn is only $2,000.",
               "burn_monthly")


# ===========================================================================
# MUST NOT BE CAUGHT — these numbers are fine
# ===========================================================================
expect_clean("Market size is not a customer count",
             "There are 25,000 salons in Australia.")

expect_clean("The amount being raised is not cash in the bank",
             "We are raising $500,000 to double the engineering team.")

expect_clean("A price is not a headcount",
             "Every salon pays a flat $40 per month.")

expect_clean("A duration is not a headcount",
             "A booking app that lets customers book in under 30 seconds.")

expect_clean("Hours spent are not a headcount",
             "Independent salon owners spend up to 9 hours a week on the phone.")

expect_clean("Correct customer count passes",
             "We now have 500 salons on the platform.")

expect_clean("Slightly rounded figure is within tolerance",
             "We have around 520 salons signed up.")

expect_clean("Correct LTV passes",
             "Lifetime value per salon is $840.")

expect_clean("Correct CAC passes",
             "It costs us $220 to sign up a new salon.")

expect_clean("Annual revenue stated correctly passes",
             "We are generating $240,000 in revenue a year.")

expect_clean("A number with no claim attached is ignored",
             "Two founders, both ex-salon owners, plus three engineers.")

expect_clean("Market value is not revenue",
             "The wider personal services market is worth $4.2 billion a year.")


# ===========================================================================
if __name__ == "__main__":
    for ok, name, got, want in results:
        print(f"{'pass' if ok else 'FAIL'}  {name:46} {got}")

    failed = [r for r in results if not r[0]]
    print()
    if failed:
        print(f"{len(failed)} of {len(results)} checks failed.")
        raise SystemExit(1)
    caught = sum(1 for r in results if r[3] == "flagged")
    clean = len(results) - caught
    print(f"All {len(results)} checks passed "
          f"({caught} contradictions caught, {clean} false alarms avoided).")
