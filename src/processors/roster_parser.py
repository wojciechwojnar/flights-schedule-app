"""
Roster parsing utilities
"""
import re
from datetime import datetime
from typing import List, Optional, Tuple
from ..models.flight_event import FlightEvent
from ..utils.exceptions import RosterParsingError


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
        """
        Extract period dates from PDF header
        
        Args:
            lines: List of text lines from PDF
            
        Returns:
            Tuple of (period_start, period_end) datetime objects
            
        Raises:
            RosterParsingError: If period cannot be parsed
        """
        if len(lines) < 2:
            raise RosterParsingError("PDF doesn't contain enough data to parse period.")
        
        try:
            period_parts = lines[1].split(" ")
            if len(period_parts) < 3:
                raise RosterParsingError("Cannot parse period from PDF header. Expected format not found.")
            
            period_start = datetime.strptime(period_parts[1], "%d%b%y")
            period_end = datetime.strptime(period_parts[2], "%d%b%y")
            return period_start, period_end
        except (ValueError, IndexError) as e:
            raise RosterParsingError(f"Error parsing period dates: {e}")
    
    @classmethod
    def extract_work_sections(cls, lines: List[str]) -> List[List[str]]:
        """
        Extract work day sections from PDF lines
        
        Args:
            lines: List of text lines from PDF
            
        Returns:
            List of work sections, each containing related work day lines
        """
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
            if collecting and current_day and current_weekday:
                flight_match = cls.FLIGHT_PATTERN.match(line)
                if flight_match:
                    current_section.append(f"{current_day}. {current_weekday} {line}")
                else:
                    current_section.append(line)
        
        return sections
    
    @classmethod
    def extract_flights_from_sections(cls, sections: List[List[str]]) -> List[str]:
        """
        Extract flight lines from work sections
        
        Args:
            sections: List of work sections
            
        Returns:
            List of flight line strings
        """
        flights = []
        for section in sections:
            for entry in section:
                # Check if line contains a valid flight pattern
                if "LO" in entry and cls._is_valid_flight_line(entry):
                    flights.append(entry)
        return flights
    
    @classmethod
    def _is_valid_flight_line(cls, line: str) -> bool:
        """Check if line contains a valid flight pattern"""
        return bool(cls.FULL_FLIGHT_PATTERN.match(line))
    
    @classmethod
    def parse_flight_to_event(
        cls, 
        flight_line: str, 
        period_start: datetime, 
        period_end: datetime
    ) -> Optional[FlightEvent]:
        """
        Parse a flight line into a FlightEvent object
        
        Args:
            flight_line: Raw flight line string
            period_start: Period start date
            period_end: Period end date
            
        Returns:
            FlightEvent object or None if parsing fails
        """
        match = cls.FULL_FLIGHT_PATTERN.match(flight_line)
        if not match:
            return None
        
        try:
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
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse flight line '{flight_line}': {e}")
            return None
    
    @classmethod
    def parse_flights_from_pdf_lines(cls, lines: List[str], cutoff_datetime: Optional[datetime] = None) -> List[FlightEvent]:
        """
        Complete parsing pipeline from PDF lines to FlightEvent objects
        
        Args:
            lines: List of text lines from PDF
            cutoff_datetime: Only include flights after this datetime (optional)
            
        Returns:
            List of FlightEvent objects (filtered by cutoff if provided)
            
        Raises:
            RosterParsingError: If parsing fails
        """
        try:
            # Parse period information
            period_start, period_end = cls.parse_period(lines)
            
            # Extract work sections
            sections = cls.extract_work_sections(lines)
            
            # Extract flight lines
            flight_lines = cls.extract_flights_from_sections(sections)
            
            # Parse flights into events
            events = []
            for i, flight_line in enumerate(flight_lines):
                event = cls.parse_flight_to_event(flight_line, period_start, period_end)
                if event:
                    # Apply cutoff filtering if provided
                    if cutoff_datetime:
                        # Determine if we should use period_end (for month rollover)
                        use_period_end = (
                            i > 0 and 
                            events and  # Check if events list has items
                            events[-1].day_of_month > event.day_of_month
                        )
                        
                        departure_dt = event.get_departure_datetime(use_period_end)
                        
                        # Only add flights after cutoff
                        if departure_dt > cutoff_datetime:
                            events.append(event)
                    else:
                        # No filtering, add all flights
                        events.append(event)
            
            return events
        
        except Exception as e:
            if isinstance(e, RosterParsingError):
                raise
            raise RosterParsingError(f"Unexpected error during parsing: {e}")