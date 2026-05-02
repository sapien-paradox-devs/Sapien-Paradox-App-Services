from datetime import datetime
from typing import Optional
from ninja import Schema


class ChapterOut(Schema):
    title: str
    order_index: int
    book_title: str


class GrantOut(Schema):
    chapter: ChapterOut
    shard_id: str
    opened_at: Optional[datetime] = None
