# %%
import re
import pdfplumber  # For extracting tables from PDF
from ics import Calendar, Event  # For creating .ics files
from datetime import datetime
from zoneinfo import ZoneInfo


# %%
def extract_events_from_pdf(pdf_path):
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for line in page.extract_text().split("\n"):
                lines.append(line)
    period_start = datetime.strptime(lines[1].split(" ")[1], "%d%b%y")
    period_end = datetime.strptime(lines[1].split(" ")[2], "%d%b%y")

    collect = False
    section = []
    sections = []
    for line in lines[3:]:
        match_workday_start_date = re.match(
            r"^(\d{1,2})\.\s([A-Za-z]{3})\sC/I\s([A-Za-z]{3})", line
        )
        if match_workday_start_date:
            day = match_workday_start_date.group(1)
            weekday = match_workday_start_date.group(2)
        match_flight = re.match(r"^LO (\d{1,5})", line)
        if "C/I" in line:
            collect = True
            section.append(line)
            continue
        if "C/O" in line:
            section.append(line)
            collect = False
            sections.append(section)
            section = []
        if collect and match_flight:
            section.append(f"{day}. {weekday} " + line)
        if collect and not match_flight:
            section.append(line)

    flights = []
    for section in sections:
        for entry in section:
            match_flight = re.match(
                r"^(\d{1,2})\.\s([A-Za-z]{3})\sLO\s(\d{1,5})", entry
            )
            if match_flight:
                flights.append(entry)

    events = []
    for flight in flights:
        match_flight = re.match(
            r"^(\d{1,2})\.\s([A-Za-z]{3})\sLO\s(\d{1,5})\s([A-Za-z]{3})\s(\d{4})\s(\d{4})\s([A-Za-z]{3})",
            flight,
        )
        if match_flight:
            event = {
                "period_start": period_start,
                "period_end": period_end,
                "flight_day_of_month": int(match_flight.group(1)),
                "flight_day_of_week": match_flight.group(2),
                "flight_no": match_flight.group(3),
                "departure_airport": match_flight.group(4),
                "planned_departure_time": match_flight.group(5),
                "planned_landing_time": match_flight.group(6),
                "destination_airport": match_flight.group(7),
            }
            events.append(event)
    return events


def create_ics_file(events, output_path):
    calendar = Calendar()
    prev_event_data = None
    start_or_end = "period_start"
    for event_data in events:
        event = Event()
        event.name = f"Lot Michała LO{event_data['flight_no']}"
        event.description = (
            f"Tracking: https://www.flightradar24.com/LO{event_data['flight_no']}"
        )
        if (prev_event_data is not None) and (
            prev_event_data["flight_day_of_month"] > event_data["flight_day_of_month"]
        ):
            start_or_end = "period_end"
        datetime_for_event_begin = datetime(
            event_data[start_or_end].date().year,
            event_data[start_or_end].date().month,
            event_data["flight_day_of_month"],
            int(event_data["planned_departure_time"][:2]),
            int(event_data["planned_departure_time"][2:]),
            tzinfo=ZoneInfo("UTC"),
        )
        dt_warsaw_begin = datetime_for_event_begin.astimezone(ZoneInfo("Europe/Warsaw"))
        datetime_for_event_end = datetime(
            event_data[start_or_end].date().year,
            event_data[start_or_end].date().month,
            event_data["flight_day_of_month"],
            int(event_data["planned_landing_time"][:2]),
            int(event_data["planned_landing_time"][2:]),
            tzinfo=ZoneInfo("UTC"),
        )
        dt_warsaw_end = datetime_for_event_end.astimezone(ZoneInfo("Europe/Warsaw"))
        event.begin = dt_warsaw_begin
        event.end = dt_warsaw_end
        calendar.events.add(event)
        prev_event_data = event_data
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(calendar)


# %%
if __name__ == "__main__":
    pdf_path = "roster.pdf"
    output_path = "events.ics"
    events = extract_events_from_pdf(pdf_path)
    create_ics_file(events, output_path)
# %%
