
from datetime import datetime, timezone

from pymongo.asynchronous.database import AsyncDatabase


CACHE_LIMIT = 25


async def get_cached_procedure(
    db: AsyncDatabase,
    hcpcs: str,
    year: int,
    modifier: str | None,
    resource_id: str
):
    collection = db["cms_cache"]

    query = {
        "hcpcs": hcpcs,
        "year": year,
        "modifier": modifier,
        "resource_id": resource_id
    }

    document = await collection.find_one(
        query,
        {"_id": 0}
    )

    if document:
        await collection.update_one(
            query,
            {"$set": {
                "last_accessed": datetime.now(timezone.utc)
            }}
        )

    return document


async def save_procedure(
    db: AsyncDatabase,
    hcpcs: str,
    year: int,
    modifier: str | None,
    resource_id: str,
    records: list[dict]
):
    collection = db["cms_cache"]
    now = datetime.now(timezone.utc)

    query = {
        "hcpcs": hcpcs,
        "year": year,
        "modifier": modifier,
        "resource_id": resource_id
    }

    document = {
        **query,
        "records": records,
        "retrieved_at": now,
        "last_accessed": now
    }

    await collection.update_one(
        query,
        {"$set": document},
        upsert=True
    )

    # Remove least recently used records
    count = await collection.count_documents({})

    if count > CACHE_LIMIT:
        excess = count - CACHE_LIMIT

        cursor = collection.find(
            {},
            {"_id": 1}
        ).sort("last_accessed", 1).limit(excess)

        old_records = await cursor.to_list(length=excess)

        await collection.delete_many({
            "_id": {
                "$in": [record["_id"] for record in old_records]
            }
        })

    return document
