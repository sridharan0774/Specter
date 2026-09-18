def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "version" in data
    assert data["api_v1_url"] == "/api/v1"


def test_health_check_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["online", "degraded"]
    assert data["database"] == "healthy"
    assert "providers_configured" in data


def test_create_and_get_case(client):
    payload = {
        "investigator_id": "OFFICER_123",
        "reported_wallet": "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
        "chain": "TRON",
        "asset": "USDT",
        "description": "Reported fraud case"
    }
    # Create Case
    response = client.post("/api/v1/cases", json=payload)
    assert response.status_code == 201
    case_data = response.json()
    assert case_data["case_id"] is not None
    assert case_data["investigator_id"] == "OFFICER_123"
    assert case_data["reported_wallet"] == "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
    assert case_data["chain"] == "TRON"
    assert case_data["status"] == "ACTIVE"

    case_id = case_data["case_id"]

    # Get Case Details
    get_res = client.get(f"/api/v1/cases/{case_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["case_id"] == case_id
    assert detail["transaction_count"] == 0
    assert detail["evidence_count"] == 0

    # List Cases
    list_res = client.get("/api/v1/cases")
    assert list_res.status_code == 200
    cases_list = list_res.json()
    assert len(cases_list) >= 1

    # Update Case
    patch_res = client.patch(f"/api/v1/cases/{case_id}", json={"status": "CLOSED", "description": "Investigation finalized"})
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["status"] == "CLOSED"
    assert updated_data["description"] == "Investigation finalized"
