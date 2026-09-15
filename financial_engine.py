"""
Financial engine for the MamakScore AI engine.

Takes the seven numbers the Excel reader found and works out the figures an
investor cares about. The formulas are the client's own, from section 12 of
the planning document — nothing invented here.

    Revenue        customers x average revenue per customer
    Gross profit   revenue x gross margin
    Burn           operating expenses - gross profit
    Runway         cash / monthly burn
    LTV            ARPU x gross margin x customer lifetime
    CAC payback    CAC / monthly gross profit per customer

No AI is involved. Every number below can be worked out by hand, which is
the point: a founder can argue with a score, but not with arithmetic.

Usage:
    from financial_engine import calculate
    result = calculate(reader_output.values)
    print(result.figures)
    print(result.notes)
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Settings. These are our assumptions, not the client's instructions.
# The client has been asked to confirm them; until then these are the
# documented defaults and changing one is a one-line edit.
# Asked 22 Aug 2026, awaiting answer.
# ---------------------------------------------------------------------------

# A twelve month forecast has twelve columns. Which one is "now"?
# We take the first, i.e. the current month rather than a future projection.
MONTH_BASIS = "first"

# Runway longer than this is reported as "beyond the forecast horizon"
# rather than a number, because a five hundred month runway is not a
# meaningful statement about a pre-seed startup.
MAX_MEANINGFUL_RUNWAY_MONTHS = 120


@dataclass
class FinancialResult:
    figures: dict = field(default_factory=dict)   # what we worked out
    notes: list = field(default_factory=list)     # anything a human should know
    missing: list = field(default_factory=list)   # inputs we did not get

    @property
    def is_complete(self):
        return not self.missing


# ---------------------------------------------------------------------------
# The six formulas, one function each.
# Each is small enough to check by hand, which is how they are tested.
# ---------------------------------------------------------------------------

def revenue(customers, arpu):
    """Monthly revenue = customers x average revenue per customer."""
    return customers * arpu


def gross_profit(monthly_revenue, gross_margin):
    """Gross profit = revenue x gross margin."""
    return monthly_revenue * gross_margin


def burn(opex_monthly, monthly_gross_profit):
    """
    Burn = operating expenses - gross profit.

    Positive means the company is losing money each month. Negative means
    it is profitable, and we report that as a profit rather than a burn.
    """
    return opex_monthly - monthly_gross_profit


def runway(cash, monthly_burn):
    """
    Runway = cash / monthly burn, in months.

    Returns None when the company is not burning cash. A profitable company
    does not have a runway, and reporting one would be misleading rather
    than merely wrong.
    """
    if monthly_burn is None or monthly_burn <= 0:
        return None
    return cash / monthly_burn


def lifetime_value(arpu, gross_margin, lifetime_months):
    """
    LTV = ARPU x gross margin x customer lifetime.

    Note this is gross-profit based, not revenue based. A customer paying
    $40 a month at 70% margin is worth $28 a month to the business, not $40.
    """
    return arpu * gross_margin * lifetime_months


def cac_payback(cac, monthly_gross_profit_per_customer):
    """
    CAC payback = CAC / monthly gross profit per customer, in months.

    How long until a customer has repaid what it cost to win them.
    Returns None when a customer generates no gross profit, because the
    answer would be infinite rather than large.
    """
    if not monthly_gross_profit_per_customer:
        return None
    return cac / monthly_gross_profit_per_customer


# ---------------------------------------------------------------------------
# Putting them together
# ---------------------------------------------------------------------------

REQUIRED = ["customers", "arpu", "gross_margin", "opex_monthly", "cash"]
OPTIONAL = ["cac", "lifetime_months"]


def calculate(values):
    """
    Run every calculation we have the inputs for.

    Missing inputs are reported rather than guessed. A founder who did not
    give us a CAC gets no CAC payback figure, not a made up one.
    """
    result = FinancialResult()

    result.missing = [f for f in REQUIRED if values.get(f) is None]
    if result.missing:
        result.notes.append(
            "Cannot calculate the core figures: missing "
            + ", ".join(result.missing)
        )
        return result

    customers = values["customers"]
    arpu = values["arpu"]
    margin = values["gross_margin"]
    opex = values["opex_monthly"]
    cash = values["cash"]

    # --- sanity checks on the inputs themselves ---
    if margin > 1:
        result.notes.append(
            f"Gross margin read as {margin:.2f}, which is above 100%. "
            "Check the source cell."
        )
    if margin < 0:
        result.notes.append("Gross margin is negative: costs exceed revenue.")
    if customers == 0:
        result.notes.append("No paying customers, so revenue is zero.")

    # --- the calculations ---
    monthly_revenue = revenue(customers, arpu)
    monthly_gross_profit = gross_profit(monthly_revenue, margin)
    monthly_burn = burn(opex, monthly_gross_profit)

    result.figures["revenue_monthly"] = monthly_revenue
    result.figures["gross_profit_monthly"] = monthly_gross_profit
    result.figures["burn_monthly"] = monthly_burn
    result.figures["profitable"] = monthly_burn <= 0

    if monthly_burn <= 0:
        result.figures["runway_months"] = None
        result.notes.append(
            "Company is profitable at these figures, so it has no runway "
            f"in the usual sense (monthly profit of {abs(monthly_burn):,.0f})."
        )
    else:
        months = runway(cash, monthly_burn)
        if months > MAX_MEANINGFUL_RUNWAY_MONTHS:
            result.figures["runway_months"] = months
            result.notes.append(
                f"Runway of {months:,.0f} months is beyond any sensible "
                "forecast horizon. Treat with caution."
            )
        else:
            result.figures["runway_months"] = months

    # Gross profit per customer, needed for CAC payback
    if customers:
        gp_per_customer = monthly_gross_profit / customers
        result.figures["gross_profit_per_customer"] = gp_per_customer
    else:
        gp_per_customer = None

    # --- unit economics, only if we have the inputs ---
    lifetime = values.get("lifetime_months")
    cac = values.get("cac")

    if lifetime is not None:
        result.figures["ltv"] = lifetime_value(arpu, margin, lifetime)
    else:
        result.notes.append("No customer lifetime given, so LTV not calculated.")

    if cac is not None and gp_per_customer is not None:
        payback = cac_payback(cac, gp_per_customer)
        result.figures["cac_payback_months"] = payback
        if payback is None:
            result.notes.append(
                "Each customer generates no gross profit, so the acquisition "
                "cost is never repaid."
            )
    elif cac is None:
        result.notes.append("No CAC given, so payback period not calculated.")

    if "ltv" in result.figures and cac:
        result.figures["ltv_to_cac"] = result.figures["ltv"] / cac

    return result


def describe(result):
    """Plain English summary, for the report and for eyeballing during tests."""
    if not result.figures:
        return "No financial figures could be calculated."

    f = result.figures
    lines = [
        f"Monthly revenue        {f['revenue_monthly']:>12,.0f}",
        f"Monthly gross profit   {f['gross_profit_monthly']:>12,.0f}",
    ]
    if f["profitable"]:
        lines.append(f"Monthly profit         {abs(f['burn_monthly']):>12,.0f}")
    else:
        lines.append(f"Monthly burn           {f['burn_monthly']:>12,.0f}")
        if f.get("runway_months") is not None:
            lines.append(f"Runway (months)        {f['runway_months']:>12,.1f}")
    if "ltv" in f:
        lines.append(f"LTV                    {f['ltv']:>12,.0f}")
    if f.get("cac_payback_months") is not None:
        lines.append(f"CAC payback (months)   {f['cac_payback_months']:>12,.1f}")
    if "ltv_to_cac" in f:
        lines.append(f"LTV to CAC             {f['ltv_to_cac']:>11,.1f}x")

    for note in result.notes:
        lines.append(f"  note: {note}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from excel_reader import read_financial_model

    for path in sys.argv[1:]:
        print(f"\n--- {path}")
        extracted = read_financial_model(path)
        print(describe(calculate(extracted.values)))
