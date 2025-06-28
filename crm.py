import aiohttp
import asyncio
import os

AMO_ACCOUNT = os.environ["AMO_ACCOUNT"]
# AMO_TOKEN = os.environ["AMO_TOKEN"]
# AMO_SECRET_KEY = os.environ["AMO_SECRET_KEY"]
AMO_LONG_TOKEN = os.environ["AMO_LONG_TOKEN"]


class AmoCrmFetcher:

    async def _get(self, endpoint: str, params: dict = None):
        url = f"{AMO_ACCOUNT}{endpoint}"
        headers = {
            "Authorization": f"Bearer {AMO_LONG_TOKEN}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    raise Exception(
                        f"GET {url} failed: {resp.status} {await resp.text()}"
                    )
                return await resp.json()

    async def _post(self, endpoint: str, payload: dict):
        url = f"{AMO_ACCOUNT}{endpoint}"
        headers = {
            "Authorization": f"Bearer {AMO_LONG_TOKEN}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status not in (200, 202):
                    raise Exception(
                        f"POST {url} failed: {resp.status} {await resp.text()}"
                    )
                return await resp.json()

    async def get_all_statuses_flat(self) -> list[dict]:

        data = await self._get("/api/v4/leads/pipelines")
        result = []
        for pipeline in data.get("_embedded", {}).get("pipelines", []):
            pipeline_id = pipeline["id"]
            pipeline_name = pipeline["name"]
            for status in pipeline["_embedded"]["statuses"]:
                result.append(
                    {
                        "pipeline_id": pipeline_id,
                        "pipeline_name": pipeline_name,
                        "status_id": status["id"],
                        "status_name": status["name"],
                    }
                )
        return result

    async def get_lead_custom_fields(self) -> list:
        """Получить список дополнительных полей для лидов"""
        data = await self._get("/api/v4/leads/custom_fields")
        return data

    async def create_lead(
        self, name: str, pipeline_id: int, status_id: int, custom_fields: dict = None
    ) -> dict:
        """Создать лид с указанием воронки, этапа и доп. полей"""
        lead_data = {"name": name, "pipeline_id": pipeline_id, "status_id": status_id}

        if custom_fields:
            lead_data["custom_fields_values"] = [
                {"field_id": field_id, "values": [{"value": value}]}
                for field_id, value in custom_fields.items()
            ]

        payload = {"add": [lead_data]}
        response = await self._post("/api/v4/leads/complex", payload)
        return response["_embedded"]["leads"][0]

    async def create_lead_full(
        self,
        name: str,
        pipeline_id: int,
        status_id: int,
        price=None,
        custom_fields=None,  #: dict[int, Union[str, int, list[str]]]
    ) -> dict:
        """
        Создаёт лид в указанной воронке/статусе и контакт с телефоном.
        Всё связывается автоматически.
        """

        # 2. Подготавливаем данные для лида
        lead_data = {
            "name": name,
            "pipeline_id": pipeline_id,
            "status_id": status_id,
            "custom_fields_values": custom_fields,
            # "created_at": created_at or int(time.time()),
        }
        # 3. Создаём сделку
        await self._post("/api/v4/leads", {"add": lead_data})


async def main():
    fetcher = AmoCrmFetcher()

    cm = await fetcher.get_lead_custom_fields()
    return

if __name__ == "__main__":
    asyncio.run(main())
