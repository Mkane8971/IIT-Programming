
from decimal import Decimal, ROUND_HALF_UP


def calculate_payment(
    procedure: dict,
    locality: dict,
    setting: str,
    year: int
) -> dict:
    if setting not in ("facility", "nonfacility"):
        raise ValueError("Invalid facility setting")

    # CMS returns numeric values as strings
    work_rvu = Decimal(procedure["rvu_work"])
    mp_rvu = Decimal(procedure["rvu_mp"])
    conversion_factor = Decimal(procedure["conv_fact"])

    # Select the applicable practice expense RVU
    if setting == "facility":
        pe_value = (
            procedure.get("full_fac_pe")
            or procedure.get("fac_pe")
        )
    else:
        pe_value = (
            procedure.get("full_nfac_pe")
            or procedure.get("nfac_pe")
        )

    if pe_value in (None, ""):
        raise ValueError("Practice expense RVU unavailable")

    pe_rvu = Decimal(pe_value)

    # Geographic Practice Cost Indices
    work_gpci = Decimal(locality["gpci_work"])
    pe_gpci = Decimal(locality["gpci_pe"])
    mp_gpci = Decimal(locality["gpci_mp"])

    # Medicare Physician Fee Schedule formula
    adjusted_rvu = (
        work_rvu * work_gpci
        + pe_rvu * pe_gpci
        + mp_rvu * mp_gpci
    )

    payment = (
        adjusted_rvu * conversion_factor
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    return {
        "hcpcs": procedure["hcpc"],
        "description": procedure.get("sdesc", ""),
        "year": year,
        "cms_release": procedure.get("year"),
        "modifier": procedure.get("modifier"),
        "setting": setting,
        "locality": locality["locality"],
        "locality_name": locality["loc_description"],
        "price_indicator": procedure.get("price_ind"),
        "work_rvu": str(work_rvu),
        "pe_rvu": str(pe_rvu),
        "mp_rvu": str(mp_rvu),
        "work_gpci": str(work_gpci),
        "pe_gpci": str(pe_gpci),
        "mp_gpci": str(mp_gpci),
        "conversion_factor": str(conversion_factor),
        "adjusted_rvu": str(adjusted_rvu),
        "estimated_payment": str(payment)
    }
