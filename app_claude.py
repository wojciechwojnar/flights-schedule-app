import streamlit as st
import re
import pdfplumber
from ics import Calendar, Event
from datetime import datetime
from zoneinfo import ZoneInfo
import tempfile
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Set page config
st.set_page_config(
    page_title="Flight Roster to Calendar Converter",
    page_icon="✈️",
    layout="wide"
)


@dataclass
class FlightEvent:
    """Represents a single flight event"""
    flight_no: str
    departure_airport: str
    destination_airport: str
    departure_time: str
    arrival_time: str
    day_of_month: int
    day_of_week: str
    period_start: datetime
    period_end: datetime
    
    def get_departure_datetime(self, use_period_end: bool = False) -> datetime:
        """Get departure datetime with proper timezone"""
        base_date = self.period_end if use_period_end else self.period_start
        return datetime(
            base_date.year,
            base_date.month,
            self.day_of_month,
            int(self.departure_time[:2]),
            int(self.departure_time[2:]),
            tzinfo=ZoneInfo("UTC")
        ).astimezone(ZoneInfo("Europe/Warsaw"))
    
    def get_arrival_datetime(self, use_period_end: bool = False) -> datetime:
        """Get arrival datetime with proper timezone"""
        base_date = self.period_end if use_period_end else self.period_start
        return datetime(
            base_date.year,
            base_date.month,
            self.day_of_month,
            int(self.arrival_time[:2]),
            int(self.arrival_time[2:]),
            tzinfo=ZoneInfo("UTC")
        ).astimezone(ZoneInfo("Europe/Warsaw"))

