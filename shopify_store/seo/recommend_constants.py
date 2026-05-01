MAX_HANDLE_WORDS = 8
MAX_TITLE_LENGTH = 65
MAX_DESCRIPTION_LENGTH = 155

BRAND_UPPER = {"akuku", "bibs", "b.o.", "canpol", "chicco", "lovi", "medela"}
POLISH_ASCII = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ź": "Z",
        "Ż": "Z",
    }
)

SKIP_DESCRIPTION_MARKERS = {
    "aby komplet",
    "wiadomości do sprzedającego",
    "zanim zamówisz",
    "marka:",
    "produkt:",
    "rodzaj:",
}

FORCE_HANDLE_CHANGE = {
    "podstawowy-md",
    "podstawowy-md-1",
    "podstawowy-md-2",
    "torba-do-szpitala-1",
    "torba-do-szpitala-2",
    "torba-do-szpitala-3",
}

STOP_HANDLE_WORDS = {
    "a",
    "copy",
    "dla",
    "i",
    "na",
    "nr",
    "op",
    "oraz",
    "po",
    "rozm",
    "rozmiar",
    "szt",
    "wariant",
    "z",
}

JUNK_PATTERNS = [
    r"\bcopy\b",
    r"\b\d{4,}\b",
    r"\b[0-9]{1,3}/[0-9]{1,3}\b",
    r"\b[a-z]{1,4}\d{2,}[a-z0-9-]*\b",
    r"\b\d+[a-z]{0,2}\+\b",
]
