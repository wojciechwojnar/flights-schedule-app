"""
Debug version of Flight Roster to Calendar Converter
This version shows detailed debugging information to help identify parsing issues
"""
import streamlit as st
import re
import pdfplumber
from datetime import datetime
from zoneinfo import ZoneInfo
import tempfile
import os

st.set_page_config(page_title="Debug Flight Roster Parser", page_icon="🐛", layout="wide")

def extract_and_debug_pdf(pdf_file):
    """Extract text from PDF and show debugging information"""
    lines = []
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(pdf_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        with pdfplumber.open(tmp_path) as pdf:
            st.write(f"📄 **PDF Info:** {len(pdf.pages)} pages")
            
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    page_lines = page_text.split("\n")
                    lines.extend(page_lines)
                    st.write(f"Page {page_num + 1}: {len(page_lines)} lines extracted")
    finally:
        os.unlink(tmp_path)
    
    return lines

def debug_parsing_steps(lines):
    """Debug each step of the parsing process"""
    
    st.header("🔍 Debug Information")
    
    # Show first 10 lines
    st.subheader("1. First 10 lines from PDF:")
    for i, line in enumerate(lines[:10]):
        st.code(f"Line {i}: '{line}'")
    
    # Test period parsing
    st.subheader("2. Period Parsing:")
    if len(lines) >= 2:
        st.write(f"Second line: `{lines[1]}`")
        period_parts = lines[1].split(" ")
        st.write(f"Split parts: {period_parts}")
        
        try:
            if len(period_parts) >= 3:
                period_start = datetime.strptime(period_parts[1], "%d%b%y")
                period_end = datetime.strptime(period_parts[2], "%d%b%y")
                st.success(f"✅ Period: {period_start.date()} to {period_end.date()}")
            else:
                st.error("❌ Not enough parts in period line")
        except Exception as e:
            st.error(f"❌ Period parsing error: {e}")
    else:
        st.error("❌ Not enough lines for period parsing")
    
    # Test regex patterns
    st.subheader("3. Regex Pattern Testing:")
    
    patterns = {
        "Workday Pattern": re.compile(r"^(\d{1,2})\.\s([A-Za-z]{3})\sC/I\s([A-Za-z]{3})"),
        "Flight Pattern": re.compile(r"^LO (\d{1,5})"),
        "Full Flight Pattern": re.compile(r"^(\d{1,2})\.\s([A-Za-z]{3})\sLO\s(\d{1,5})\s([A-Za-z]{3})\s(\d{4})\s(\d{4})\s([A-Za-z]{3})")
    }
    
    for pattern_name, pattern in patterns.items():
        st.write(f"**{pattern_name}:**")
        matches = []
        for i, line in enumerate(lines):
            if pattern.match(line):
                matches.append((i, line))
        
        if matches:
            st.success(f"✅ Found {len(matches)} matches")
            for line_num, line in matches[:5]:  # Show first 5 matches
                st.code(f"Line {line_num}: '{line}'")
            if len(matches) > 5:
                st.write(f"... and {len(matches) - 5} more")
        else:
            st.error(f"❌ No matches found")
    
    # Test section extraction
    st.subheader("4. Section Extraction:")
    
    sections = []
    current_section = []
    collecting = False
    current_day = None
    current_weekday = None
    
    workday_pattern = re.compile(r"^(\d{1,2})\.\s([A-Za-z]{3})\sC/I\s([A-Za-z]{3})")
    flight_pattern = re.compile(r"^LO (\d{1,5})")
    
    for i, line in enumerate(lines[3:], start=3):
        # Check for workday start
        workday_match = workday_pattern.match(line)
        if workday_match:
            current_day = workday_match.group(1)
            current_weekday = workday_match.group(2)
            st.write(f"📅 Found workday: {current_day}. {current_weekday} (line {i})")
        
        # Start collecting when we see C/I
        if "C/I" in line:
            collecting = True
            current_section.append(line)
            st.write(f"🟢 Start collecting: '{line}' (line {i})")
            continue
        
        # Stop collecting and save section when we see C/O
        if "C/O" in line:
            current_section.append(line)
            collecting = False
            sections.append(current_section)
            st.write(f"🔴 Stop collecting: '{line}' (line {i}) - Section has {len(current_section)} lines")
            current_section = []
            continue
        
        # Add flight lines to current section
        if collecting and current_day and current_weekday:
            flight_match = flight_pattern.match(line)
            if flight_match:
                modified_line = f"{current_day}. {current_weekday} {line}"
                current_section.append(modified_line)
                st.write(f"✈️ Added flight: '{modified_line}' (line {i})")
            else:
                current_section.append(line)
                st.write(f"📝 Added other: '{line}' (line {i})")
    
    st.write(f"**Total sections found: {len(sections)}**")
    
    # Test flight extraction from sections
    st.subheader("5. Flight Extraction from Sections:")
    
    full_flight_pattern = re.compile(r"^(\d{1,2})\.\s([A-Za-z]{3})\sLO\s(\d{1,5})\s([A-Za-z]{3})\s(\d{4})\s(\d{4})\s([A-Za-z]{3})")
    
    all_flights = []
    for section_num, section in enumerate(sections):
        st.write(f"**Section {section_num + 1}:** {len(section)} lines")
        section_flights = []
        
        for entry in section:
            if full_flight_pattern.match(entry):
                section_flights.append(entry)
                all_flights.append(entry)
                st.code(f"✈️ Flight: {entry}")
        
        if not section_flights:
            st.write("❌ No flights found in this section")
            st.write("Section contents:")
            for entry in section:
                st.code(f"  '{entry}'")
    
    st.write(f"**Total flights found: {len(all_flights)}**")
    
    return all_flights

def main():
    st.title("🐛 Debug Flight Roster Parser")
    st.markdown("This debug version shows detailed information about each parsing step")
    
    uploaded_file = st.file_uploader("Upload PDF for debugging", type="pdf")
    
    if uploaded_file:
        st.header("📄 PDF Processing")
        
        with st.spinner("Extracting text from PDF..."):
            lines = extract_and_debug_pdf(uploaded_file)
        
        st.success(f"✅ Extracted {len(lines)} lines total")
        
        if st.checkbox("Show all extracted lines", help="Warning: This might be very long!"):
            st.subheader("All extracted lines:")
            for i, line in enumerate(lines):
                st.code(f"{i:3d}: '{line}'")
        
        # Run debugging
        flights = debug_parsing_steps(lines)
        
        if flights:
            st.success(f"🎉 Successfully found {len(flights)} flights!")
            
            st.subheader("✈️ Found Flights:")
            for flight in flights:
                st.code(flight)
        else:
            st.error("❌ No flights found - check the debug information above")
            
            st.subheader("💡 Troubleshooting Tips:")
            st.markdown("""
            1. **Check line format**: Look at the extracted lines - do they match the expected format?
            2. **Check regex patterns**: Are the patterns matching the actual text in your PDF?
            3. **Check C/I and C/O markers**: Are these present in the extracted text?
            4. **Check section extraction**: Are sections being properly identified?
            5. **Check flight line format**: Do flight lines match the full flight pattern?
            """)

if __name__ == "__main__":
    main()