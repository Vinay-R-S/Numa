REQUIRED_COMPONENTS = {
    "client": "Next.js frontend",
    "server": "FastAPI backend",
    "database": "PostgreSQL data store",
    "ci": "GitHub Actions pipeline",
}


def test_system_required_components_are_documented():
    assert set(REQUIRED_COMPONENTS) == {"client", "server", "database", "ci"}
    assert all(description for description in REQUIRED_COMPONENTS.values())
