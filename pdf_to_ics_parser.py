# %%
import pdfplumber  # For extracting tables from PDF
from ics import Calendar, Event  # For creating .ics files
from datetime import datetime
# %%
def extract_events_from_pdf(pdf_path):
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for line in page.extract_text().split("\n"):
                lines.append(line)
    period_start = datetime.strptime(
        lines[1].split(" ")[1],
        "%d%b%y"
    )
    period_end = datetime.strptime(
        lines[1].split(" ")[2],
        "%d%b%y"
    )
    header = lines[3].split(" ")

    return events

def create_ics_file(events, output_path):
    calendar = Calendar()
    for event_data in events:
        event = Event()
        # Fill event fields, e.g. event.name, event.begin, etc.
        # event.name = event_data['title']
        # event.begin = event_data['start']
        calendar.events.add(event)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(calendar)

if __name__ == "__main__":
    pdf_path = "your_events.pdf"
    output_path = "events.ics"
    events = extract_events_from_pdf(pdf_path)
    create_ics_file(events, output_path)
# %%
test_file_path = "F:\\PC_BIALY\\GIT REPOS\\pdf_to_ics\\roster.pdf"
test_lines = []
with pdfplumber.open(test_file_path) as pdf:
    for page in pdf.pages:
        for line in page.extract_text().split("\n"):
            test_lines.append(line)
# %%
test_lines[1]
# %%
test_lines[4].split(" ")
# %%
test_lines[5].split(" ")
# %%