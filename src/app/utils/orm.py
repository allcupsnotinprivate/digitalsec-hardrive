from typing import Any

from pydantic import BaseModel
from sqlalchemy import Dialect, TypeDecorator
from sqlalchemy.sql.sqltypes import JSON


class PydanticJSON(TypeDecorator[JSON]):
    impl = JSON

    def __init__(self, model_class: type[BaseModel], *args: tuple[Any], **kwargs: dict[str, Any]):
        self.model_class = model_class
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        return value

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        if isinstance(value, dict):
            return self.model_class.model_validate(value)
        return value
