# AI Engine — extraction, financial calculation and contradiction checking

Part of the MamakScore AI evaluation engine, built by team PG-S2-29.

This part of the system reads a founder's financial model, works out the
figures an investor cares about, and checks whether the pitch deck's claims
agree with the founder's own numbers.

No AI is used anywhere in this code. Every figure here is plain arithmetic,
so any result can be checked by hand and defended to a founder who disagrees
with it.

---

## What is in here

| File | What it does |
|---|---|
| `excel_reader.py` | Opens a founder's spreadsheet and pulls out the seven numbers the engine needs, whatever layout the founder used |
| `financial_engine.py` | The six calculations from section 12 of the client planning document |
| `contradiction_checker.py` | Compares what the deck claims against what the spreadsheet supports |
| `build_models.py` | Generates the three client-named test spreadsheets |
| `layout_c.py` | Generates the deliberately unstructured test spreadsheet |
| `tests/` | Three test suites, 73 checks |
| `testdata/` | Synthetic test files for a fake company called BookFast |

---

## Running it

Install the one dependency:

```
pip install -r requirements.txt
```

Run all three test suites from the repository root:

```
python tests/test_excel_reader.py
python tests/test_financial_engine.py
python tests/test_contradiction_checker.py
```

Run the whole pipeline on a spreadsheet:

```
python financial_engine.py testdata/bookfast_1_startup_model.xlsx
```

Run the contradiction checker on a deck and a spreadsheet together:

```
python contradiction_checker.py testdata/bookfast_deck.txt testdata/bookfast_1_startup_model.xlsx
```

---

## The seven numbers

Everything downstream depends on these being found correctly:

`customers`, `arpu` (average revenue per customer per month), `gross_margin`,
`opex_monthly`, `cash`, `cac` (cost to acquire a customer), and
`lifetime_months`.

The reader records the source cell for every number it finds, so any figure
in a report can be traced back to the cell it came from.

## The six calculations

From section 12 of the client planning document:

```
Revenue        customers x average revenue per customer
Gross profit   revenue x gross margin
Burn           operating expenses - gross profit
Runway         cash / monthly burn
LTV            ARPU x gross margin x customer lifetime
CAC payback    CAC / monthly gross profit per customer
```

---

## Test data

All four spreadsheets describe the same fake company, BookFast, with the same
underlying figures. That is deliberate: the correct answer is known in
advance, so any extraction error shows up immediately.

| File | Format |
|---|---|
| `bookfast_1_startup_model.xlsx` | Startup Financial Model — revenue forecast, COGS, opex, EBITDA, cash flow, funding requirements |
| `bookfast_2_sme_projection.xlsx` | Simple SME Projection — monthly revenue, expenses, P&L, cash balance |
| `bookfast_3_investor_model.xlsx` | Investor Financial Model — unit economics, LTV/CAC, three-statement projection, scenarios |
| `bookfast_layout_c.xlsx` | Unstructured — no clear labels, figures buried in a third sheet, margin stored as text |
| `bookfast_deck.txt` | Pitch deck text with four deliberate contradictions |

The first three formats are the ones the client named on 25 August 2026. The
fourth represents a founder who follows no format at all.

These files are synthetic. The client confirmed that no real applicant
documents are available, and course rules prohibit using confidential
business documents without written permission.

---

## Decisions still open with the client

Both are settings at the top of the relevant file, not assumptions buried in
the logic. If the client answers differently, each is a one-line change.

**Which forecast month counts as current.** A twelve month forecast has twelve
columns. We take the first. See `MONTH_BASIS` in `financial_engine.py`.

**How far apart two numbers must be before it counts as a contradiction.** We
use 20%. Below that we assume rounding or a different reporting date rather
than exaggeration. See `DIFFERENCE_THRESHOLD` in `contradiction_checker.py`.

A third question — what the engine should do when a founder submits a deck
but no financial model — is with the client. At present the engine reports
the missing inputs rather than guessing at them.

---

## Known limitations

**Monthly versus annual operating expenses.** The reader prefers labels that
say "monthly". A founder who writes only "Operating expenses" on an annual
sheet, and nowhere else, could still be misread by a factor of twelve.

**Claims split across sentences.** The contradiction checker reads one
sentence at a time. A claim spread over two slides will not be matched.

**Deck text only.** The checker needs text. Pitch decks exported from design
tools are often images with no text layer at all, which is the PDF reader's
problem to solve before this code sees anything.

---

## Testing approach

Every expected number in the test suites was worked out by hand before the
code was written, and the working is printed next to each result:

```
pass  BookFast runway    got 16.363636  expected 16.3636   [180,000 / 11,000]
```

That order matters. A test written by running the code and copying its answer
proves only that the code agrees with itself.

Three extraction bugs were found this way, and all three produced
plausible-looking numbers rather than errors: closing cash read instead of
opening cash, annual operating expenses read instead of monthly, and LTV
calculated from the acquisition cost instead of gross profit. None of them
would have been noticed without knowing the right answer in advance.
