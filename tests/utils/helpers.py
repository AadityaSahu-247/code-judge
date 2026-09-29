"""Small shared helpers for API tests."""


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_json(response, status_code: int) -> dict:
    assert response.status_code == status_code, (
        f"expected {status_code}, got {response.status_code}: {response.text}"
    )
    return response.json()
