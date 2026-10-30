
import io
import json
import logging
from pathlib import Path

from data_pipeline.data_validator import validate_dataframe
from data_pipeline.data_processor import process_data, create_cleaning_report

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile


from src import (
    DatasetInfo,
    DatasetStorage,
    HealthResponse,
    ProcessConfig,
    ProcessingReport,
    setup_logging,
    log_requests,
)

setup_logging(verbose=True)
logger = logging.getLogger(__name__)


app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)

storage = DatasetStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""

    extension = Path(file.filename or "").suffix.lower()

    if extension != ".csv":
        logger.warning("Unsupported file format: %s", extension)
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )

    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError
    ) as error:
        logger.warning("Invalid CSV upload: %s", error)
        raise HTTPException(
            status_code=400,
            detail="Unable to read CSV file"
        ) from error

    dataset_id = storage.save(df, file.filename)

    logger.info(
        "Uploaded dataset: id=%s, filename=%s, rows=%s",
        dataset_id,
        file.filename,
        len(df)
    )

    return storage.get_metadata(dataset_id)


@app.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: int,
    limit: int = Query(default=100, ge=1)
):
    """Return up to limit rows from a stored dataset."""

    df = storage.get(dataset_id)

    if df is None:
        logger.warning("Dataset not found: %s", dataset_id)
        raise HTTPException(
            status_code=404,
            detail="Dataset not found"
        )

    records = json.loads(df.head(limit).to_json(orient="records"))

    logger.info(
        "Retrieved dataset: id=%s, returned_rows=%s",
        dataset_id,
        len(records)
    )

    return {
        "id": dataset_id,
        "data": records,
        "total_rows": len(df)
    }



@app.post("/datasets/{dataset_id}/process", response_model=ProcessingReport)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and clean a stored dataset."""

    df = storage.get(dataset_id)

    if df is None:
        logger.warning("Dataset not found: %s", dataset_id)
        raise HTTPException(
            status_code=404,
            detail="Dataset not found"
        )

    settings = config.model_dump()

    try:
        validated_df = validate_dataframe(
            df,
            required_columns=settings["validation"]["required_columns"],
            numeric_columns=settings["validation"]["numeric_columns"]
        )

        validation_rows_removed = len(df) - len(validated_df)

        processed_df = process_data(
            validated_df.copy(),
            settings
        )

        cleaning_report = create_cleaning_report(
            validated_df,
            processed_df
        )

    except ValueError as error:
        logger.warning("Processing failed: %s", error)
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    storage.update(dataset_id, processed_df)

    logger.info(
        "Processed dataset: id=%s, rows_before=%s, rows_after=%s",
        dataset_id,
        len(df),
        len(processed_df)
    )

    return ProcessingReport(
        id=dataset_id,
        validation_rows_removed=validation_rows_removed,
        cleaning_report=cleaning_report
    )

