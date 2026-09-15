"""
Excel reader for the MamakScore AI engine.

Opens a founder's financial model and pulls out the seven numbers the
financial engine needs, whatever layout the founder used.

The seven numbers:
    customers            how many paying customers
    arpu                 average revenue per customer per month
    gross_margin         as a fraction, so 0.70 means 70%
    opex_monthly         monthly operating expenses
    cash                 money in the bank
    cac                  cost to acquire one customer
    lifetime_months      how long a customer stays

Usage:
    from excel_reader import read_financial_model
    result = read_financial_model("bookfast_layout_a.xlsx")
    print(result.values)
    print(result.found_in)
"""

from dataclasses import dataclass, field
import re
from openpyxl import load_workbook


# Every spelling we have seen for each of the seven numbers.
# Add to these lists as new founder spreadsheets turn up.
LABELS = {
    "customers": [
        "customers", "paying customers", "no. of active accounts",
        "active accounts", "number of customers", "subscribers",
        "active users", "paying users", "accounts",
    ],
    "arpu": [
        "average revenue per customer", "monthly fee per customer",
        "sub fee p/m", "subscription fee", "arpu", "price per customer",
        "average revenue per user", "monthly fee", "revenue per customer",
    ],
    "gross_margin": [
        "gross margin", "gm %", "gm", "margin", "gross margin %",
    ],
    # Monthly wordings come first. A three-statement sheet also says
    # "Operating expenses" but means the annual figure, which would be
    # twelve times too big if it won.
    "opex_monthly": [
        "operating expenses monthly", "monthly operating expenses",
        "operating expenses at start", "opex p/m", "monthly opex",
        "monthly expenses", "operating expenses", "opex",
        "operating costs", "running costs",
    ],
    # Order matters. See pick_best_match: earlier entries win.
    # 'opening cash' is the money on hand today; 'closing cash' is what is
    # left after a month of burn, so it must never outrank the others.
    "cash": [
        "opening cash", "opening cash balance", "opening balance",
        "cash in bank", "cash at bank", "cash on hand", "bank balance",
        "cash balance", "cash", "closing cash", "closing balance",
    ],
    "cac": [
        "customer acquisition cost", "cac", "cost to acquire one customer",
        "cost to win a customer", "cost to win a new customer",
        "acquisition cost", "cost per acquisition", "blended cac",
    ],
    "lifetime_months": [
        "average customer lifetime", "expected customer lifetime",
        "average months a customer stays", "months a customer stays",
        "avg life mths", "customer lifetime", "avg life", "lifetime",
    ],
}

# Which fields must be a fraction between 0 and 1
FRACTION_FIELDS = {"gross_margin"}


@dataclass
class ExtractionResult:
    """What the reader hands back."""
    values: dict = field(default_factory=dict)      # the seven numbers
    found_in: dict = field(default_factory=dict)    # where each one came from
    missing: list = field(default_factory=list)     # anything not found
    text_by_sheet: dict = field(default_factory=dict)  # prose, for the checker

    @property
    def is_complete(self):
        return not self.missing


def normalise(text):
    """Lowercase, strip punctuation and spare spaces, so labels compare fairly."""
    if text is None:
        return ""
    text = str(text).lower().strip()
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"[^a-z0-9%/. ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def to_number(raw, field_name):
    """
    Turn a cell value into a number.

    Founders write '70%' as text, '$25,000' with symbols, and '25k' as
    shorthand. This copes with all three and returns None if it cannot.
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        value = float(raw)
        # A margin typed as 70 rather than 0.70
        if field_name in FRACTION_FIELDS and value > 1:
            value = value / 100
        return value

    text = str(raw).strip().lower()
    if not text:
        return None

    is_percent = "%" in text
    multiplier = 1.0
    if re.search(r"\d\s*k\b", text):
        multiplier = 1_000
    elif re.search(r"\d\s*m\b", text):
        multiplier = 1_000_000

    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if cleaned in ("", "-", ".", "-."):
        return None

    try:
        value = float(cleaned) * multiplier
    except ValueError:
        return None

    if is_percent or (field_name in FRACTION_FIELDS and value > 1):
        value = value / 100
    return value


def match_rank(cell_text, candidates):
    """
    How well this cell's text matches a field, as a rank. Lower is better.

    Returns None when nothing matches. Ranking beats first-match-wins:
    'Closing cash' should never outrank 'Opening cash' just because it
    happens to sit higher up the sheet.
    """
    if not cell_text:
        return None
    best = None
    for position, candidate in enumerate(candidates):
        if cell_text == candidate:
            quality = 0                    # exact label
        elif cell_text.startswith(candidate + " "):
            quality = 1                    # label plus extra words
        elif candidate in cell_text and len(candidate) > 3:
            quality = 2                    # label buried in a longer phrase
        else:
            continue
        # Priority dominates. 'Opening cash at 1 Aug 2026' must beat an
        # exact match on 'Closing cash', which sits lower in the list.
        score = position * 1000 + quality
        if best is None or score < best:
            best = score
    return best


def first_number_to_the_right(sheet, row, start_col, field_name, max_look=14):
    """
    Walk right along a row until a usable number appears.

    Layout A puts the value one cell to the right. Layout B has twelve
    monthly columns, and the first one is the current month. Layout C
    leaves a gap column. Walking right handles all three.
    """
    for col in range(start_col + 1, min(start_col + 1 + max_look, sheet.max_column + 1)):
        value = to_number(sheet.cell(row, col).value, field_name)
        if value is not None:
            return value, sheet.cell(row, col).coordinate
    return None, None


def read_financial_model(path):
    """Open a spreadsheet and pull out the seven numbers."""
    workbook = load_workbook(path, data_only=True)
    result = ExtractionResult()
    best_rank = {}

    for sheet in workbook.worksheets:
        prose = []

        for row in sheet.iter_rows():
            for cell in row:
                raw = cell.value
                if raw is None:
                    continue

                # Collect sentences for the contradiction checker later
                if isinstance(raw, str) and len(raw.split()) >= 5:
                    prose.append(raw.strip())

                cell_text = normalise(raw)
                if not cell_text:
                    continue

                for field_name, candidates in LABELS.items():
                    rank = match_rank(cell_text, candidates)
                    if rank is None:
                        continue
                    # Keep the best-ranked match seen anywhere in the workbook
                    if field_name in best_rank and best_rank[field_name] <= rank:
                        continue

                    value, coordinate = first_number_to_the_right(
                        sheet, cell.row, cell.column, field_name
                    )
                    if value is not None:
                        best_rank[field_name] = rank
                        result.values[field_name] = value
                        result.found_in[field_name] = f"{sheet.title}!{coordinate}"

        if prose:
            result.text_by_sheet[sheet.title] = prose

    result.missing = [f for f in LABELS if f not in result.values]
    return result


if __name__ == "__main__":
    import sys
    for path in sys.argv[1:]:
        print(f"\n--- {path}")
        r = read_financial_model(path)
        for name in LABELS:
            if name in r.values:
                print(f"  {name:18} {r.values[name]:>12,.2f}   from {r.found_in[name]}")
            else:
                print(f"  {name:18} {'NOT FOUND':>12}")
        if r.missing:
            print(f"  missing: {r.missing}")
