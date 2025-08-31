"""
Calendar generation utilities
"""
from datetime import datetime
from typing import List
from ics import Calendar, Event
from ..models.flight_event import FlightEvent
from ..utils.exceptions import CalendarGenerationError


class CalendarGenerator:
    """Generates ICS calendar files from flight events"""
    
    @staticmethod
    def create_ics_from_events(events: List[FlightEvent], cutoff_date: datetime) -> str:
        """
        Create ICS calendar content from flight events
        
        Args:
            events: List of FlightEvent objects
            cutoff_date: Only include flights after this date
            
        Returns:
            ICS calendar content as string
            
        Raises:
            CalendarGenerationError: If calendar generation fails
        """
        try:
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
                event.name = flight.display_name
                event.description = CalendarGenerator._create_event_description(flight)
                event.begin = departure_dt
                event.end = arrival_dt
                
                calendar.events.add(event)
            
            return calendar.serialize()
        
        except Exception as e:
            raise CalendarGenerationError(f"Error creating calendar file: {e}")
    
    @staticmethod
    def _create_event_description(flight: FlightEvent) -> str:
        """
        Create detailed event description
        
        Args:
            flight: FlightEvent object
            
        Returns:
            Formatted event description string
        """
        return f"""Flight: LO{flight.flight_no}
Route: {flight.departure_airport} → {flight.destination_airport}
Departure: {flight.departure_time[:2]}:{flight.departure_time[2:]} UTC
Arrival: {flight.arrival_time[:2]}:{flight.arrival_time[2:]} UTC
Tracker: {flight.tracker_url}"""
    
    @staticmethod
    def generate_filename(events: List[FlightEvent], default: str = "flights.ics") -> str:
        """
        Generate appropriate filename for calendar file
        
        Args:
            events: List of FlightEvent objects
            default: Default filename if events are empty
            
        Returns:
            Generated filename string
        """
        if not events:
            return default
        
        try:
            start_date = events[0].period_start.strftime("%Y%m%d")
            end_date = events[0].period_end.strftime("%Y%m%d")
            return f"{start_date}_{end_date}_flights.ics"
        except (AttributeError, IndexError):
            return default
    
    @classmethod
    def create_calendar_package(
        cls, 
        events: List[FlightEvent], 
        cutoff_date: datetime
    ) -> tuple[str, str]:
        """
        Create complete calendar package with content and filename
        
        Args:
            events: List of FlightEvent objects
            cutoff_date: Only include flights after this date
            
        Returns:
            Tuple of (ics_content, filename)
            
        Raises:
            CalendarGenerationError: If calendar generation fails
        """
        ics_content = cls.create_ics_from_events(events, cutoff_date)
        filename = cls.generate_filename(events)
        return ics_content, filename