from typing import Literal
from fastapi import APIRouter, HTTPException, Path, Query, Request
from app.repositories.procedures import get_procedure

router = APIRouter(
    prefix="/api/v1/procedures",
    tags=["Procedures"]
)

@router.get("/{hcpcs}")
async def read_procedure(
        request: Request,
        hcpcs: str = Path(
            pattern=r"^[A-Za-z0-9]{5}$",
            description="The HCPCS code of the procedure."
            ),
        year: int = Query(
            ge=2000,
            le=2100,
            description="The year of the procedure."),
        modifier: str | None = Query(
            default=None,
            min_length=2,
            max_length=2,
            pattern=r"^[A-Za-z0-9]{2}$",
            description="The modifier of the procedure."),
        setting: Literal["facility", "non-facility"] = "facility"
):
    """
    Retrieve a procedure by its HCPCS code, year, and optional modifier.
    """
    hcpcs = hcpcs.upper()
    modifier = modifier.upper() if modifier else None

    db = request.app.state.db
    procedure = await get_procedure(
        db=db,
        hcpcs=hcpcs,
        year=year,
        modifier=modifier)

    if not procedure or procedure is None:
        raise HTTPException(status_code=404, detail="Procedure not found")

    pe_field = (
        "facility_pe_rvu"
        if setting == "facility"
        else "non_facility_pe_rvu"
    )

    return {
        "hcpcs": hcpcs,
        "year": year,
        "modifier": modifier,
        "setting": setting,
        "work_rvu": procedure.get("work_rvu"),
        "practice_expense_rvu": procedure.get(pe_field),
        "malpractice_rvu": procedure.get("malpractice_rvu")
    }
