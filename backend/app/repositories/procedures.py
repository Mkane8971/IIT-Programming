from pymongo.asynchronous.database import AsyncDatabase


async def get_procedure(
        db: AsyncDatabase,
        hcpcs: str,
        year: int,
        modifier: str | None = None
):
    collection = db["pfs_procedures"]

    query = {
        "hcpcs": hcpcs,
        "year": year,
        "modifier": modifier
    }

    procedure = await collection.find_one(
        query,
        {"_id": 0}
    )

    return procedure
