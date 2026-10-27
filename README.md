from datetime import date

from services import extraction_service as ex
from services import vaccine_service
from services.ocr_service import OCRLine

TODAY = date(2026, 10, 11)


def lines(*texts, conf=92.0):
    return [OCRLine(t, conf) for t in texts]


def test_date_formats_are_normalised():
    cases = {
        "given on 14/03/2020": "2020-03-14",
        "2021-07-09": "2021-07-09",
        "5 Mar 2022": "2022-03-05",
        "March 5, 2022": "2022-03-05",
        "04.06.24": "2024-06-04",
        "12/O3/2O2O": "2020-03-12",  # letter O misread for zero
    }
    for text, expected in cases.items():
        assert ex.normalize_date(text, "DMY", TODAY) == expected, text


def test_date_order_setting_changes_the_reading():
    assert ex.normalize_date("03/04/2022", "DMY", TODAY) == "2022-04-03"
    assert ex.normalize_date("03/04/2022", "MDY", TODAY) == "2022-03-04"
    assert ex.normalize_date("25/12/2022", "MDY", TODAY) == "2022-12-25"  # only valid reading


def test_unreadable_or_partial_dates_stay_blank():
    assert ex.normalize_date("31/02/2022", "DMY", TODAY) is None
    hit = ex.find_dates("Mar 2022", "DMY", TODAY)[0]
    assert hit.partial and hit.iso is None
    assert ex.normalize_date("no date here", "DMY", TODAY) is None


def test_ambiguous_dates_are_flagged():
    out = ex.extract_candidates(lines("OPV 1 03/04/2022"), "DMY", today=TODAY)[0]
    assert any("check the day and month" in i for i in out["issues"])
    clear = ex.extract_candidates(lines("OPV 1 25/04/2022"), "DMY", today=TODAY)[0]
    assert not any("day and month" in i for i in clear["issues"])


def test_vaccine_names_match_aliases_and_typos():
    assert vaccine_service.canonicalize("Hep-B")[0]["id"] == "hepb"
    assert vaccine_service.canonicalize("Covishield")[0]["id"] == "covid19"
    vaccine, score = vaccine_service.canonicalize("Pentavalnt")
    assert vaccine["id"] == "penta" and score < 1.0
    assert vaccine_service.canonicalize("banana smoothie")[0] is None
    assert vaccine_service.canonicalize("Vaccine")[0] is None


def test_extracts_vaccine_dose_and_date():
    rows = ex.extract_candidates(lines("Hepatitis B Dose 2 15 Mar 2024", "OPV 3 06/08/2023", "BCG 12/03/2001"), today=TODAY)
    got = [(r["vaccine_name"], r["dose_number"], r["vaccination_date"]) for r in rows]
    assert ("Hepatitis B", 2, "2024-03-15") in got
    assert ("Oral polio vaccine (OPV)", 3, "2023-08-06") in got
    assert ("BCG", None, "2001-03-12") in got


def test_missing_fields_are_left_blank_not_invented():
    rows = ex.extract_candidates(lines("Rotavirus"), today=TODAY)
    assert rows[0]["vaccination_date"] is None and rows[0]["dose_number"] is None
    assert "Date not found." in rows[0]["issues"]
    assert all(r["verification_status"] == "unverified" for r in rows)


def test_multiple_doses_on_one_line():
    rows = ex.extract_candidates(lines("OPV 1 06/08/2023 2 10/09/2023"), today=TODAY)
    assert [(r["dose_number"], r["vaccination_date"]) for r in rows] == [(1, "2023-08-06"), (2, "2023-09-10")]


def test_date_on_next_line_is_attached_with_a_warning():
    row = ex.extract_candidates(lines("Pentavalent 1", "25/04/2020"), today=TODAY)[0]
    assert row["vaccination_date"] == "2020-04-25" and any("line below" in i for i in row["issues"])


def test_age_phrases_are_not_dose_numbers_and_titles_are_ignored():
    td = ex.extract_candidates(lines("Td 10 years 12/12/2010"), today=TODAY)[0]
    assert td["dose_number"] is None
    mr = ex.extract_candidates(lines("Mr Sharma 12/03/2001 clinic"), today=TODAY)[0]
    assert mr["vaccine_name"] == ""


def test_low_confidence_is_reported():
    row = ex.extract_candidates(lines("OPV 1 25/04/2020", conf=41.0), today=TODAY)[0]
    assert any("hard to read" in i for i in row["issues"])


def test_extracts_next_due_date_from_labelled_vaccine_row():
    row = ex.extract_candidates(
        lines("Hepatitis B 1 11 Oct 2026 Next Due Date 08 Nov 2026"),
        today=date(2026, 10, 12),
    )[0]
    assert row["vaccination_date"] == "2026-10-11"
    assert row["next_due_date"] == "2026-11-08"


def test_extracts_future_due_date_from_table_row_without_repeated_header():
    row = ex.extract_candidates(
        lines("Hepatitis B 1 11 Oct 2026 08 Nov 2026"),
        today=date(2026, 10, 12),
    )[0]
    assert row["vaccination_date"] == "2026-10-11"
    assert row["next_due_date"] == "2026-11-08"
