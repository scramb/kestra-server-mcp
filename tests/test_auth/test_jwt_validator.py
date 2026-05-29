"""Tests for JWT validation."""


from src.auth.jwt_validator import extract_claims, validate_token


class TestValidateToken:
    def test_valid_token_passes(
        self, valid_token, jwks_response, test_entra_config, httpx_mock
    ):
        httpx_mock.add_response(
            url=test_entra_config.jwks_uri,
            json=jwks_response,
        )
        claims = validate_token(valid_token, test_entra_config)
        assert claims is not None
        assert claims["sub"] == "test-user-001"

    def test_expired_token_fails(
        self, expired_token, jwks_response, test_entra_config, httpx_mock
    ):
        httpx_mock.add_response(
            url=test_entra_config.jwks_uri,
            json=jwks_response,
        )
        claims = validate_token(expired_token, test_entra_config)
        assert claims is None

    def test_wrong_issuer_fails(
        self, wrong_issuer_token, jwks_response, test_entra_config, httpx_mock
    ):
        httpx_mock.add_response(
            url=test_entra_config.jwks_uri,
            json=jwks_response,
        )
        claims = validate_token(wrong_issuer_token, test_entra_config)
        assert claims is None

    def test_wrong_audience_fails(
        self, wrong_audience_token, jwks_response, test_entra_config, httpx_mock
    ):
        httpx_mock.add_response(
            url=test_entra_config.jwks_uri,
            json=jwks_response,
        )
        claims = validate_token(wrong_audience_token, test_entra_config)
        assert claims is None

    def test_empty_token_returns_none(self, test_entra_config):
        assert validate_token("", test_entra_config) is None

    def test_none_token_returns_none(self, test_entra_config):
        assert validate_token(None, test_entra_config) is None

    def test_cache_is_used_for_valid_token(
        self, valid_token, jwks_response, test_entra_config, httpx_mock
    ):
        # First call fetches JWKS
        httpx_mock.add_response(
            url=test_entra_config.jwks_uri,
            json=jwks_response,
        )
        claims = validate_token(valid_token, test_entra_config)
        assert claims is not None

        # Second call uses cache — no additional HTTP request
        claims2 = validate_token(valid_token, test_entra_config)
        assert claims2 is not None


class TestExtractClaims:
    def test_valid_bearer_header(self, valid_token, jwks_response, test_entra_config, httpx_mock):
        httpx_mock.add_response(
            url=test_entra_config.jwks_uri,
            json=jwks_response,
        )
        claims = extract_claims(f"Bearer {valid_token}", test_entra_config)
        assert claims is not None
        assert claims["sub"] == "test-user-001"

    def test_none_header(self, test_entra_config):
        assert extract_claims(None, test_entra_config) is None

    def test_missing_bearer_prefix(self, valid_token, test_entra_config):
        assert extract_claims(valid_token, test_entra_config) is None

    def test_expired_token_in_header(
        self, expired_token, jwks_response, test_entra_config, httpx_mock
    ):
        httpx_mock.add_response(
            url=test_entra_config.jwks_uri,
            json=jwks_response,
        )
        claims = extract_claims(f"Bearer {expired_token}", test_entra_config)
        assert claims is None
