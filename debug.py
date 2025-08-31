
# %%
import re
import pdfplumber  # For extracting tables from PDF
from ics import Calendar, Event  # For creating .ics files
from datetime import datetime
from zoneinfo import ZoneInfo
# zczytanie tekstu z pdfa i podział na linie
pdf_path = r"F:\PC_BIALY\GIT REPOS\flights-schedule-app\20250601_20250731_roster.pdf"
pdf_path = r"F:\PC_BIALY\GIT REPOS\flights-schedule-app\20250817_roster.pdf"
lines = []
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        for line in page.extract_text().split("\n"):
            lines.append(line)
# %%
lines[0]
# %%
text = lines[0]
pattern = r'\b(\d{1,2}[A-Za-z]{3}\d{2})\b'
match = re.search(pattern, text)
if match:
    date_value = match.group(1)  # Returns: "17Aug25"
    print(date_value)
# %%
print(lines[0])
MIN_CUTOFF_PATTERN = re.compile(r'\b(\d{1,2}[A-Za-z]{3}\d{2})\b')
match = MIN_CUTOFF_PATTERN.match(text)
print(match)
# %%
import re

# Compile the regex pattern
date_pattern = re.compile(r'\b(\d{1,2}[A-Za-z]{3}\d{2})\b')

# Your text
text = 'Individual plan NetLine/Crew(LOT) printedbyCREWLINK 17Aug25 09:13Page1'

# Use the compiled pattern
match = date_pattern.search(text)

if match:
    date_value = match.group(1)  # Returns: "17Aug25"
    print(datetime.strptime(date_value, "%d%b%y"))

# %%
