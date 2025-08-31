"""
Flight event data model
"""
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


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
    
    @property
    def display_name(self) -> str:
        """Get display-friendly flight name"""
        return f"LO{self.flight_no} {self.departure_airport} → {self.destination_airport}"
    
    @property
    def tracker_url(self) -> str:
        """Get flight tracker URL"""
        return f"https://www.flightradar24.com/data/flights/LO{self.flight_no}"