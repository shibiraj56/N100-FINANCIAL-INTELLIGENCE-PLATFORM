"""
Normalisation Module
Provides functions to normalise financial years and company ticker symbols.
"""

import re
from typing import Optional, Union

# Month name to 2-digit month mapping
MONTH_MAP = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "sept": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}


def normalize_year(val: Union[str, int, float, None], strict: bool = False) -> Optional[str]:
    """
    Standardises financial year inputs into 'YYYY-MM' format (or 'TTM' for trailing twelve months).
    
    Supported input formats:
      - '2023-03' (already normalized)
      - 'Mar-23', 'Mar 23', 'March-2023', 'Dec 2012'
      - 'Mar 2016 9m', 'Mar 2023 15'
      - 2023, '2023', 2023.0 (defaults to March FY close: '2023-03')
      - '2024.5' or 2024.5 (defaults to September mid-year: '2024-09')
      - 'FY23', 'FY 2023', 'FY-23' (defaults to March FY close: '2023-03')
      - '2022-23' (defaults to end year March: '2023-03')
      - 'TTM' (preserved as 'TTM')
    """
    if val is None:
        if strict:
            raise ValueError("Year cannot be None")
        return None

    # Clean string representation
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "nat", ""):
        if strict:
            raise ValueError("Empty or null year value")
        return None

    # Preserve TTM
    if s.upper() == "TTM":
        return "TTM"

    # 1. Already normalised 'YYYY-MM'
    if re.match(r"^\d{4}-(0[1-9]|1[0-2])$", s):
        return s

    # 2. Decimal half-year representation: e.g. 2024.5 -> 2024-09
    m_half = re.match(r"^(\d{4})\.5$", s)
    if m_half:
        return f"{m_half.group(1)}-09"

    # 3. Integer or float representation: e.g. 2023 or 2023.0
    m_int = re.match(r"^(\d{4})(?:\.0+)?$", s)
    if m_int:
        year_num = int(m_int.group(1))
        if 1950 <= year_num <= 2099:
            return f"{year_num}-03"

    # 4. Fiscal Year formats: 'FY23', 'FY 23', 'FY-23', 'FY2023', 'FY 2023'
    m_fy = re.match(r"^FY[\s\-]?(\d{2,4})$", s, re.IGNORECASE)
    if m_fy:
        raw_yr = m_fy.group(1)
        if len(raw_yr) == 2:
            yr = 2000 + int(raw_yr) if int(raw_yr) < 50 else 1900 + int(raw_yr)
        else:
            yr = int(raw_yr)
        if 1950 <= yr <= 2099:
            return f"{yr}-03"

    # 5. Multi-year fiscal year: '2022-23' or '2022-2023'
    m_split_fy = re.match(r"^(\d{4})[\-/](\d{2,4})$", s)
    if m_split_fy:
        part1 = int(m_split_fy.group(1))
        part2 = int(m_split_fy.group(2))
        if len(m_split_fy.group(2)) == 2:
            part2 = (part1 // 100) * 100 + part2
        if 1950 <= part2 <= 2099:
            return f"{part2}-03"

    # 6. Month and Year, with optional period suffix (e.g. 'Mar 2016 9m', 'Mar 2023 15')
    m_my = re.match(r"^([A-Za-z]+)[\s\-_/]+(\d{2,4})(?:[\s\-_/]+.*)?$", s)
    if m_my:
        month_str = m_my.group(1).lower()
        yr_str = m_my.group(2)
        if month_str in MONTH_MAP:
            mm = MONTH_MAP[month_str]
            if len(yr_str) == 2:
                yr = 2000 + int(yr_str) if int(yr_str) < 50 else 1900 + int(yr_str)
            else:
                yr = int(yr_str)
            if 1950 <= yr <= 2099:
                return f"{yr}-{mm}"

    # Match Year first: '(\d{2,4})[\s\-_/]+([A-Za-z]+)'
    m_ym = re.match(r"^(\d{2,4})[\s\-_/]+([A-Za-z]+)(?:[\s\-_/]+.*)?$", s)
    if m_ym:
        yr_str = m_ym.group(1)
        month_str = m_ym.group(2).lower()
        if month_str in MONTH_MAP:
            mm = MONTH_MAP[month_str]
            if len(yr_str) == 2:
                yr = 2000 + int(yr_str) if int(yr_str) < 50 else 1900 + int(yr_str)
            else:
                yr = int(yr_str)
            if 1950 <= yr <= 2099:
                return f"{yr}-{mm}"

    if strict:
        raise ValueError(f"Unable to parse year string: '{val}'")
    return None


def normalize_ticker(ticker: Union[str, None], strict: bool = False) -> Optional[str]:
    """
    Cleans and standardises stock ticker symbol.
    
    Rules:
      - Strips leading and trailing whitespace
      - Converts to uppercase
      - Preserves valid characters: alphanumeric, hyphens (e.g. BAJAJ-AUTO), ampersands (e.g. M&M)
      - Enforces length between 2 and 12 characters
    """
    if ticker is None:
        if strict:
            raise ValueError("Ticker cannot be None")
        return None

    cleaned = str(ticker).strip().upper()
    if not cleaned or cleaned in ("NAN", "NONE", "NULL", ""):
        if strict:
            raise ValueError("Empty ticker symbol")
        return None

    # Validate character set (alphanumeric, -, &)
    if not re.match(r"^[A-Z0-9\-&]+$", cleaned):
        if strict:
            raise ValueError(f"Ticker contains invalid characters: '{ticker}'")
        return None

    # Length requirement: 2 - 12 characters
    if not (2 <= len(cleaned) <= 12):
        if strict:
            raise ValueError(f"Ticker length must be between 2 and 12 characters: '{ticker}'")
        return None

    return cleaned
