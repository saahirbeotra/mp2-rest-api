# MP2 - Data Processing API

For MP2, I built a REST API using FastAPI that lets users upload CSV files, process the data, and retrieve the results. I reused my MP1 code to validate columns, remove duplicates, handle missing values, and remove outliers. I also added request logging and wrote three tests using pytest to make sure the API works.

## How to Run

First Start the API:


python -m uvicorn main:app


Then go to http://127.0.0.1:8000/docs to test the endpoints

## Tests

Run:


python -m pytest tests -v


All three required tests passed