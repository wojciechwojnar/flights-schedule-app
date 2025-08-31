"""
Custom exceptions for the flight roster application
"""


class FlightRosterError(Exception):
    """Base exception for flight roster processing"""
    pass


class PDFProcessingError(FlightRosterError):
    """Raised when PDF processing fails"""
    pass


class RosterParsingError(FlightRosterError):
    """Raised when roster parsing fails"""
    pass


class CalendarGenerationError(FlightRosterError):
    """Raised when calendar generation fails"""
    pass


class InvalidFileError(PDFProcessingError):
    """Raised when uploaded file is invalid"""
    pass


class FileSizeError(PDFProcessingError):
    """Raised when file size exceeds limits"""
    pass