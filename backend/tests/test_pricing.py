
from app.services.pricing import calculate_payment


def test_arizona_facility_payment():
    procedure = {
        "hcpc": "27447",
        "year": "2026",
        "modifier": None,
        "price_ind": "9",
        "rvu_work": "19.11",
        "full_fac_pe": "11.58",
        "rvu_mp": "4.02",
        "conv_fact": "33.4009"
    }

    locality = {
        "locality": "0310200",
        "loc_description": "ARIZONA",
        "gpci_work": "1.000",
        "gpci_pe": "0.969",
        "gpci_mp": "0.856"
    }

    result = calculate_payment(
        procedure,
        locality,
        setting="facility",
        year=2026
    )

    assert result["estimated_payment"] == "1128.02"
    assert result["year"] == 2026
    assert result["cms_release"] == "2026"