"""
Builds the three financial model formats the client named, all for the same
fake company (BookFast) so the correct answer is known in every case.

    1. Startup Financial Model   revenue forecast, COGS, opex, EBITDA,
                                 cash flow, funding requirements
    2. Simple SME Projection     monthly revenue, monthly expenses, P&L,
                                 cash balance
    3. Investor Financial Model  revenue assumptions, unit economics,
                                 customer acquisition, LTV/CAC,
                                 three-statement projections, scenarios

The seven core facts are identical in all three:
    500 customers, $40 each per month, 70% gross margin, $25,000 monthly
    opex, $180,000 cash, $220 CAC, 30 month customer lifetime.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ---------- shared styling ----------
F = "Arial"
BLUE = Font(name=F, size=11, color="0000FF")          # typed input
BLACK = Font(name=F, size=11)                          # formula
BOLD = Font(name=F, size=11, bold=True)
TITLE = Font(name=F, size=14, bold=True)
SUB = Font(name=F, size=11, bold=True, color="1F4E79")
NOTE = Font(name=F, size=9, italic=True, color="595959")
HDR = PatternFill("solid", fgColor="D9D9D9")
BAND = PatternFill("solid", fgColor="EDF3F8")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(top=thin, bottom=thin, left=thin, right=thin)
TOPLINE = Border(top=Side(style="thin", color="404040"))

CUR = '$#,##0;($#,##0);-'
CUR2 = '$#,##0.00;($#,##0.00);-'
PCT = '0.0%'
NUM = '#,##0;(#,##0);-'
DEC = '0.0'

MONTHS = ["Aug 26", "Sep 26", "Oct 26", "Nov 26", "Dec 26", "Jan 27",
          "Feb 27", "Mar 27", "Apr 27", "May 27", "Jun 27", "Jul 27"]

CUSTOMERS_M1 = 500
GROWTH = 1.08
ARPU = 40
GM = 0.70
OPEX_M1 = 25000
OPEX_GROWTH = 1.03
CASH = 180000
CAC = 220
LIFETIME = 30


def header_row(ws, row, first_col, labels, width=12):
    for i, label in enumerate(labels):
        c = ws.cell(row, first_col + i, label)
        c.font = BOLD
        c.fill = HDR
        c.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(first_col + i)].width = width


def month_header(ws, row, first_col=2):
    ws.cell(row, 1, "").font = BOLD
    header_row(ws, row, first_col, MONTHS)


def series(ws, row, label, values_or_formula, fmt, first_col=2,
           font=BLACK, bold_label=False, band=False):
    """Write a labelled row across the twelve month columns."""
    lc = ws.cell(row, 1, label)
    lc.font = BOLD if bold_label else BLACK
    if band:
        lc.fill = BAND
    for i in range(12):
        col = get_column_letter(first_col + i)
        value = (values_or_formula(i, col) if callable(values_or_formula)
                 else values_or_formula[i])
        c = ws.cell(row, first_col + i, value)
        c.font = font
        c.number_format = fmt
        c.border = BOX
        if band:
            c.fill = BAND


def customer_series():
    out, n = [], CUSTOMERS_M1
    for _ in range(12):
        out.append(n)
        n = round(n * GROWTH)
    return out


def opex_series():
    out, n = [], OPEX_M1
    for _ in range(12):
        out.append(n)
        n = round(n * OPEX_GROWTH)
    return out


# =====================================================================
# 1. STARTUP FINANCIAL MODEL
# =====================================================================
def build_startup_model(path):
    wb = Workbook()

    # --- Assumptions ---
    ws = wb.active
    ws.title = "Assumptions"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 44

    ws["A1"] = "BookFast Pty Ltd — Startup Financial Model"
    ws["A1"].font = TITLE
    ws["A2"] = "Salon booking software. Twelve month plan from August 2026."
    ws["A2"].font = NOTE
    ws["A3"] = "Synthetic test file for the MamakScore AI engine. Not a real company."
    ws["A3"].font = NOTE

    ws["A5"] = "Key assumptions"
    ws["A5"].font = SUB
    header_row(ws, 6, 1, ["Assumption", "Value", "Basis"], width=16)
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["C"].width = 44

    assumptions = [
        ("Paying customers at start", CUSTOMERS_M1, NUM, "Salons on a paid plan at 1 Aug 2026"),
        ("Monthly customer growth rate", GROWTH - 1, PCT, "Average of the last three months"),
        ("Average revenue per customer", ARPU, CUR, "Single flat subscription tier"),
        ("Gross margin", GM, PCT, "After hosting and card processing fees"),
        ("Operating expenses at start", OPEX_M1, CUR, "Salaries, marketing, rent, tools"),
        ("Monthly opex growth rate", OPEX_GROWTH - 1, PCT, "Two hires planned in the period"),
        ("Opening cash balance", CASH, CUR, "Bank balance at 1 Aug 2026"),
        ("Customer acquisition cost", CAC, CUR, "Sales and marketing / new customers"),
        ("Average customer lifetime (months)", LIFETIME, NUM, "Founder estimate, not yet observed"),
    ]
    r = 7
    for label, val, fmt, basis in assumptions:
        ws.cell(r, 1, label).font = BLACK
        c = ws.cell(r, 2, val)
        c.font = BLUE
        c.number_format = fmt
        c.border = BOX
        ws.cell(r, 3, basis).font = NOTE
        r += 1
    ws.cell(r + 1, 1, "Blue figures are typed in. Every other sheet is formulas.").font = NOTE

    # --- Revenue Forecast ---
    rv = wb.create_sheet("Revenue Forecast")
    rv.column_dimensions["A"].width = 34
    rv["A1"] = "Revenue forecast"
    rv["A1"].font = TITLE
    month_header(rv, 3)
    series(rv, 4, "Paying customers", customer_series(), NUM, font=BLUE)
    series(rv, 5, "Average revenue per customer",
           lambda i, col: "=Assumptions!$B$9", CUR, font=BLACK)
    series(rv, 6, "Revenue", lambda i, col: f"={col}4*{col}5", CUR,
           bold_label=True, band=True)
    series(rv, 7, "Cost of goods sold",
           lambda i, col: f"={col}6*(1-Assumptions!$B$10)", CUR)
    series(rv, 8, "Gross profit", lambda i, col: f"={col}6-{col}7", CUR,
           bold_label=True, band=True)
    rv.cell(10, 1, "Cost of goods sold is hosting, SMS and payment fees.").font = NOTE

    # --- Operating Expenses ---
    ox = wb.create_sheet("Operating Expenses")
    ox.column_dimensions["A"].width = 34
    ox["A1"] = "Operating expenses"
    ox["A1"].font = TITLE
    month_header(ox, 3)
    opex = opex_series()
    salaries = [round(v * 0.62) for v in opex]
    marketing = [round(v * 0.22) for v in opex]
    other = [opex[i] - salaries[i] - marketing[i] for i in range(12)]
    series(ox, 4, "Salaries and contractors", salaries, CUR, font=BLUE)
    series(ox, 5, "Marketing", marketing, CUR, font=BLUE)
    series(ox, 6, "Rent, tools and other", other, CUR, font=BLUE)
    series(ox, 7, "Total operating expenses",
           lambda i, col: f"=SUM({col}4:{col}6)", CUR, bold_label=True, band=True)

    # --- Profit and Loss ---
    pl = wb.create_sheet("P&L")
    pl.column_dimensions["A"].width = 34
    pl["A1"] = "Profit and loss"
    pl["A1"].font = TITLE
    month_header(pl, 3)
    series(pl, 4, "Revenue", lambda i, col: f"='Revenue Forecast'!{col}6", CUR)
    series(pl, 5, "Cost of goods sold", lambda i, col: f"='Revenue Forecast'!{col}7", CUR)
    series(pl, 6, "Gross profit", lambda i, col: f"={col}4-{col}5", CUR, bold_label=True)
    series(pl, 7, "Operating expenses",
           lambda i, col: f"='Operating Expenses'!{col}7", CUR)
    series(pl, 8, "EBITDA", lambda i, col: f"={col}6-{col}7", CUR,
           bold_label=True, band=True)
    series(pl, 9, "EBITDA margin",
           lambda i, col: f"=IFERROR({col}8/{col}4,0)", PCT)
    pl.cell(11, 1, "No depreciation or interest in the period, so EBITDA equals operating profit.").font = NOTE

    # --- Cash Flow ---
    cf = wb.create_sheet("Cash Flow")
    cf.column_dimensions["A"].width = 34
    cf["A1"] = "Cash flow"
    cf["A1"].font = TITLE
    month_header(cf, 3)
    series(cf, 4, "Opening cash",
           lambda i, col: ("=Assumptions!$B$13" if i == 0
                           else f"={get_column_letter(1+i)}7"), CUR)
    series(cf, 5, "Cash from operations", lambda i, col: f"='P&L'!{col}8", CUR)
    series(cf, 6, "Net burn", lambda i, col: f"=-{col}5", CUR, bold_label=True)
    series(cf, 7, "Closing cash", lambda i, col: f"={col}4+{col}5", CUR,
           bold_label=True, band=True)
    cf.cell(9, 1, "Net burn is positive when the company is losing money.").font = NOTE

    # --- Funding Requirements ---
    fr = wb.create_sheet("Funding Requirements")
    fr.column_dimensions["A"].width = 40
    fr.column_dimensions["B"].width = 18
    fr.column_dimensions["C"].width = 44
    fr["A1"] = "Funding requirements"
    fr["A1"].font = TITLE
    header_row(fr, 3, 1, ["Item", "Value", "Note"], width=18)
    fr.column_dimensions["A"].width = 40
    fr.column_dimensions["C"].width = 44

    items = [
        ("Monthly net burn (month 1)", "='Cash Flow'!B6", CUR,
         "Operating expenses less gross profit"),
        ("Runway at current burn (months)",
         "=IFERROR(Assumptions!B13/'Cash Flow'!B6,\"n/a\")", DEC,
         "Opening cash divided by month one burn"),
        ("Cash at month 12", "='Cash Flow'!M7", CUR, "Closing balance on the cash flow"),
        ("Amount sought", 500000, CUR, "Pre-seed round"),
        ("Use of funds — engineering", 250000, CUR, "Two engineers for eighteen months"),
        ("Use of funds — sales and marketing", 175000, CUR, "Channel partnerships and paid acquisition"),
        ("Use of funds — working capital", 75000, CUR, "Buffer"),
    ]
    r = 4
    for label, val, fmt, note in items:
        fr.cell(r, 1, label).font = BLACK
        c = fr.cell(r, 2, val)
        c.font = BLUE if isinstance(val, (int, float)) else BLACK
        c.number_format = fmt
        c.border = BOX
        fr.cell(r, 3, note).font = NOTE
        r += 1
    fr.cell(r, 1, "Total use of funds").font = BOLD
    tc = fr.cell(r, 2, "=SUM(B8:B10)")
    tc.font = BOLD
    tc.number_format = CUR
    tc.border = TOPLINE

    wb.save(path)


# =====================================================================
# 2. SIMPLE SME PROJECTION
# =====================================================================
def build_sme_projection(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly Projection"
    ws.column_dimensions["A"].width = 32

    ws["A1"] = "BookFast — monthly projection"
    ws["A1"].font = TITLE
    ws["A2"] = "Synthetic test file for the MamakScore AI engine. Not a real company."
    ws["A2"].font = NOTE

    ws["A4"] = "Revenue"
    ws["A4"].font = SUB
    month_header(ws, 5)
    series(ws, 6, "Customers", customer_series(), NUM, font=BLUE)
    series(ws, 7, "Monthly fee per customer", [ARPU] * 12, CUR, font=BLUE)
    series(ws, 8, "Monthly revenue", lambda i, col: f"={col}6*{col}7", CUR,
           bold_label=True, band=True)

    ws["A10"] = "Expenses"
    ws["A10"].font = SUB
    opex = opex_series()
    series(ws, 11, "Direct costs", lambda i, col: f"={col}8*0.3", CUR)
    series(ws, 12, "Wages", [round(v * 0.62) for v in opex], CUR, font=BLUE)
    series(ws, 13, "Advertising", [round(v * 0.22) for v in opex], CUR, font=BLUE)
    series(ws, 14, "Rent and other",
           [opex[i] - round(opex[i] * 0.62) - round(opex[i] * 0.22) for i in range(12)],
           CUR, font=BLUE)
    series(ws, 15, "Monthly expenses", lambda i, col: f"=SUM({col}12:{col}14)", CUR,
           bold_label=True, band=True)

    ws["A17"] = "Profit and loss"
    ws["A17"].font = SUB
    series(ws, 18, "Gross profit", lambda i, col: f"={col}8-{col}11", CUR)
    series(ws, 19, "Net profit or loss", lambda i, col: f"={col}18-{col}15", CUR,
           bold_label=True, band=True)

    ws["A21"] = "Cash"
    ws["A21"].font = SUB
    series(ws, 22, "Opening balance",
           lambda i, col: (CASH if i == 0 else f"={get_column_letter(1+i)}23"), CUR,
           font=BLUE)
    series(ws, 23, "Cash balance", lambda i, col: f"={col}22+{col}19", CUR,
           bold_label=True, band=True)

    ws["A25"] = "Other figures"
    ws["A25"].font = SUB
    extras = [
        ("Gross margin", GM, PCT),
        ("Cost to win a customer", CAC, CUR),
        ("Average months a customer stays", LIFETIME, NUM),
    ]
    r = 26
    for label, val, fmt in extras:
        ws.cell(r, 1, label).font = BLACK
        c = ws.cell(r, 2, val)
        c.font = BLUE
        c.number_format = fmt
        c.border = BOX
        r += 1

    wb.save(path)


# =====================================================================
# 3. INVESTOR FINANCIAL MODEL
# =====================================================================
def build_investor_model(path):
    wb = Workbook()

    # --- Revenue Assumptions ---
    ra = wb.active
    ra.title = "Revenue Assumptions"
    ra.column_dimensions["A"].width = 38
    ra.column_dimensions["B"].width = 16
    ra.column_dimensions["C"].width = 42

    ra["A1"] = "BookFast Pty Ltd — Investor Financial Model"
    ra["A1"].font = TITLE
    ra["A2"] = "Synthetic test file for the MamakScore AI engine. Not a real company."
    ra["A2"].font = NOTE

    ra["A4"] = "Revenue assumptions"
    ra["A4"].font = SUB
    header_row(ra, 5, 1, ["Assumption", "Value", "Comment"], width=16)
    ra.column_dimensions["A"].width = 38
    ra.column_dimensions["C"].width = 42

    rows = [
        ("Customers", CUSTOMERS_M1, NUM, "Paying salons at 1 Aug 2026"),
        ("ARPU (monthly)", ARPU, CUR, "Average revenue per user"),
        ("Monthly growth", GROWTH - 1, PCT, "Compounding"),
        ("Gross margin", GM, PCT, "After variable delivery costs"),
        ("Monthly churn", 0.033, PCT, "Implied by a thirty month life"),
        ("Operating expenses (monthly)", OPEX_M1, CUR, "Fixed cost base"),
        ("Cash on hand", CASH, CUR, "Bank balance"),
    ]
    r = 6
    for label, val, fmt, note in rows:
        ra.cell(r, 1, label).font = BLACK
        c = ra.cell(r, 2, val)
        c.font = BLUE
        c.number_format = fmt
        c.border = BOX
        ra.cell(r, 3, note).font = NOTE
        r += 1

    # --- Unit Economics ---
    ue = wb.create_sheet("Unit Economics")
    ue.column_dimensions["A"].width = 40
    ue.column_dimensions["B"].width = 16
    ue.column_dimensions["C"].width = 48
    ue["A1"] = "Unit economics"
    ue["A1"].font = TITLE
    header_row(ue, 3, 1, ["Metric", "Value", "Calculation"], width=16)
    ue.column_dimensions["A"].width = 40
    ue.column_dimensions["C"].width = 48

    # Row 3 is the header, so data starts at row 4:
    #   B4 CAC, B5 lifetime, B6 gross profit per customer,
    #   B7 LTV, B8 LTV/CAC, B9 CAC payback
    ue_rows = [
        ("Customer acquisition cost (CAC)", CAC, CUR, "Sales and marketing spend / new customers", True),
        ("Average customer lifetime (months)", LIFETIME, NUM, "1 / monthly churn", True),
        ("Gross profit per customer (monthly)",
         "='Revenue Assumptions'!B7*'Revenue Assumptions'!B9", CUR2,
         "ARPU x gross margin", False),
        ("Lifetime value (LTV)", "=B6*B5", CUR, "Monthly gross profit x lifetime", False),
        ("LTV to CAC ratio", "=IFERROR(B7/B4,\"n/a\")", '0.0"x"', "LTV / CAC", False),
        ("CAC payback (months)", "=IFERROR(B4/B6,\"n/a\")", DEC,
         "CAC / monthly gross profit per customer", False),
    ]
    r = 4
    for label, val, fmt, calc, is_input in ue_rows:
        ue.cell(r, 1, label).font = BLACK
        c = ue.cell(r, 2, val)
        c.font = BLUE if is_input else BLACK
        c.number_format = fmt
        c.border = BOX
        ue.cell(r, 3, calc).font = NOTE
        r += 1

    ue.cell(12, 1, "Customer acquisition").font = SUB
    header_row(ue, 13, 1, ["Quarter", "New customers", "Spend", "Blended CAC"], width=16)
    ue.column_dimensions["A"].width = 40
    acq = [("Q1 FY27", 130, 28600), ("Q2 FY27", 168, 36960),
           ("Q3 FY27", 218, 47960), ("Q4 FY27", 282, 62040)]
    r = 14
    for q, new, spend in acq:
        ue.cell(r, 1, q).font = BLACK
        for col, val, fmt in ((2, new, NUM), (3, spend, CUR)):
            c = ue.cell(r, col, val)
            c.font = BLUE
            c.number_format = fmt
            c.border = BOX
        c = ue.cell(r, 4, f"=IFERROR(C{r}/B{r},0)")
        c.font = BLACK
        c.number_format = CUR
        c.border = BOX
        r += 1

    # --- Three Statement ---
    ts = wb.create_sheet("Three Statement")
    ts.column_dimensions["A"].width = 34
    ts["A1"] = "Three statement projection"
    ts["A1"].font = TITLE
    ts["A2"] = "Annual view. Year 1 is the twelve months from August 2026."
    ts["A2"].font = NOTE
    header_row(ts, 4, 2, ["Year 1", "Year 2", "Year 3"], width=16)

    def yr(row, label, vals, fmt, bold=False):
        c = ts.cell(row, 1, label)
        c.font = BOLD if bold else BLACK
        for i, v in enumerate(vals):
            cc = ts.cell(row, 2 + i, v)
            cc.font = BLACK if isinstance(v, str) else BLUE
            cc.number_format = fmt
            cc.border = BOX

    ts.cell(6, 1, "Profit and loss").font = SUB
    yr(7, "Revenue", [377000, 782000, 1520000], CUR)
    yr(8, "Cost of goods sold", ["=B7*0.3", "=C7*0.3", "=D7*0.3"], CUR)
    yr(9, "Gross profit", ["=B7-B8", "=C7-C8", "=D7-D8"], CUR, bold=True)
    yr(10, "Operating expenses", [355000, 610000, 980000], CUR)
    yr(11, "EBITDA", ["=B9-B10", "=C9-C10", "=D9-D10"], CUR, bold=True)

    ts.cell(13, 1, "Cash flow").font = SUB
    yr(14, "Opening cash", [CASH, "=B17", "=C17"], CUR)
    yr(15, "Operating cash flow", ["=B11", "=C11", "=D11"], CUR)
    yr(16, "Capital raised", [500000, 0, 0], CUR)
    yr(17, "Closing cash", ["=B14+B15+B16", "=C14+C15+C16", "=D14+D15+D16"], CUR, bold=True)

    ts.cell(19, 1, "Balance sheet").font = SUB
    yr(20, "Cash", ["=B17", "=C17", "=D17"], CUR)
    yr(21, "Receivables", [31000, 65000, 127000], CUR)
    yr(22, "Total assets", ["=B20+B21", "=C20+C21", "=D20+D21"], CUR, bold=True)
    yr(23, "Payables", [42000, 71000, 115000], CUR)
    yr(24, "Equity", ["=B22-B23", "=C22-C23", "=D22-D23"], CUR, bold=True)

    # --- Scenarios ---
    sc = wb.create_sheet("Scenario Analysis")
    sc.column_dimensions["A"].width = 34
    sc["A1"] = "Scenario analysis"
    sc["A1"].font = TITLE
    header_row(sc, 3, 2, ["Downside", "Base", "Upside"], width=16)

    def scen(row, label, vals, fmt, bold=False):
        c = sc.cell(row, 1, label)
        c.font = BOLD if bold else BLACK
        for i, v in enumerate(vals):
            cc = sc.cell(row, 2 + i, v)
            cc.font = BLACK if isinstance(v, str) else BLUE
            cc.number_format = fmt
            cc.border = BOX

    scen(4, "Monthly growth rate", [0.03, 0.08, 0.14], PCT)
    scen(5, "Monthly churn", [0.05, 0.033, 0.02], PCT)
    scen(6, "Gross margin", [0.62, 0.70, 0.76], PCT)
    scen(7, "Year 1 revenue", [268000, 377000, 542000], CUR)
    scen(8, "Year 1 EBITDA", [-210000, -91100, 14000], CUR, bold=True)
    scen(9, "Year 1 closing cash",
         ["=180000+500000+B8", "=180000+500000+C8", "=180000+500000+D8"], CUR)
    sc.cell(11, 1, "All scenarios assume the $500k round closes in year one.").font = NOTE

    wb.save(path)


if __name__ == "__main__":
    build_startup_model("/home/claude/bookfast_1_startup_model.xlsx")
    build_sme_projection("/home/claude/bookfast_2_sme_projection.xlsx")
    build_investor_model("/home/claude/bookfast_3_investor_model.xlsx")
    print("built 3 files")
