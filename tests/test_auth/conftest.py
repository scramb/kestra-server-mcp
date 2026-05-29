"""Auth-specific test fixtures."""

import pytest


@pytest.fixture
def mock_entra_token_response():
    """Mock MSAL token acquisition response."""
    return {
        "access_token": "test-access-token-value",
        "refresh_token": "test-refresh-token-value",
        "id_token": "test-id-token-value",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


@pytest.fixture
def mock_entra_error_response():
    """Mock MSAL error response."""
    return {
        "error": "invalid_grant",
        "error_description": "AADSTS70000: The request is not properly formed.",
    }
