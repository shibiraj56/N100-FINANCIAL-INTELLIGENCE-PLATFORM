"""
Unit tests for Year and Ticker normalisation functions.
Meets Day 02 requirement: 35+ unit tests (20 normalize_year, 15+ normalize_ticker).
"""

import pytest
from src.etl.normaliser import normalize_year, normalize_ticker


# ============================================================================
# 20+ UNIT TESTS FOR normalize_year()
# ============================================================================

def test_ny_01_mar_hyphen_2digit():
    assert normalize_year("Mar-23") == "2023-03"

def test_ny_02_mar_space_2digit():
    assert normalize_year("Mar 23") == "2023-03"

def test_ny_03_full_month_name():
    assert normalize_year("March-2023") == "2023-03"

def test_ny_04_integer_year():
    assert normalize_year(2023) == "2023-03"

def test_ny_05_string_integer_year():
    assert normalize_year("2023") == "2023-03"

def test_ny_06_float_year():
    assert normalize_year(2023.0) == "2023-03"

def test_ny_07_fy_2digit():
    assert normalize_year("FY23") == "2023-03"

def test_ny_08_fy_space_2digit():
    assert normalize_year("FY 23") == "2023-03"

def test_ny_09_fy_4digit():
    assert normalize_year("FY2023") == "2023-03"

def test_ny_10_december_hyphen():
    assert normalize_year("Dec-22") == "2022-12"

def test_ny_11_december_space_4digit():
    assert normalize_year("Dec 2012") == "2012-12"

def test_ny_12_june_hyphen():
    assert normalize_year("Jun-23") == "2023-06"

def test_ny_13_september_format():
    assert normalize_year("Sep-21") == "2021-09"

def test_ny_14_already_normalised():
    assert normalize_year("2023-03") == "2023-03"

def test_ny_15_case_insensitivity():
    assert normalize_year("mar-23") == "2023-03"
    assert normalize_year("DEC-20") == "2020-12"

def test_ny_16_whitespace_padding():
    assert normalize_year("   Mar-23   ") == "2023-03"

def test_ny_17_multi_year_fiscal():
    assert normalize_year("2022-23") == "2023-03"

def test_ny_18_year_first_format():
    assert normalize_year("2014 Mar") == "2014-03"

def test_ny_19_none_and_empty():
    assert normalize_year(None) is None
    assert normalize_year("") is None
    assert normalize_year("nan") is None

def test_ny_20_invalid_garbage():
    assert normalize_year("garbage") is None
    with pytest.raises(ValueError):
        normalize_year("garbage", strict=True)


# ============================================================================
# 16+ UNIT TESTS FOR normalize_ticker()
# ============================================================================

def test_nt_01_basic_uppercase():
    assert normalize_ticker("TCS") == "TCS"

def test_nt_02_lowercase_conversion():
    assert normalize_ticker("tcs") == "TCS"

def test_nt_03_whitespace_stripping():
    assert normalize_ticker("  TCS  ") == "TCS"

def test_nt_04_hyphen_preserved():
    assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

def test_nt_05_hyphen_lowercase():
    assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"

def test_nt_06_ampersand_preserved():
    assert normalize_ticker("M&M") == "M&M"

def test_nt_07_ampersand_with_spaces():
    assert normalize_ticker("  m&m  ") == "M&M"

def test_nt_08_ticker_with_digits():
    assert normalize_ticker("3MINDIA") == "3MINDIA"

def test_nt_09_minimum_length_valid():
    assert normalize_ticker("AA") == "AA"

def test_nt_10_maximum_length_valid():
    assert normalize_ticker("ABCDEFGHIJKL") == "ABCDEFGHIJKL"

def test_nt_11_too_short_rejected():
    assert normalize_ticker("A") is None
    with pytest.raises(ValueError):
        normalize_ticker("A", strict=True)

def test_nt_12_too_long_rejected():
    assert normalize_ticker("ABCDEFGHIJKLM") is None
    with pytest.raises(ValueError):
        normalize_ticker("ABCDEFGHIJKLM", strict=True)

def test_nt_13_empty_string():
    assert normalize_ticker("") is None
    with pytest.raises(ValueError):
        normalize_ticker("", strict=True)

def test_nt_14_none_ticker():
    assert normalize_ticker(None) is None
    with pytest.raises(ValueError):
        normalize_ticker(None, strict=True)

def test_nt_15_special_characters_rejected():
    assert normalize_ticker("TCS@NSE") is None
    assert normalize_ticker("TCS$") is None

def test_nt_16_mixed_casing_and_special():
    assert normalize_ticker("  adani-ports  ") == "ADANI-PORTS"
