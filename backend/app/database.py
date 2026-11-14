
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pymongo import AsyncMongoClient
from pymongo.server_api import ServerApi


def create_mongo_client():
    server_api = ServerApi(
        version="1",
        strict=True,
        deprecation_errors=True
    )

    mongo_uri = os.getenv("MONGO_URI")

    # Azure / MongoDB Atlas connection
    if mongo_uri:
        return AsyncMongoClient(
            mongo_uri,
            server_api=server_api,
            serverSelectionTimeoutMS=2000
        )

    # Local Docker Compose connection
    return AsyncMongoClient(
        host=os.environ["MONGO_HOST"],
        port=int(os.environ["MONGO_PORT"]),
        username=os.environ["MONGO_USERNAME"],
        password=os.environ["MONGO_PASSWORD"],
        authSource="admin",
        server_api=server_api,
        serverSelectionTimeoutMS=2000
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = create_mongo_client()

    try:
        # MongoDB is an optional cache dependency.
        # Creating the client does not require an active connection.
        app.state.db = client[os.environ["MONGO_DATABASE"]]

        print("FastAPI initialized. MongoDB cache client configured.")

        yield

    finally:
        await client.close()
