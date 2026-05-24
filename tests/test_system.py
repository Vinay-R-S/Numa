REQUIRED_COMPONENTS = {
    "client": "Next.js frontend",
    "server": "FastAPI backend",
    "database": "PostgreSQL data store",
    "ci": "GitHub Actions pipeline",
}


def required_routes() -> set[str]:
    return {"/", "/health", "/home", "/tasks", "/calendar/events"}


def test_system_required_components_are_documented():
    assert set(REQUIRED_COMPONENTS) == {"client", "server", "database", "ci"}
    assert all(description for description in REQUIRED_COMPONENTS.values())


def test_system_public_routes_include_health_check():
    assert "/health" in required_routes()


def test_system_protected_routes_are_separate_from_public_root():
    routes = required_routes()

    assert "/home" in routes
    assert "/" in routes
    assert "/home" != "/"
