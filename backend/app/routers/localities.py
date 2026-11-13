
from fastapi import APIRouter, HTTPException, Query
import httpx

from app.clients.cms import CMSClient


router = APIRouter(
    prefix="/api/v1/localities",
    tags=["Localities"]
)


@router.get("")
async def get_localities(
    year: int = Query(ge=2000, le=2100)
):
    cms = CMSClient()

    try:
        records = await cms.get_localities(year)

        return {
            "year": year,
            "count": len(records),
            "localities": records
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve CMS locality data"
        ) from exc
