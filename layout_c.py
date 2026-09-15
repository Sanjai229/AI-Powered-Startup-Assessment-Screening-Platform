from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

ARI = "Calibri"
B = Font(name=ARI, size=11)
BOLD = Font(name=ARI, size=11, bold=True)
BIG = Font(name=ARI, size=16, bold=True, color="C00000")
NOTE = Font(name=ARI, size=9, italic=True, color="808080")
FILL = PatternFill("solid", fgColor="FFF2CC")

wb = Workbook()

# --- Sheet 1: a cover page with nothing useful ---
cover = wb.active
cover.title = "Cover"
cover.column_dimensions["A"].width = 50
cover.merge_cells("A2:D3")
cover["A2"] = "BookFast"
cover["A2"].font = BIG
cover["A2"].alignment = Alignment(horizontal="center", vertical="center")
cover["A5"] = "Investor pack — August 2026"
cover["A5"].font = BOLD
cover["A7"] = "Prepared by the founding team"
cover["A7"].font = B
cover["A9"] = "Test file for the MamakScore AI engine. Not a real company."
cover["A9"].font = NOTE

# --- Sheet 2: notes, chatty, no clean labels ---
notes = wb.create_sheet("Notes")
notes.column_dimensions["A"].width = 90
notes["A1"] = "Business notes"
notes["A1"].font = BOLD
lines = [
    "We launched in Feb 2026 and things are going really well.",
    "We now have over 5,000 salons using BookFast across Australia.",
    "Everyone pays the same flat rate of forty dollars a month.",
    "Our margins are strong, roughly 70 percent after hosting and card fees.",
    "We spend about $25k a month running the business.",
    "We raised a small round and still have $180k in the bank.",
    "It costs us around $220 to sign up a new salon.",
    "Salons typically stay with us for two and a half years.",
]
for i, t in enumerate(lines, start=3):
    notes.cell(i, 1, t).font = B

# --- Sheet 3: the actual numbers, buried, merged, unlabelled headers ---
s = wb.create_sheet("Sheet3")
s.column_dimensions["A"].width = 4
s.column_dimensions["B"].width = 30
s.column_dimensions["C"].width = 6
s.column_dimensions["D"].width = 16

s.merge_cells("B2:D2")
s["B2"] = "Summary of key figures"
s["B2"].font = BOLD
s["B2"].alignment = Alignment(horizontal="center")
s["B2"].fill = FILL

data = [
    ("No. of active accounts", 500),
    ("Sub fee p/m", 40),
    ("GM %", "70%"),
    ("Opex p/m", 25000),
    ("Cash at bank", 180000),
    ("CAC", 220),
    ("Avg life (mths)", 30),
]
r = 4
for label, val in data:
    s.cell(r, 2, label).font = B
    c = s.cell(r, 4, val)
    c.font = B
    r += 2

s["B20"] = "figures as at 31 July, unaudited"
s["B20"].font = NOTE

wb.save("/home/claude/bookfast_layout_c.xlsx")
print("written C")
