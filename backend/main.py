import io
from typing import Dict, List
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

app = FastAPI(title="Archivium API")

ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}

MAX_UPLOAD_BYTES = 50 * 1024 * 1024

datasets: Dict[str, "DatasetMetadata"] = {}


class HealthResponse(BaseModel):
    status: str


class DatasetMetadata(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    column_names: List[str]


@app.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/datasets/upload", response_model=DatasetMetadata)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetMetadata:
    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {file.content_type}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds 50 MB limit",
        )

    try:
        frame = pd.read_csv(io.BytesIO(content))
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="File is not readable as text/CSV"
        )
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="File contains no CSV data")
    except pd.errors.ParserError as exc:
        raise HTTPException(status_code=400, detail=f"Malformed CSV: {exc}")

    dataset_id = str(uuid4())

    metadata = DatasetMetadata(
        dataset_id=dataset_id,
        filename=filename,
        rows=int(len(frame.index)),
        columns=int(len(frame.columns)),
        column_names=[str(column) for column in frame.columns],
    )

    datasets[dataset_id] = metadata

    return metadata