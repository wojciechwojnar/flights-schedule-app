import streamlit as st
import re
import pdfplumber
from ics import Calendar, Event
from datetime import datetime
from zoneinfo import ZoneInfo
import io
import tempfile
import os

# Set page config
st.set_page_config(
    page_title="Flight Roster to Calendar Converter",
    page_icon="✈️",
    layout="wide"
)

def extract_events_from_pdf(pdf_file):
    """Extract flight events from uploaded PDF file"""
    lines = []
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(pdf_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    for line in page_text.split("\n"):
                        lines.append(line)
    finally:
        # Clean up temporary file
        os.unlink(tmp_path)
    
    if len(lines) < 2:
        st.error("PDF doesn't contain enough data. Please check if the file is correct.")
        return []
    
    try:
        # Extract period from second line
        period_parts = lines[1].split(" ")
        if len(period_parts) < 3:
            st.error("Cannot parse period from PDF. Expected format in second line.")
            return []
            
        period_start = datetime.strptime(period_parts[1], "%d%b%y")
        period_end = datetime.strptime(period_parts[2], "%d%b%y")
    except (ValueError, IndexError) as e:
        st.error(f"Error parsing period dates: {e}")
        return []

    # Split into work days
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

    # Extract flights
    flights = []
    for section in sections:
        for entry in section:
            match_flight = re.match(
                r"^(\d{1,2})\.\s([A-Za-z]{3})\sLO\s(\d{1,5})", entry
            )
            if match_flight:
                flights.append(entry)

    # Create event dictionaries
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
    """Create ICS calendar file from events"""
    calendar = Calendar()
    prev_event_data = None
    start_or_end = "period_start"
    
    for event_data in events:
        event = Event()
        event.name = f"LO{event_data['flight_no']} z {event_data['departure_airport']} do {event_data['destination_airport']}"
        event.description = f"Tabela lotów: https://www.flightradar24.com/data/flights/LO{event_data['flight_no']}"
        
        # Check if previous flight had higher day number than current
        if (prev_event_data is not None) and (
            prev_event_data["flight_day_of_month"] > event_data["flight_day_of_month"]
        ):
            start_or_end = "period_end"
            
        # Create datetime for event begin
        datetime_for_event_begin = datetime(
            event_data[start_or_end].date().year,
            event_data[start_or_end].date().month,
            event_data["flight_day_of_month"],
            int(event_data["planned_departure_time"][:2]),
            int(event_data["planned_departure_time"][2:]),
            tzinfo=ZoneInfo("UTC"),
        )
        
        # Convert to Warsaw timezone
        dt_warsaw_begin = datetime_for_event_begin.astimezone(ZoneInfo("Europe/Warsaw"))
        
        datetime_for_event_end = datetime(
            event_data[start_or_end].date().year,
            event_data[start_or_end].date().month,
            event_data["flight_day_of_month"],
            int(event_data["planned_landing_time"][:2]),
            int(event_data["planned_landing_time"][2:]),
            tzinfo=ZoneInfo("UTC"),
        )
        
        # Convert to Warsaw timezone
        dt_warsaw_end = datetime_for_event_end.astimezone(ZoneInfo("Europe/Warsaw"))
        
        if dt_warsaw_begin > cutoff_date:
            event.begin = dt_warsaw_begin
            event.end = dt_warsaw_end
            calendar.events.add(event)
            
        prev_event_data = event_data
    
    return calendar.serialize()

# Streamlit UI
def main():
    st.title("✈️ Flight Roster to Calendar Converter")
    st.markdown("Convert your LOT Polish Airlines roster PDF to a calendar (.ics) file")
    
    # Sidebar with instructions
    st.sidebar.header("📋 Instructions")
    st.sidebar.markdown("""
    1. Upload your roster PDF file
    2. Set the cutoff date (flights before this date will be excluded)
    3. Click 'Process PDF' to extract flights
    4. Download the generated calendar file
    5. Import the .ics file to your calendar app (Google Calendar, Outlook, etc.)
    """)
    
    st.sidebar.header("ℹ️ About")
    st.sidebar.markdown("""
    This tool extracts flight information from LOT Polish Airlines roster PDFs and converts them to a standard calendar format.
    
    **Supported format:**
    - LOT roster PDFs with C/I and C/O markers
    - Flight numbers starting with 'LO'
    - Standard airport codes
    """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Upload Roster PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file", 
            type="pdf",
            help="Upload your LOT Polish Airlines roster PDF file"
        )
        
        st.header("Settings")
        cutoff_date = st.date_input(
            "Cutoff Date",
            value=datetime.now().date(),
            help="Flights before this date will be excluded from the calendar"
        )
        
        # Convert date to datetime with timezone
        cutoff_datetime = datetime.combine(cutoff_date, datetime.min.time())
        cutoff_datetime = cutoff_datetime.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
    
    with col2:
        st.header("Status")
        status_placeholder = st.empty()
        
    if uploaded_file is not None:
        with status_placeholder.container():
            st.info("📄 PDF file uploaded successfully")
            
        if st.button("🚀 Process PDF", type="primary"):
            with st.spinner("Processing PDF..."):
                # Extract events
                events = extract_events_from_pdf(uploaded_file)
                
                if events:
                    st.success(f"✅ Found {len(events)} flights in the roster")
                    
                    # Display extracted flights
                    st.header("📅 Extracted Flights")
                    
                    # Create a summary table
                    flight_data = []
                    for event in events:
                        flight_data.append({
                            "Date": f"{event['flight_day_of_month']} {event['flight_day_of_week']}",
                            "Flight": f"LO{event['flight_no']}",
                            "Route": f"{event['departure_airport']} → {event['destination_airport']}",
                            "Departure": f"{event['planned_departure_time'][:2]}:{event['planned_departure_time'][2:]}",
                            "Arrival": f"{event['planned_landing_time'][:2]}:{event['planned_landing_time'][2:]}"
                        })
                    
                    st.dataframe(flight_data, use_container_width=True)
                    
                    # Generate calendar file
                    with st.spinner("Generating calendar file..."):
                        ics_content = create_ics_file(cutoff_datetime, events)
                        
                        if ics_content:
                            # Generate filename
                            if events:
                                start_date = events[0]['period_start'].strftime("%Y%m%d")
                                end_date = events[0]['period_end'].strftime("%Y%m%d")
                                filename = f"{start_date}_{end_date}_flights.ics"
                            else:
                                filename = "flights.ics"
                            
                            st.success("✅ Calendar file generated successfully!")
                            
                            # Download button
                            st.download_button(
                                label="📥 Download Calendar (.ics)",
                                data=ics_content,
                                file_name=filename,
                                mime="text/calendar",
                                type="primary"
                            )
                            
                            st.info("""
                            **Next steps:**
                            1. Click the download button above
                            2. Import the .ics file to your calendar application:
                               - **Google Calendar**: Settings → Import & Export → Import
                               - **Outlook**: File → Open & Export → Import/Export
                               - **Apple Calendar**: File → Import
                            """)
                        else:
                            st.error("❌ Error generating calendar file")
                else:
                    st.error("❌ No flights found in the PDF. Please check if the file format is correct.")
    else:
        with status_placeholder.container():
            st.info("👆 Please upload a PDF file to get started")

if __name__ == "__main__":
    main()