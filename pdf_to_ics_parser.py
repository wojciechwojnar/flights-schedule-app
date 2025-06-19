# %%
import re
import pdfplumber  # For extracting tables from PDF
from ics import Calendar, Event  # For creating .ics files
from datetime import datetime
from zoneinfo import ZoneInfo


# %%
def extract_events_from_pdf(pdf_path):
    # zczytanie tekstu z pdfa i podział na linie
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for line in page.extract_text().split("\n"):
                lines.append(line)
    # zczytanie z drugiej linijki na jaki okres jest rozpiska z pdfa
    period_start = datetime.strptime(lines[1].split(" ")[1], "%d%b%y")
    period_end = datetime.strptime(lines[1].split(" ")[2], "%d%b%y")

    # podział na dni pracy
    collect = False
    section = []
    sections = []
    for line in lines[3:]:
        # początek dnia pracy jest rozpoznawany poprzez:
        # - ^ sprawdzenie od początku linijki,
        # - sprawdzenie czy w linijce jest dzień miesiąca: (\d{1,2}) - sprawdza czy liczba jest maksymalnie dwucyfrowa,
        # - \. sprawdza czy jest kropka,
        # - \s sprawdza spację,
        # - sprawdzenie skrótu dnia: ([A-Za-z]{3}) - sprawdza czy dany element składa się z 3 liter dużych bądź małych
        # - C/I clock-in/check-in
        # - sprawdzenie lotniska na którym jest check-in ([A-Za-z]{3})
        # ogólnie powyższą walidacje można by poprawić, ale jest dobrym punktem startowym
        match_workday_start_date = re.match(
            r"^(\d{1,2})\.\s([A-Za-z]{3})\sC/I\s([A-Za-z]{3})", line
        )
        # "zwykłe nawiasy": () definiują grupe w regexach, zapisanie dnia miesiąca i tygodnia z grupy 1 i 2
        if match_workday_start_date:
            day = match_workday_start_date.group(1)
            weekday = match_workday_start_date.group(2)
        # jeśli linia zaczyna się od LO i nr lotu, to będziemy musieli dodać dzień miesiąca i dzień tygodnia zapisany w powyższych dwóch linijkach
        # nazwa zmiennej jest myląca, ale nieważne
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
        # dodawanie tego typu linii: 'LO 635 WAW 2055 2300 SOF E75'
        if collect and match_flight:
            section.append(f"{day}. {weekday} " + line)
        # dodawanie tego typu linii: '29. Thu LO 636 SOF 0220 0425 WAW E75'
        if collect and not match_flight:
            section.append(line)

    # faktycznie rozpoznawanie lotów
    # odrzucanie np takich linijek: 'H1 SOF'
    flights = []
    # sprawdzamy "dni robocze"
    for section in sections:
        # sprawdzamy czy dany element dnia jest lotem
        for entry in section:
            match_flight = re.match(
                r"^(\d{1,2})\.\s([A-Za-z]{3})\sLO\s(\d{1,5})", entry
            )
            if match_flight:
                flights.append(entry)

    # zapisanie istotnych informacji na temat lotów do słowników
    events = []
    for flight in flights:
        # ostateczne sprawdzenie czy lot jest lotem xd i zapisanie informacji z każdej z "grup" do słownika
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
        event.name = f"LO{event_data['flight_no']} z {event_data['departure_airport']} do {event_data['destination_airport']}"
        event.description = fr"""Link działa prawidłowo tylko na komputerze i gdy samolot jest online: https://www.flightradar24.com/LO{event_data["flight_no"]}
W innym wypadku lepiej korzystać z tego i ręcznie wybrać śledzenie: https://www.flightradar24.com/data/flights/LO{event_data["flight_no"]}
"""
        # sprawdzenie czy poprzedni lot miał "wyższy" dzień niż obecny, wtedy należy wziąć miesiąc i rok z końca okresu
        # znów nazwa zmiennej nie jest idealna, ale z grubsza mówi ocb
        if (prev_event_data is not None) and (
            prev_event_data["flight_day_of_month"] > event_data["flight_day_of_month"]
        ):
            start_or_end = "period_end"
        # zapisanie datetime początku eventu
        datetime_for_event_begin = datetime(
            event_data[start_or_end].date().year,
            event_data[start_or_end].date().month,
            event_data["flight_day_of_month"],
            int(event_data["planned_departure_time"][:2]),
            int(event_data["planned_departure_time"][2:]),
            tzinfo=ZoneInfo("UTC"),
        )
        # konwersja na odpowiednią strefę czasową (to właściwie nie jest konieczne,
        # bo przynajmniej kalendarz Google dobrze to wyświetla niezależnie od strefy którą zapiszę do pliku)
        dt_warsaw_begin = datetime_for_event_begin.astimezone(ZoneInfo("Europe/Warsaw"))
        datetime_for_event_end = datetime(
            event_data[start_or_end].date().year,
            event_data[start_or_end].date().month,
            event_data["flight_day_of_month"],
            int(event_data["planned_landing_time"][:2]),
            int(event_data["planned_landing_time"][2:]),
            tzinfo=ZoneInfo("UTC"),
        )
        # konwersja na odpowiednią strefę czasową (to właściwie nie jest konieczne,
        # bo przynajmniej kalendarz Google dobrze to wyświetla niezależnie od strefy którą zapiszę do pliku)
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
