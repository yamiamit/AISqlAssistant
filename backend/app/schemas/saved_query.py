from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SavedQueryCreate(BaseModel):
    name: str
    prompt_text: str
    sql_text: str
    db_connection_id: int | None = None


class SavedQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    prompt_text: str
    sql_text: str
    db_connection_id: int | None
    created_at: datetime
