def test_health_returns_200_with_expected_version(client):
    resp = client.get("/api/v1/health")

    assert resp.status_code == 200
    assert resp.get_json()["version"] == "1.6.0"
