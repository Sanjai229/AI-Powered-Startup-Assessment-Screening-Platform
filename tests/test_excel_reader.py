"""
Tests for the Excel reader.

Every file below describes the same company, BookFast, so the correct
answer is known in advance. If the reader returns anything else, it is
wrong, and the test says so.

Run:  python3 test_excel_reader.py
"""

from excel_reader import read_financial_model

# The truth. Every file must produce these seven numbers.
EXPECTED = {
    "customers": 500,
    "arpu": 40,
    "gross_margin": 0.70,
    "opex_monthly": 25000,
    "cash": 180000,
    "cac": 220,
    "lifetime_months": 30,
}

FILES = [
    ("Startup Financial Model", "bookfast_1_startup_model.xlsx"),
    ("Simple SME Projection", "bookfast_2_sme_projection.xlsx"),
    ("Investor Financial Model", "bookfast_3_investor_model.xlsx"),
    ("Messy real-world file", "bookfast_layout_c.xlsx"),
]

TOLERANCE = 0.005   # half a percent, to allow for rounding


def close_enough(got, want):
    if want == 0:
        return abs(got) < 1e-9
    return abs(got - want) / abs(want) <= TOLERANCE


def run():
    failures = []

    for name, path in FILES:
        result = read_financial_model(path)
        problems = []

        for field, want in EXPECTED.items():
            if field not in result.values:
                problems.append(f"{field}: not found")
                continue
            got = result.values[field]
            if not close_enough(got, want):
                problems.append(
                    f"{field}: got {got:,.2f}, expected {want:,.2f} "
                    f"(from {result.found_in[field]})"
                )

        if problems:
            failures.append((name, problems))
            print(f"FAIL  {name}")
            for p in problems:
                print(f"        {p}")
        else:
            print(f"pass  {name}")

    print()
    if failures:
        print(f"{len(failures)} of {len(FILES)} files failed.")
        return 1
    print(f"All {len(FILES)} files passed. Seven fields each, "
          f"{len(FILES) * len(EXPECTED)} checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
