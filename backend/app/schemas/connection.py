from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class DBConnectionCreate(BaseModel):
    name: str
    connection_string: str | None = None

    host: str | None = None
    port: int = 5432
    database_name: str | None = None
    username: str | None = None
    password: str | None = None
    ssl_mode: str = "prefer"

    @model_validator(mode="after")
    def require_string_or_fields(self):
        if self.connection_string:
            return self
        missing = [f for f in ("host", "database_name", "username", "password") if not getattr(self, f)]
        if missing:
            raise ValueError(
                f"Provide a connection string, or all of: host, database_name, username, password. Missing: {', '.join(missing)}"
            )
        return self


class DBConnectionUpdate(BaseModel):
    name: str | None = None
    connection_string: str | None = None
    host: str | None = None
    port: int | None = None
    database_name: str | None = None
    username: str | None = None
    password: str | None = None
    ssl_mode: str | None = None


class DBConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    host: str
    port: int
    database_name: str
    username: str
    ssl_mode: str
    is_demo: bool
    has_write_access: bool | None
    schema_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AccessScriptRequest(BaseModel):
    # None means "every table the connection can currently read" -- the common
    # case, and what the UI sends until a table picker exists.
    tables: list[str] | None = None


class AccessScriptResponse(BaseModel):
    role: str
    password: str
    tables: list[str]
    script: str
    connection_string: str


class TestConnectionResult(BaseModel):
    success: bool
    message: str


class SchemaColumn(BaseModel):
    name: str
    type: str
    nullable: bool
    is_primary_key: bool


class SchemaForeignKey(BaseModel):
    column: str | None
    references_table: str
    references_column: str | None


class SchemaTable(BaseModel):
    name: str
    columns: list[SchemaColumn]
    primary_keys: list[str]
    foreign_keys: list[SchemaForeignKey]


class SchemaResponse(BaseModel):
    tables: list[SchemaTable]
