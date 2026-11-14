from datetime import datetime, timedelta, timezone
import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal

from app.clients.cms import CMSClient
from app.repositories.procedures import (
    get_cached_procedure,
    save_procedure,
    cache_status,
)
from app.services.pricing import calculate_payment

router = APIRouter(
    prefix="/api/v1/pricing",
    tags=["Pricing"],
)


@router.get("/estimate")
async def estimate_payment(
    request: Request,
    hcpcs: str = Query(
        pattern=r"^[A-Za-z0-9]{5}$",
        min_length=5,
        max_length=5,
    ),
    year: int = Query(ge=2000, le=2100),
    modifier: str | None = Query(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z0-9]{2}$"
    ),
    setting: Literal["facility", "nonfacility"] = "facility",
    locality: str | None = Query(
        default=None,
        min_length=1,
        max_length=100
    )
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
        records = None
        source = "cms"

        # Reuse records cached within the last 24 hours
        if cached:
            retrieved_at = cached.get("retrieved_at")

            if retrieved_at.tzinfo is None:
                retrieved_at = retrieved_at.replace(
                    tzinfo=timezone.utc
                )

            if datetime.now(timezone.utc) - retrieved_at < timedelta(hours=24):
                records = cached["records"]
                source = "mongodb"

        # Fetch fresh records
        if records is None:
            records = await cms.get_procedure(
                hcpcs,
                year,
                modifier,
                resource_id=resource_id,
            )

            if records:
                await save_procedure(
                    db, hcpcs, year, modifier, resource_id, records
                )

        if not records:
            raise HTTPException(
                    status_code=404,
                    detail="Procedure not found for the selected year",
            )

        localities = await cms.get_localities(year)
        selected_locality = next(
             (
                  item for item in localities
                  if item["locality"] == locality
             ),
             None,
        )

        if selected_locality is None:
            raise HTTPException(
                status_code=404,
                detail="Locality not found for the selected year",
            )

        estimates = [
            calculate_payment(
                procedure=record,
                locality=selected_locality,
                setting=setting,
            )
            for record in records
        ]

        return {
            "hcpcs": hcpcs,
            "year": year,
            "setting": setting,
            "source": source,
            "cache_status": cache_status(),
            "locality": selected_locality,
            "estimates": estimates
        }

    except HTTPException:
        raise

    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to calculate estimate: {exc}",
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve CMS data"
        ) from exc
