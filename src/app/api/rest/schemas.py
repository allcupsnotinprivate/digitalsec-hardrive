import math

from pydantic import Field

from app.utils.schemas import BaseAPISchema


class PaginationParams(BaseAPISchema):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, alias="pageSize", ge=1, le=100)


class PageMeta(BaseAPISchema):
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(alias="pageSize", ge=1)
    pages: int = Field(ge=0)


def build_page_info(*, total: int, page: int, page_size: int) -> PageMeta:
    pages = math.ceil(total / page_size) if total else 0
    return PageMeta(total=total, page=page, pageSize=page_size, pages=pages)
