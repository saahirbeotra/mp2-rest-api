
def test_upload_csv(client, sample_csv_bytes):
    """Test uploading a CSV file."""

    response = client.post(
        "/upload",
        files={
            "file": (
                "sample_data.csv",
                sample_csv_bytes,
                "text/csv"
            )
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["rows"] == 6
    assert data["columns"] == 2
    assert isinstance(data["id"], int)
    assert data["id"] > 0


def test_process_and_retrieve(
    client, uploaded_dataset_id, processing_body
):
    """Test processing and retrieving a dataset."""

    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json=processing_body
    )

    assert response.status_code == 200

    report = response.json()

    assert report["validation_rows_removed"] == 1
    assert report["cleaning_report"]["rows_before"] == 5
    assert report["cleaning_report"]["rows_after"] == 3

    response = client.get(
        f"/datasets/{uploaded_dataset_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 3

    records = data["data"]

    actual = {
        int(row["student_id"]): int(row["score"])
        for row in records
    }

    assert actual == {
        1: 80,
        2: 90,
        5: 85
    }


def test_retrieve_missing_dataset(client):
    """Test retrieving a dataset that does not exist."""

    response = client.get("/datasets/999")

    assert response.status_code == 404
