"""
Flight Roster to Calendar Converter - Streamlit App
"""
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

# Import our custom modules
from src.processors.pdf_processor import PDFProcessor
from src.processors.roster_parser import RosterParser
from src.generators.calendar_generator import CalendarGenerator
from src.utils.exceptions import (
    FlightRosterError, 
    PDFProcessingError, 
    RosterParsingError, 
    CalendarGenerationError
)

# Set page config
st.set_page_config(
    page_title="Flight Roster to Calendar Converter",
    page_icon="✈️",
    layout="wide"
)


def process_roster_pdf(pdf_file, cutoff_datetime=None):
    """
    Process uploaded roster PDF and extract flight events
    
    Args:
        pdf_file: Streamlit uploaded file object
        cutoff_datetime: Only include flights after this datetime (optional)
        
    Returns:
        List of FlightEvent objects or empty list on error
    """
    try:
        # Extract text from PDF
        st.write("🔍 Extracting text from PDF...")
        lines = PDFProcessor.extract_text_from_pdf(pdf_file)
        st.write(f"✅ Extracted {len(lines)} lines from PDF")
        
        # Validate PDF structure
        st.write("🔍 Validating PDF structure...")
        PDFProcessor.validate_pdf_structure(lines)
        st.write("✅ PDF structure validation passed")
        
        # Parse flights from PDF lines (with cutoff filtering)
        st.write("🔍 Parsing flights from PDF...")
        events, min_cutoff_datetime = RosterParser.parse_flights_from_pdf_lines(lines)
        if cutoff_datetime and (cutoff_datetime > min_cutoff_datetime):
            events = [event for event in events if (event.departure_datetime.date() >= cutoff_datetime.date()) 
                      & (event.departure_datetime is not None)]
            st.write(f"✅ Found {len(events)} flight events after {cutoff_datetime.date()}")
        elif cutoff_datetime and (cutoff_datetime <= min_cutoff_datetime):
            events = [event for event in events if (event.departure_datetime.date() >= min_cutoff_datetime.date()) 
                      & (event.departure_datetime is not None)]
            st.write(f"Selected earlier cutoff date than minimal expected, changing to minimal based on file {min_cutoff_datetime.strftime("%Y-%m-%d")}")
            st.write(f"✅ Found {len(events)} flight events after {min_cutoff_datetime.date()}")
        else:
            st.write(f"Cutoff datetime was not selected, changing to minimal based on file {min_cutoff_datetime.strftime("%Y-%m-%d")}")
            events = [event for event in events if (event.departure_datetime.date() >= min_cutoff_datetime.date()) 
                      & (event.departure_datetime is not None)]
            st.write(f"✅ Found {len(events)} flight events after {min_cutoff_datetime.date()}")
        
        # Show some debug info
        if events:
            st.write("📋 First few flights found:")
            for i, event in enumerate(events[:3]):
                st.write(f"  - LO{event.flight_no}: {event.departure_airport} → {event.destination_airport} ({event.departure_datetime.strftime('%Y-%m-%d %H:%M')})")
        
        return events
    
    except PDFProcessingError as e:
        st.error(f"PDF Processing Error: {e}")
        return []
    except RosterParsingError as e:
        st.error(f"Roster Parsing Error: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.exception(e)  # This will show the full traceback
        return []


def create_calendar_file(events):
    """
    Create ICS calendar file from flight events
    
    Args:
        events: List of FlightEvent objects (pre-filtered)
        
    Returns:
        Tuple of (ics_content, filename) or (None, None) on error
    """
    try:
        return CalendarGenerator.create_calendar_package(events)
    except CalendarGenerationError as e:
        st.error(f"Calendar Generation Error: {e}")
        return None, None
    except Exception as e:
        st.error(f"Unexpected error creating calendar: {e}")
        return None, None


def display_flight_summary(events):
    """Display extracted flights in a table"""
    if not events:
        return
    
    flight_data = []
    for event in events:
        flight_data.append({
            "Date": f"{event.departure_datetime.strftime("%Y-%m-%d")}",
            "Flight": f"LO{event.flight_no}",
            "Route": f"{event.departure_airport} → {event.destination_airport}",
            "Departure": f"{event.departure_time[:2]}:{event.departure_time[2:]}",
            "Arrival": f"{event.arrival_time[:2]}:{event.arrival_time[2:]}"
        })
    
    st.dataframe(flight_data, use_container_width=True)


def render_sidebar():
    """Render sidebar with instructions and information"""
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
    
    st.sidebar.header("🔧 Technical Info")
    st.sidebar.markdown("""
    **File Limits:**
    - Maximum file size: 50MB
    - Supported format: PDF only
    - Text-based PDFs (not scanned images)
    """)


def main():
    """Main Streamlit application"""
    st.title("✈️ Flight Roster to Calendar Converter")
    st.markdown("Convert your LOT Polish Airlines roster PDF to a calendar (.ics) file")
    
    # Initialize session state
    if 'events' not in st.session_state:
        st.session_state.events = []
    if 'processed_file_name' not in st.session_state:
        st.session_state.processed_file_name = None
    
    # Render sidebar
    render_sidebar()
    
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
            value=None,
            help="Flights before this date will be excluded from the calendar"
        )
        if cutoff_date:
            # Convert date to datetime with timezone
            cutoff_datetime = datetime.combine(cutoff_date, datetime.min.time())
            cutoff_datetime = cutoff_datetime.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
        else:
            cutoff_datetime = None
    
    with col2:
        st.header("Status")
        status_placeholder = st.empty()
        
    # File processing logic
    if uploaded_file is not None:
        with status_placeholder.container():
            st.info("📄 PDF file uploaded successfully")
            st.caption(f"File: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
        if st.button("🚀 Process PDF", type="primary"):
            with st.spinner("Processing PDF..."):
                # Extract events with cutoff filtering
                events = process_roster_pdf(uploaded_file, cutoff_datetime)

                if events:
                    # Store in session state
                    st.session_state.events = events
                    st.session_state.processed_file_name = uploaded_file.name
                    
                    st.success(f"✅ Found {len(events)} flights after {cutoff_date}")
                    
                    # Display extracted flights
                    st.header("📅 Extracted Flights")
                    display_flight_summary(events)
                    
                    # Generate and offer calendar download
                    with st.spinner("Generating calendar file..."):
                        ics_content, filename = create_calendar_file(events)
                        
                        if ics_content and filename:
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
                    st.error(f"❌ No flights found after {cutoff_date}. Try adjusting the cutoff date.")
    else:
        with status_placeholder.container():
            st.info("👆 Please upload a PDF file to get started")
    
    # Display cached results if available
    if st.session_state.events and st.session_state.processed_file_name:
        st.header("📅 Previously Processed Flights")
        st.caption(f"From file: {st.session_state.processed_file_name}")
        
        # Re-filter cached events based on current cutoff
        filtered_events = []
        for event in st.session_state.events:
            departure_dt = event.departure_datetime
            if (cutoff_datetime is not None) and (departure_dt.date() >= cutoff_datetime.date()):
                filtered_events.append(event)
            else:
                filtered_events = st.session_state.events
        
        if filtered_events:
            display_flight_summary(filtered_events)
            
            # Offer re-download with current cutoff
            with st.spinner("Regenerating calendar file..."):
                ics_content, filename = create_calendar_file(filtered_events)
                
                if ics_content and filename:
                    st.download_button(
                        label="📥 Re-download Calendar (.ics)",
                        data=ics_content,
                        file_name=filename,
                        mime="text/calendar",
                        key="redownload"
                    )
        else:
            st.info(f"No cached flights found after {cutoff_date}. Process a new PDF or adjust the cutoff date.")


if __name__ == "__main__":
    main()