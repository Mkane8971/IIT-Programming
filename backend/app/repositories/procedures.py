import logging
import time
from datetime import datetime, timezone

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError


logger = logging.getLogger(__name__)

CACHE_LIMIT = 25
CACHE_RETRY_SECONDS = 60

_cache_disabled_until = 0.0
_cache_state = "unknown"


def cache_status() -> str:
    if time.monotonic() < _cache_disabled_until:
        return "unavailable"

    if _cache_state == "unavailable":
        return "retry_pending"

    return _cache_state


def _cache_enabled() -> bool:
    return time.monotonic() >= _cache_disabled_until


def _mark_available() -> None:
    global _cache_disabled_until, _cache_state

    if _cache_state != "available":
        logger.info("MongoDB cache connection available")

    _cache_disabled_until = 0.0
    _cache_state = "available"


def _mark_unavailable(exc: PyMongoError) -> None:
    global _cache_disabled_until, _cache_state

    _cache_disabled_until = (
        time.monotonic() + CACHE_RETRY_SECONDS
    )
    _cache_state = "unavailable"

    logger.warning(
        "MongoDB cache unavailable. "
        "Bypassing cache for %s seconds: %s",
        CACHE_RETRY_SECONDS,
        exc,
    )


async def get_cached_procedure(
    db: AsyncDatabase,
    hcpcs: str,
    year: int,
    modifier: str | None,
    resource_id: str,
):
    if not _cache_enabled():
        return None

    collection = db["cms_cache"]

    query = {
        "hcpcs": hcpcs,
        "year": year,
        "modifier": modifier,
        "resource_id": resource_id,
    }

    try:
        document = await collection.find_one(
            query,
            {"_id": 0},
        )

        if document:
            await collection.update_one(
                query,
                {
                    "$set": {
                        "last_accessed": datetime.now(timezone.utc)
                    }
                },
            )

        _mark_available()
        return document

    except PyMongoError as exc:
        _mark_unavailable(exc)
        return None


async def save_procedure(
    db: AsyncDatabase,
    hcpcs: str,
    year: int,
    modifier: str | None,
    resource_id: str,
    records: list[dict],
):
    if not _cache_enabled():
        return None

    collection = db["cms_cache"]
    now = datetime.now(timezone.utc)

    query = {
        "hcpcs": hcpcs,
        "year": year,
        "modifier": modifier,
        "resource_id": resource_id,
    }

    document = {
        **query,
        "records": records,
        "retrieved_at": now,
        "last_accessed": now,
    }

    try:
        await collection.update_one(
            query,
            {"$set": document},
            upsert=True,
        )

        count = await collection.count_documents({})

        if count > CACHE_LIMIT:
            excess = count - CACHE_LIMIT

            cursor = collection.find(
                {},
                {"_id": 1},
            ).sort("last_accessed", 1).limit(excess)

            old_records = await cursor.to_list(
                length=excess
            )

            await collection.delete_many(
                {
                    "_id": {
                        "$in": [
                            record["_id"]
                            for record in old_records
                        ]
                    }
                }
            )

        _mark_available()
        return document

    except PyMongoError as exc:
        _mark_unavailable(exc)
        return None