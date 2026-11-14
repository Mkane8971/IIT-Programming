
import os
import re

import httpx


class CMSClient:
    def __init__(self):
        self.url = os.environ["CMS_PFS_API_URL"]
        self.catalog_url = (
            "https://pfs.data.cms.gov/api/1/"
            "metastore/schemas/dataset/items"
        )

    async def get_resource_id(
            self,
            year: int,
            dataset_type: str = "Indicators"
            ):
        async with httpx.AsyncClient(timeout=30.0) as client:

            # Retrieve CMS dataset catalog
            response = await client.get(
                self.catalog_url,
                params={"limit": 200}
            )
            response.raise_for_status()
            datasets = response.json()

            # Find all Indicators datasets for the requested year
            if dataset_type not in ("Indicators", "Localities"):
                raise ValueError(
                    f"Invalid dataset type: {dataset_type}"
                )

            matches = [
                dataset
                for dataset in datasets
                if re.fullmatch(
                    rf"{dataset_type} for {year}([A-Z])?",
                    dataset.get("title", "").strip(),
                    flags=re.IGNORECASE
                )
            ]

            if not matches:
                raise ValueError(
                    f"No Indicators dataset found for {year}"
                )

            # Select the highest release suffix (A, B, C, D...)
            # Unsuffixed datasets sort before suffixed datasets.
            def release_order(dataset):
                title = dataset["title"].strip().upper()
                suffix = title.removeprefix(
                    f"{dataset_type.upper()} FOR {year}"
                ).strip()
                return suffix

            latest = max(matches, key=release_order)

            dataset_id = latest["identifier"]

            print(f"Selected CMS dataset: {latest['title']}")

            # Retrieve resource metadata
            response = await client.get(
                f"{self.catalog_url}/{dataset_id}",
                params={"show-reference-ids": "true"}
            )
            response.raise_for_status()

            metadata = response.json()
            distributions = metadata.get("distribution", [])

            if len(distributions) != 1:
                raise ValueError(
                    "Expected exactly one datastore resource"
                )

            resource_id = distributions[0].get("identifier")

            if not resource_id or not re.fullmatch(
                r"[a-fA-F0-9-]{36}", resource_id
            ):
                raise ValueError(
                    "Valid datastore resource ID not found"
                )

            return resource_id

    async def get_procedure(
        self,
        hcpcs: str,
        year: int,
        modifier: str | None = None,
        resource_id: str | None = None
    ):
        # Validate inputs
        hcpcs = hcpcs.strip().upper()

        if not re.fullmatch(r"[A-Z0-9]{5}", hcpcs):
            raise ValueError("Invalid HCPCS code")

        if not 2000 <= year <= 2100:
            raise ValueError("Invalid year")

        if modifier is not None:
            modifier = modifier.strip().upper()

            if not re.fullmatch(r"[A-Z0-9]{2}", modifier):
                raise ValueError("Invalid modifier")

        # Resolve the latest available dataset for the year
        if resource_id is None:
            resource_id = await self.get_resource_id(year)

        # Build CMS datastore SQL query
        query = (
            f"[SELECT * FROM {resource_id}]"
            f'[WHERE hcpc = "{hcpcs}"]'
            "[LIMIT 100 OFFSET 0]"
        )

        # Request CMS procedure data
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.url,
                params={"query": query}
            )
            response.raise_for_status()
            records = response.json()
            print("Raw CMS records:", records[:3], flush=True)

        # Normalize CMS modifier values
        for record in records:
            record["modifier"] = (
                record.get("modifier") or ""
            ).strip() or None

        # Return matching modifier records
        return [
            record for record in records
            if record["modifier"] == modifier
        ]

    async def get_localities(self, year: int):
        if not 2000 <= year <= 2100:
            raise ValueError("Invalid year")

        # Find the CMS Localities resource
        resource_id = await self.get_resource_id(
            year,
            dataset_type="Localities"
        )

        # Retrieve locality and GPCI records
        query = (
            f"[SELECT * FROM {resource_id}]"
            "[LIMIT 200 OFFSET 0]"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.url,
                params={"query": query}
            )
            response.raise_for_status()

            return response.json()
