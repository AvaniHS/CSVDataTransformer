"""Pipeline configuration Pydantic models."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

CastType = Literal["str", "int64", "float64", "datetime64[ns]"]
JoinType = Literal["LEFT", "INNER", "RIGHT", "OUTER"]
SourceType = Literal["DIRECT", "DERIVED", "EXPRESSION"]
RightType = Literal["literal", "column"]
LogicType = Literal["AND", "OR"]
ConnectionTypeName = Literal["LOCAL_FILE_DIRECTORY"]
TransformType = Literal["EXPRESSION", "REGEXP_REPLACE", "CASE"]


class FileOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: str = "CSV"
    encoding: str = "utf-8"
    delimiter: str = ","
    quote_char: str = '"'
    header_row: bool = True
    max_file_size_mb: int = Field(default=100, ge=1)


class Connection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ConnectionTypeName
    base_path: str
    target_path: str
    file_options: FileOptions = Field(default_factory=FileOptions)

    @field_validator("type", mode="before")
    @classmethod
    def normalize_connection_type(cls, value: str) -> str:
        if value == "LOCAL_CSV_DIRECTORY":
            return "LOCAL_FILE_DIRECTORY"
        return value

    @property
    def resolved_type(self) -> str:
        return self.type


class RootTable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_ref: str
    file_name: str
    alias: str
    comment: str | None = None


class Predicate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: str
    operator: str
    right: Any | None = None
    right_type: RightType | None = None


class ConditionGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logic: LogicType
    conditions: list[JoinConditionItem]


class ExpressionFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["expression"]
    value: str


JoinConditionItem = Union[Predicate, ConditionGroup]
FilterItem = Union[Predicate, ConditionGroup, ExpressionFilter]


class Join(BaseModel):
    model_config = ConfigDict(extra="forbid")

    join_type: JoinType
    connection_ref: str
    file_name: str
    alias: str
    conditions: list[JoinConditionItem]
    pre_filters: list[FilterItem] = Field(default_factory=list)
    comment: str | None = None


class Sources(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_table: RootTable
    joins: list[Join] = Field(default_factory=list)


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_ref: str
    file_name: str
    comment: str | None = None


class Mapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_column: str
    source_type: SourceType
    source_value: str
    cast_to: CastType
    is_nullable: bool
    default_value: Any | None = None


class ExpressionDerivation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable_name: str
    transform_type: Literal["EXPRESSION"]
    expression: str
    comment: str | None = None


class RegexpReplaceDerivation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable_name: str
    transform_type: Literal["REGEXP_REPLACE"]
    source: str
    pattern: str
    replacement: str
    comment: str | None = None


class CaseBranch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    when: JoinConditionItem
    then: Any


class CaseDerivation(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    variable_name: str
    transform_type: Literal["CASE"]
    branches: list[CaseBranch]
    else_value: Any | None = Field(default=None, alias="else")
    comment: str | None = None


Derivation = Annotated[
    Union[ExpressionDerivation, RegexpReplaceDerivation, CaseDerivation],
    Field(discriminator="transform_type"),
]


class Blueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence_order: int = Field(ge=1)
    blueprint_id: str
    sources: Sources
    target: Target
    pre_filters: list[FilterItem] = Field(default_factory=list)
    derivations: list[Derivation] = Field(default_factory=list)
    mappings: list[Mapping]
    post_filters: list[FilterItem] = Field(default_factory=list)
    comment: str | None = None


class PipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_uri: str | None = Field(default=None, alias="$schema")
    migration_id: str
    client_id: str
    version: str
    connections: dict[str, Connection]
    blueprints: list[Blueprint]


ConditionGroup.model_rebuild()
Blueprint.model_rebuild()