class PDFProcessor:
    """Handles PDF text extraction and validation"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_file) -> List[str]:
        """Extract text lines from PDF file"""
        if pdf_file.size > 50 * 1024 * 1024:
            raise ValueError("File too large. Maximum size is 50MB.")
        
        lines = []
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            with pdfplumber.open(tmp_path) as pdf:
                if not pdf.pages:
                    raise ValueError("PDF file appears to be empty or corrupted.")
                
                for page in pdf.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            lines.extend(page_text.split("\n"))
                    except Exception as e:
                        st.warning(f"Could not extract text from page {page.page_number}: {e}")
                        continue
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        
        return lines

class RosterParser:
    """Parses roster data from PDF text lines"""
    
    # Regex patterns as class constants
    WORKDAY_PATTERN = re.compile(r"^(\d{1,2})\.\s([A-Za-z]{3})\sC/I\s([A-Za-z]{3})")
    FLIGHT_PATTERN = re.compile(r"^LO (\d{1,5})")
    FULL_FLIGHT_PATTERN = re.compile(
        r"^(\d{1,2})\.\s([A-Za-z]{3})\sLO\s(\d{1,5})\s([A-Za-z]{3})\s(\d{4})\s(\d{4})\s([A-Za-z]{3})"
    )
    
    @staticmethod
    def parse_period(lines: List[str]) -> Tuple[datetime, datetime]:
        """Extract period dates from PDF header"""
        if len(lines) < 2:
            raise ValueError("PDF doesn't contain enough data.")
        
        try:
            period_parts = lines[1].split(" ")
            if len(period_parts) < 3:
                raise ValueError("Cannot parse period from PDF header.")
            
            period_start = datetime.strptime(period_parts[1], "%d%b%y")
            period_end = datetime.strptime(period_parts[2], "%d%b%y")
            return period_start, period_end
        except (ValueError, IndexError) as e:
            raise ValueError(f"Error parsing period dates: {e}")
    
    @classmethod
    def extract_work_sections(cls, lines: List[str]) -> List[List[str]]:
        """Extract work day sections from PDF lines"""
        sections = []
        current_section = []
        collecting = False
        current_day = None
        current_weekday = None
        
        for line in lines[3:]:  # Skip header lines
            # Check for workday start
            workday_match = cls.WORKDAY_PATTERN.match(line)
            if workday_match:
                current_day = workday_match.group(1)
                current_weekday = workday_match.group(2)
            
            # Start collecting when we see C/I
            if "C/I" in line:
                collecting = True
                current_section.append(line)
                continue
            
            # Stop collecting and save section when we see C/O
            if "C/O" in line:
                current_section.append(line)
                collecting = False
                if current_section:
                    sections.append(current_section)
                current_section = []
                continue
            
            # Add flight lines to current section
            if collecting:
                flight_match = cls.FLIGHT_PATTERN.match(line)
                if flight_match:
                    current_section.append(f"{current_day}. {current_weekday} {line}")
                else:
                    current_section.append(line)
        
        return sections
    
    @classmethod
    def extract_flights_from_sections(cls, sections: List[List[str]]) -> List[str]:
        """Extract flight lines from work sections"""
        flights = []
        for section in sections:
            for entry in section:
                if cls.WORKDAY_PATTERN.match(entry.split("LO")[0] + "LO") if "LO" in entry else False:
                    flights.append(entry)
        return flights
    
    @classmethod
    def parse_flight_to_event(cls, flight_line: str, period_start: datetime, period_end: datetime) -> Optional[FlightEvent]:
        """Parse a flight line into a FlightEvent object"""
        match = cls.FULL_FLIGHT_PATTERN.match(flight_line)
        if not match:
            return None
        
        return FlightEvent(
            day_of_month=int(match.group(1)),
            day_of_week=match.group(2),
            flight_no=match.group(3),
            departure_airport=match.group(4),
            departure_time=match.group(5),
            arrival_time=match.group(6),
            destination_airport=match.group(7),
            period_start=period_start,
            period_end=period_end
        )

class CalendarGenerator:
    """Generates ICS calendar files from flight events"""
    
    @staticmethod
    def create_ics_from_events(events: List[FlightEvent], cutoff_date: datetime) -> str:
        """Create ICS calendar content from flight events"""
        calendar = Calendar()
        
        for i, flight in enumerate(events):
            # Determine if we should use period_end (for month rollover)
            use_period_end = (
                i > 0 and 
                events[i-1].day_of_month > flight.day_of_month
            )
            
            departure_dt = flight.get_departure_datetime(use_period_end)
            arrival_dt = flight.get_arrival_datetime(use_period_end)
            
            # Skip flights before cutoff date
            if departure_dt <= cutoff_date:
                continue
            
            event = Event()
            event.name = f"LO{flight.flight_no} {flight.departure_airport} → {flight.destination_airport}"
            event.description = f"Flight: LO{flight.flight_no}\nRoute: {flight.departure_airport} → {flight.destination_airport}\nTracker: https://www.flightradar24.com/data/flights/LO{flight.flight_no}"
            event.begin = departure_dt
            event.end = arrival_dt
            
            calendar.events.add(event)
        
        return calendar.serialize()

def extract_events_from_pdf(pdf_file) -> List[FlightEvent]:
    """Main function to extract flight events from PDF file"""
    try:
        # Extract text from PDF
        lines = PDFProcessor.extract_text_from_pdf(pdf_file)
        
        # Parse period information
        period_start, period_end = RosterParser.parse_period(lines)
        
        # Extract work sections
        sections = RosterParser.extract_work_sections(lines)
        
        # Extract flight lines
        flight_lines = RosterParser.extract_flights_from_sections(sections)
        
        # Parse flights into events
        events = []
        for flight_line in flight_lines:
            event = RosterParser.parse_flight_to_event(flight_line, period_start, period_end)
            if event:
                events.append(event)
        
        return events
    
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return []

def create_ics_file(cutoff_date: datetime, events: List[FlightEvent]) -> str:
    """Create ICS calendar file from flight events"""
    try:
        return CalendarGenerator.create_ics_from_events(events, cutoff_date)
    except Exception as e:
        st.error(f"Error creating calendar file: {e}")
        return ""

# Streamlit UI
def main():
    st.title("✈️ Flight Roster to Calendar Converter")
    st.markdown("Convert your LOT Polish Airlines roster PDF to a calendar (.ics) file")
    
    # Initialize session state
    if 'events' not in st.session_state:
        st.session_state.events = []
    if 'processed_file_name' not in st.session_state:
        st.session_state.processed_file_name = None
    
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
                            "Date": f"{event.day_of_month} {event.day_of_week}",
                            "Flight": f"LO{event.flight_no}",
                            "Route": f"{event.departure_airport} → {event.destination_airport}",
                            "Departure": f"{event.departure_time[:2]}:{event.departure_time[2:]}",
                            "Arrival": f"{event.arrival_time[:2]}:{event.arrival_time[2:]}"
                        })
                    
                    st.dataframe(flight_data, use_container_width=True)
                    
                    # Generate calendar file
                    with st.spinner("Generating calendar file..."):
                        ics_content = create_ics_file(cutoff_datetime, events)
                        
                        if ics_content:
                            # Generate filename
                            if events:
                                start_date = events[0].period_start.strftime("%Y%m%d")
                                end_date = events[0].period_end.strftime("%Y%m%d")
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