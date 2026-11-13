
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request
import httpx

from app.clients.cms import CMSClient
from app.repositories.procedures import (
    get_cached_procedure,
    save_procedure
)


router = APIRouter(
    prefix="/api/v1/procedures",
    tags=["Procedures"]
)


@router.get("/{hcpcs}")
async def read_procedure(
    request: Request,
    hcpcs: str = Path(pattern=r"^[A-Za-z0-9]{5}$"),
    year: int = Query(ge=2000, le=2100),
    modifier: str | None = Query(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z0-9]{2}$"
    ),
    setting: Literal["facility", "nonfacility"] = "facility"
):
    hcpcs = hcpcs.upper()
    modifier = modifier.upper() if modifier else None

    db = request.app.state.db
    cms = CMSClient()

    try:
        # Find CMS resource for the selected year
        resource_id = await cms.get_resource_id(year)

        # Check MongoDB first
        cached = await get_cached_procedure(
            db, hcpcs, year, modifier, resource_id
        )

        # Reuse records cached within the last 24 hours
        if cached:
            retrieved_at = cached["retrieved_at"]

            if retrieved_at.tzinfo is None:
                retrieved_at = retrieved_at.replace(
                    tzinfo=timezone.utc
                )

            if datetime.now(timezone.utc) - retrieved_at < timedelta(hours=24):
                return {
                    "source": "mongodb",
                    "setting": setting,
                    "records": cached["records"]
                }

        # Retrieve data from CMS
        records = await cms.get_procedure(
            hcpcs,
            year,
            modifier,
            resource_id=resource_id
        )

        if not records:
            raise HTTPException(
                status_code=404,
                detail="Procedure not found in CMS"
            )

        # Store the CMS response in MongoDB
        await save_procedure(
            db, hcpcs, year, modifier, resource_id, records
        )

        return {
            "source": "cms",
            "setting": setting,
            "records": records
        }

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="CMS API request failed"
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        ) from exc
