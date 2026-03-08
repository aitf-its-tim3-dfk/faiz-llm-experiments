import asyncio
import urllib.parse
import httpx
from typing import List, Dict


class RetrievalQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._worker_task = None

    async def start(self):
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def retrieve(self, query: str) -> List[Dict]:
        """Submit a query to the queue and wait for its result."""
        future = asyncio.get_running_loop().create_future()
        await self._queue.put((query, future))
        return await future

    async def _worker(self):
        """Process queries in batches of up to 3 to improve throughput without excessive rate-limiting."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                # Wait for at least one item
                batch = [await self._queue.get()]

                # Try to get up to 2 more items immediately if available
                while len(batch) < 3 and not self._queue.empty():
                    batch.append(self._queue.get_nowait())

                async def process_item(item):
                    query, future = item
                    try:
                        results = await self._perform_search(client, query)
                        future.set_result(results)
                    except Exception as e:
                        future.set_exception(e)
                    finally:
                        self._queue.task_done()

                await asyncio.gather(*(process_item(item) for item in batch))

                # Small delay between batches to respect rate limits
                await asyncio.sleep(1)

    async def _perform_search(
        self, client: httpx.AsyncClient, query: str
    ) -> List[Dict]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://4get.canine.tools/api/v1/web?s={encoded_query}&scraper=ddg&nsfw=yes&country=id-en"

        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        answers = data.get("answer", [])
        webs = data.get("web", [])

        all_results = [*answers, *webs]
        formatted_results = []

        for r in all_results:
            desc = r.get("description", "")
            if isinstance(desc, list):
                if len(desc) > 0 and isinstance(desc[0], dict):
                    desc = desc[0].get("value", "")
                else:
                    desc = str(desc)

            formatted_results.append(
                {
                    "title": r.get("title", query),
                    "description": desc,
                    "url": r.get("url", ""),
                }
            )

        return formatted_results


# Global singleton
search_queue = RetrievalQueue()
