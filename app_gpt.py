# streamlit_app.py
import re
import pdfplumber
from ics import Calendar, Event
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from io import BytesIO
import pandas as pd

# ------------------------------
# Your existing functions
# ------------------------------
def extract_events_from_pdf(pdf_file):
    lines = []
    with pdfplumber.open(pdf_file) as pdf:
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


def create_ics_file(cutoff_date, events):
    calendar = Calendar()
    prev_event_data = None
    start_or_end = "period_start"

    for event_data in events:
        event = Event()
        event.name = f"LO{event_data['flight_no']} z {event_data['departure_airport']} do {event_data['destination_airport']}"
        event.description = fr"""Tabela lotów: https://www.flightradar24.com/data/flights/LO{event_data["flight_no"]}"""

        if (prev_event_data is not None) and (
            prev_event_data["flight_day_of_month"] > event_data["flight_day_of_month"]
        ):
            start_or_end = "period_end"

        datetime_for_event_begin = datetime(
            event_data[start_or_end].year,
            event_data[start_or_end].month,
            event_data["flight_day_of_month"],
            int(event_data["planned_departure_time"][:2]),
            int(event_data["planned_departure_time"][2:]),
            tzinfo=ZoneInfo("UTC"),
        )
        dt_warsaw_begin = datetime_for_event_begin.astimezone(ZoneInfo("Europe/Warsaw"))

        datetime_for_event_end = datetime(
            event_data[start_or_end].year,
            event_data[start_or_end].month,
            event_data["flight_day_of_month"],
            int(event_data["planned_landing_time"][:2]),
            int(event_data["planned_landing_time"][2:]),
            tzinfo=ZoneInfo("UTC"),
        )
        dt_warsaw_end = datetime_for_event_end.astimezone(ZoneInfo("Europe/Warsaw"))

        if dt_warsaw_begin > cutoff_date:
            event.begin = dt_warsaw_begin
            event.end = dt_warsaw_end
            calendar.events.add(event)

        prev_event_data = event_data

    return str(calendar)


# ------------------------------
# Streamlit UI
# ------------------------------
st.title("✈️ Flight Roster → Calendar (.ics)")

uploaded_file = st.file_uploader("Upload your roster PDF", type=["pdf"])
cutoff_date = st.date_input("Cutoff date", value=datetime.today().date())

if uploaded_file is not None:
    events = extract_events_from_pdf(uploaded_file)

    if len(events) == 0:
        st.warning("No flights detected in this PDF. Check format or parsing rules.")
    else:
        st.success(f"Found {len(events)} flights in the PDF ✅")

        # Preview extracted flights as table
        df = pd.DataFrame(events)
        df["planned_departure_time"] = df["planned_departure_time"].apply(lambda x: f"{x[:2]}:{x[2:]}")
        df["planned_landing_time"] = df["planned_landing_time"].apply(lambda x: f"{x[:2]}:{x[2:]}")
        st.subheader("Preview of extracted flights:")
        st.dataframe(df[[
            "flight_day_of_month", "flight_day_of_week", "flight_no",
            "departure_airport", "planned_departure_time",
            "planned_landing_time", "destination_airport"
        ]])

        if st.button("Generate Calendar"):
            ics_content = create_ics_file(
                datetime.combine(cutoff_date, datetime.min.time(), tzinfo=ZoneInfo("Europe/Warsaw")),
                events
            )
            ics_bytes = BytesIO(ics_content.encode("utf-8"))
            st.download_button(
                "📥 Download .ics file",
                data=ics_bytes,
                file_name="flights_calendar.ics",
                mime="text/calendar",
            )
