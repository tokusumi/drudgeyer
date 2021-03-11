import asyncio
from typing import Dict

import uvicorn

from drudgeyer.log_tracker.broadcasting import BaseReadStreamer, create_app


class ToyReadStreamer(BaseReadStreamer):
    key_to_id: Dict[str, str] = {}
    id_cnt: Dict[str, int] = {}

    async def get(self, key: str) -> str:
        if key not in self.key_to_id:
            raise KeyError("must add key at first")
        try:
            await asyncio.sleep(0.5)
            id = self.key_to_id.get(key)
            self.id_cnt[id] += 1
            return f"key: {key}. id: {id}. cnt: {self.id_cnt[id]}. tot: {len(self.key_to_id)}"
        except (RuntimeError, asyncio.CancelledError) as e:
            print(e)
        raise ValueError("broken connection. try again")

    async def add_client(self, id: str, key: str) -> None:
        await asyncio.sleep(0.01)
        self.key_to_id[key] = id
        if id not in self.id_cnt:
            self.id_cnt[id] = 0

    async def delete(self, key: str) -> None:
        id = self.key_to_id[key]
        try:
            del self.key_to_id[key]
        except KeyError:
            pass
        if id not in self.key_to_id.values():
            del self.id_cnt[id]
        await asyncio.sleep(0.05)


if __name__ == "__main__":
    app = create_app(ToyReadStreamer())
    uvicorn.run(app)