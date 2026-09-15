"""
Tests for the financial engine.

Every expected number below was worked out by hand FIRST, then the code was
written to match. That order matters: if you write the test by running the
code and copying the answer, the test only proves the code agrees with
itself.

The workings are written out in each test so anyone can check them.

Run:  python3 test_financial_engine.py
"""

from financial_engine import calculate, describe

TOLERANCE = 0.01


def close(got, want):
    if want is None or got is None:
        return got == want
    if want == 0:
        return abs(got) < 1e-9
    return abs(got - want) / abs(want) <= TOLERANCE


results = []


def check(name, got, want, working):
    ok = close(got, want)
    results.append((ok, name, got, want, working))
    return ok


# ===========================================================================
# CASE 1 — BookFast. The normal case.
#
#   500 customers, $40 each, 70% margin, $25,000 opex, $180,000 cash,
#   $220 CAC, 30 month lifetime.
#
# By hand:
#   Revenue        500 x 40                = 20,000
#   Gross profit   20,000 x 0.70           = 14,000
#   Burn           25,000 - 14,000         = 11,000
#   Runway         180,000 / 11,000        = 16.36 months
#   GP per cust    14,000 / 500            = 28
#   LTV            40 x 0.70 x 30          = 840
#   CAC payback    220 / 28                = 7.86 months
#   LTV to CAC     840 / 220               = 3.82
# ===========================================================================
bookfast = calculate({
    "customers": 500, "arpu": 40, "gross_margin": 0.70,
    "opex_monthly": 25000, "cash": 180000, "cac": 220, "lifetime_months": 30,
})
f = bookfast.figures
check("BookFast revenue", f["revenue_monthly"], 20000, "500 x 40")
check("BookFast gross profit", f["gross_profit_monthly"], 14000, "20,000 x 0.70")
check("BookFast burn", f["burn_monthly"], 11000, "25,000 - 14,000")
check("BookFast runway", f["runway_months"], 16.3636, "180,000 / 11,000")
check("BookFast GP per customer", f["gross_profit_per_customer"], 28, "14,000 / 500")
check("BookFast LTV", f["ltv"], 840, "40 x 0.70 x 30")
check("BookFast CAC payback", f["cac_payback_months"], 7.857, "220 / 28")
check("BookFast LTV to CAC", f["ltv_to_cac"], 3.818, "840 / 220")


# ===========================================================================
# CASE 2 — Pre-revenue startup. No customers at all.
#
#   0 customers, $50 arpu, 60% margin, $8,000 opex, $60,000 cash.
#
# By hand:
#   Revenue        0 x 50          = 0
#   Gross profit   0 x 0.60        = 0
#   Burn           8,000 - 0       = 8,000
#   Runway         60,000 / 8,000  = 7.5 months
#   GP per cust    undefined, no customers to divide by
#   CAC payback    cannot be worked out
#
# This is the case that crashes naive code: dividing by zero customers.
# ===========================================================================
pre_revenue = calculate({
    "customers": 0, "arpu": 50, "gross_margin": 0.60,
    "opex_monthly": 8000, "cash": 60000, "cac": 300, "lifetime_months": 24,
})
f = pre_revenue.figures
check("Pre-revenue revenue", f["revenue_monthly"], 0, "0 x 50")
check("Pre-revenue burn", f["burn_monthly"], 8000, "8,000 - 0")
check("Pre-revenue runway", f["runway_months"], 7.5, "60,000 / 8,000")
check("Pre-revenue CAC payback is None",
      f.get("cac_payback_months"), None, "no customers, so undefined")


# ===========================================================================
# CASE 3 — Profitable company. Gross profit exceeds costs.
#
#   4,000 customers, $60 each, 75% margin, $120,000 opex, $400,000 cash.
#
# By hand:
#   Revenue        4,000 x 60          = 240,000
#   Gross profit   240,000 x 0.75      = 180,000
#   Burn           120,000 - 180,000   = -60,000  (a profit, not a burn)
#   Runway         not applicable
#
# A profitable company has no runway. Reporting one would be nonsense.
# ===========================================================================
profitable = calculate({
    "customers": 4000, "arpu": 60, "gross_margin": 0.75,
    "opex_monthly": 120000, "cash": 400000, "cac": 400, "lifetime_months": 36,
})
f = profitable.figures
check("Profitable revenue", f["revenue_monthly"], 240000, "4,000 x 60")
check("Profitable burn is negative", f["burn_monthly"], -60000, "120,000 - 180,000")
check("Profitable flag set", f["profitable"], True, "burn <= 0")
check("Profitable runway is None", f.get("runway_months"), None,
      "not burning cash, so no runway")


# ===========================================================================
# CASE 4 — Negative margin. Costs more to deliver than it charges.
#
#   200 customers, $30 each, -20% margin, $15,000 opex, $50,000 cash.
#
# By hand:
#   Revenue        200 x 30            = 6,000
#   Gross profit   6,000 x -0.20       = -1,200
#   Burn           15,000 - (-1,200)   = 16,200
#   Runway         50,000 / 16,200     = 3.09 months
#   LTV            30 x -0.20 x 18     = -108   (a customer costs money)
# ===========================================================================
negative = calculate({
    "customers": 200, "arpu": 30, "gross_margin": -0.20,
    "opex_monthly": 15000, "cash": 50000, "cac": 150, "lifetime_months": 18,
})
f = negative.figures
check("Negative margin gross profit", f["gross_profit_monthly"], -1200, "6,000 x -0.20")
check("Negative margin burn", f["burn_monthly"], 16200, "15,000 + 1,200")
check("Negative margin runway", f["runway_months"], 3.086, "50,000 / 16,200")
check("Negative margin LTV", f["ltv"], -108, "30 x -0.20 x 18")


# ===========================================================================
# CASE 5 — Missing optional inputs. No CAC, no lifetime.
#
# The core figures should still work. LTV and payback should be absent,
# not zero, and the reason should be stated.
# ===========================================================================
partial = calculate({
    "customers": 1000, "arpu": 25, "gross_margin": 0.55,
    "opex_monthly": 20000, "cash": 90000,
})
f = partial.figures
check("Partial revenue", f["revenue_monthly"], 25000, "1,000 x 25")
check("Partial gross profit", f["gross_profit_monthly"], 13750, "25,000 x 0.55")
check("Partial burn", f["burn_monthly"], 6250, "20,000 - 13,750")
check("Partial LTV absent", f.get("ltv"), None, "no lifetime given")
check("Partial payback absent", f.get("cac_payback_months"), None, "no CAC given")


# ===========================================================================
# CASE 6 — Missing required inputs. Nothing should be invented.
# ===========================================================================
broken = calculate({"customers": 100, "arpu": 20})
check("Broken returns no figures", len(broken.figures), 0, "missing required inputs")
check("Broken lists what is missing", len(broken.missing), 3,
      "gross_margin, opex_monthly, cash")


# ===========================================================================
if __name__ == "__main__":
    failed = [r for r in results if not r[0]]
    for ok, name, got, want, working in results:
        mark = "pass" if ok else "FAIL"
        print(f"{mark}  {name:34} got {got}  expected {want}   [{working}]")

    print()
    if failed:
        print(f"{len(failed)} of {len(results)} checks failed.")
        raise SystemExit(1)
    print(f"All {len(results)} checks passed.")
    print()
    print("BookFast summary:")
    print(describe(bookfast))
