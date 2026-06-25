"""API type aliases for OpenAPI / Swagger compatibility."""

from __future__ import annotations

from typing import Annotated

from fastapi import UploadFile as FastAPIUploadFile
from pydantic import WithJsonSchema

# Swagger UI renders file pickers for format=binary but shows text inputs for
# OpenAPI 3.1 contentMediaType (FastAPI >=0.129). See fastapi#14975 / swagger-ui#10825.
BinaryUploadFile = Annotated[
    FastAPIUploadFile,
    WithJsonSchema({"type": "string", "format": "binary"}),
]
