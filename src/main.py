from collections import Counter
from typing import Any

import aioredis
import asyncpg
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from pydantic.fields import Field
from starlette.status import HTTP_201_CREATED

from src.generate_data import get_random_dev_type, get_random_mac_address

app = FastAPI()


@app.on_event('startup')
async def startup_event() -> None:
    app.state.redis = await aioredis.create_redis_pool('redis://redis:6379')
    app.state.pg = await asyncpg.connect(
        "postgresql://postgres:example@db:5432"
    )


class Words(BaseModel):
    first: str = Field(..., min_length=1)
    second: str = Field(..., min_length=1)


class CountDevicesByDevID(BaseModel):
    dev_id: str
    count: int


# Проверяет на то, что является анаграммой,
# приводя к нижнему регистру.
# Подсчитывает кол-во таких пар
@app.post("/anagram")
async def anagram_counter(words: Words, request: Request) -> Any:
    is_anagram = False
    response = {}
    first = words.first.lower()
    second = words.second.lower()
    if Counter(first) == Counter(second) and first != second:
        is_anagram = True
        pipe = request.app.state.redis.pipeline()
        pipe.incr(first+second)
        pipe.incr(second+first)
        counter, _ = await pipe.execute()
        response["anagram"] = is_anagram
        response["counter"] = counter
    else:
        response["anagram"] = is_anagram
    return response


@app.post("/add_devices", response_class=Response, status_code=201)
async def add_devices(request: Request) -> Response:
    # добавлена 1, чтобы в unnnest успешно произошло приведение типов
    values = [(1, get_random_dev_type(), get_random_mac_address())
              for _ in range(10)]
    statement_devices = """
    INSERT INTO devices (dev_id, dev_type)
    (
    SELECT
        r.dev_id, r.dev_type
     FROM
        unnest($1::devices[]) as r
    )
    RETURNING id;
    """
    result = await request.app.state.pg.fetch(statement_devices, values)

    ids = [[row["id"]] for row in result[:5]]

    statement_endpoints = """
    INSERT INTO endpoints (device_id)
    VALUES($1);
    """
    await request.app.state.pg.executemany(statement_endpoints, ids)
    return Response(status_code=HTTP_201_CREATED)


@app.get("/without_endpoint", response_model=list[CountDevicesByDevID])
async def without_endpoint(request: Request) -> list[CountDevicesByDevID]:
    statement = """
    SELECT dev_id, COUNT(*) as count FROM devices
    WHERE id NOT IN (SELECT device_id FROM endpoints)
    GROUP BY dev_id
    """
    result = await request.app.state.pg.fetch(statement)
    return [CountDevicesByDevID(dev_id=row["dev_id"], count=row["count"])
            for row in result]
