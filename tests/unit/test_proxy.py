"""
Tests for proxy mode: configurable base_url and StaticBearerAuth.
"""

import json
from datetime import datetime, timedelta

import pytest
import responses

from schwabpy import (
    SchwabClient,
    StaticBearerAuth,
    AuthenticationError,
    APIError,
    ProxyAuthenticationError,
    ServerError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from schwabpy.auth import AuthProvider, OAuthManager

PROXY = "https://broker.example/api/public/v1/schwab"
API_KEY = "stb_test_key_123"
DECOY_TOKEN = "DECOY_ACCESS_TOKEN"


@pytest.fixture
def decoy_cwd(tmp_path, monkeypatch):
    """Run in a temp cwd holding a decoy default token file."""
    token_file = tmp_path / ".schwab_tokens.json"
    token_file.write_text(json.dumps({
        "access_token": DECOY_TOKEN,
        "refresh_token": "DECOY_REFRESH_TOKEN",
        "token_expiry": (datetime.now() + timedelta(hours=1)).isoformat(),
        "refresh_token_expiry": (datetime.now() + timedelta(days=6)).isoformat(),
    }))
    monkeypatch.chdir(tmp_path)
    return token_file


@pytest.fixture
def proxy_client():
    client = SchwabClient(base_url=PROXY, auth=StaticBearerAuth(API_KEY))
    yield client
    client.close()


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr("schwabpy.client.time.sleep", lambda _s: None)


class TestStaticBearerAuth:
    def test_get_headers_returns_bearer_key(self):
        assert StaticBearerAuth(API_KEY).get_headers() == {"Authorization": f"Bearer {API_KEY}"}

    @pytest.mark.parametrize("bad", ["", "   ", None])
    def test_init_empty_key_raises(self, bad):
        with pytest.raises(ValueError):
            StaticBearerAuth(bad)

    def test_satisfies_auth_provider_protocol(self):
        assert isinstance(StaticBearerAuth(API_KEY), AuthProvider)

    def test_repr_redacts_key(self):
        assert API_KEY not in repr(StaticBearerAuth(API_KEY))


class TestProxyClientConstruction:
    def test_init_static_auth_needs_no_app_credentials(self, decoy_cwd):
        client = SchwabClient(base_url=PROXY, auth=StaticBearerAuth(API_KEY))
        assert client.base_url == PROXY
        assert client.client_id is None
        assert not isinstance(client.auth, OAuthManager)

    def test_init_static_auth_never_builds_oauth_manager(self, decoy_cwd, monkeypatch):
        def boom(*_a, **_k):
            raise AssertionError("OAuthManager must not be built in static auth mode")

        monkeypatch.setattr("schwabpy.client.OAuthManager", boom)
        SchwabClient(base_url=PROXY, auth=StaticBearerAuth(API_KEY))

    def test_init_trailing_slash_stripped(self):
        client = SchwabClient(base_url=PROXY + "/", auth=StaticBearerAuth(API_KEY))
        assert client.base_url == PROXY

    def test_init_without_auth_or_credentials_raises(self):
        with pytest.raises(ValueError):
            SchwabClient()

    def test_authenticate_with_static_auth_raises(self, proxy_client):
        with pytest.raises(AuthenticationError):
            proxy_client.authenticate()
        with pytest.raises(AuthenticationError):
            proxy_client.authorize_from_code("abc")

    def test_repr_does_not_leak_key(self, proxy_client):
        text = repr(proxy_client)
        assert API_KEY not in text
        assert "StaticBearerAuth" in text


class TestProxyRequests:
    @responses.activate
    def test_trader_call_uses_base_url_and_bearer_key(self, decoy_cwd, proxy_client):
        responses.get(f"{PROXY}/trader/v1/accounts/accountNumbers", json=[{"accountNumber": "1", "hashValue": "H"}])

        result = proxy_client.accounts.get_account_numbers()

        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.url == f"{PROXY}/trader/v1/accounts/accountNumbers"
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
        assert result

    @responses.activate
    def test_marketdata_call_uses_base_url(self, decoy_cwd, proxy_client):
        responses.get(f"{PROXY}/marketdata/v1/quotes", json={"AAPL": {"symbol": "AAPL", "quote": {}}})

        proxy_client.get("/marketdata/v1/quotes", params={"symbols": "AAPL"})

        request = responses.calls[0].request
        assert request.url.startswith(f"{PROXY}/marketdata/v1/quotes?")
        assert "symbols=AAPL" in request.url
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"

    @responses.activate
    def test_post_sends_json_content_type_through_proxy(self, proxy_client):
        responses.post(f"{PROXY}/trader/v1/accounts/HASH/orders", status=201)

        proxy_client.post("/trader/v1/accounts/HASH/orders", json={"orderType": "MARKET"})

        request = responses.calls[0].request
        assert request.headers["Content-Type"] == "application/json"
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"

    @responses.activate
    def test_token_file_untouched(self, decoy_cwd, proxy_client):
        before_listing = sorted(p.name for p in decoy_cwd.parent.iterdir())
        before_bytes = decoy_cwd.read_bytes()
        before_mtime = decoy_cwd.stat().st_mtime_ns
        responses.get(f"{PROXY}/trader/v1/accounts", json=[])

        proxy_client.get("/trader/v1/accounts")

        sent = responses.calls[0].request.headers["Authorization"]
        assert DECOY_TOKEN not in sent
        assert decoy_cwd.read_bytes() == before_bytes
        assert decoy_cwd.stat().st_mtime_ns == before_mtime
        assert sorted(p.name for p in decoy_cwd.parent.iterdir()) == before_listing

    @responses.activate
    def test_schwab_host_never_called(self, proxy_client):
        responses.get(f"{PROXY}/trader/v1/userPreference", json={})

        proxy_client.accounts.get_user_preference()

        assert all("api.schwabapi.com" not in c.request.url for c in responses.calls)


class TestProxyErrors:
    @responses.activate
    def test_401_raises_proxy_authentication_error(self, proxy_client):
        responses.get(
            f"{PROXY}/trader/v1/accounts",
            status=401,
            json={"error": "invalid_api_key", "detail": "Unknown or revoked API key."},
        )

        with pytest.raises(ProxyAuthenticationError) as exc_info:
            proxy_client.get("/trader/v1/accounts")

        err = exc_info.value
        assert isinstance(err, AuthenticationError)
        assert isinstance(err, APIError)
        assert err.status_code == 401
        assert err.error == "invalid_api_key"
        assert "revoked" in str(err)
        assert len(responses.calls) == 1

    @responses.activate
    def test_403_raises_proxy_authentication_error(self, proxy_client):
        responses.get(
            f"{PROXY}/trader/v1/accounts/HASH",
            status=403,
            json={"error": "account_not_allowed", "detail": "This key may not use that account."},
            headers={"X-Broker-Error": "account_not_allowed"},
        )

        with pytest.raises(ProxyAuthenticationError) as exc_info:
            proxy_client.get("/trader/v1/accounts/HASH")

        assert exc_info.value.status_code == 403
        assert exc_info.value.error == "account_not_allowed"

    @responses.activate
    def test_401_non_json_body_still_maps(self, proxy_client):
        responses.get(f"{PROXY}/trader/v1/accounts", status=401, body="nope")

        with pytest.raises(ProxyAuthenticationError) as exc_info:
            proxy_client.get("/trader/v1/accounts")

        assert exc_info.value.body is None

    @responses.activate
    def test_503_token_unavailable_raises_with_body_and_no_retry(self, proxy_client, no_sleep):
        body = {
            "error": "token_unavailable",
            "detail": "The Schwab sign-in expired. Someone needs to sign in again.",
            "state": "expired",
            "refresh_deadline": "2026-10-09T20:16:56Z",
            "admin_url": "https://broker.example/",
            "sign_in_url": "https://broker.example/",
        }
        responses.get(
            f"{PROXY}/marketdata/v1/quotes",
            status=503,
            json=body,
            headers={"Retry-After": "60", "X-Broker-Error": "token_unavailable"},
        )

        with pytest.raises(ServiceUnavailableError) as exc_info:
            proxy_client.get("/marketdata/v1/quotes", params={"symbols": "AAPL"})

        err = exc_info.value
        assert isinstance(err, ServerError)
        assert err.status_code == 503
        assert err.body == body
        assert err.state == "expired"
        assert err.sign_in_url == "https://broker.example/"
        assert err.retry_after == "60"
        assert len(responses.calls) == 1

    @responses.activate
    def test_503_other_still_retried(self, proxy_client, no_sleep):
        responses.get(f"{PROXY}/trader/v1/accounts", status=503, body="busy")

        with pytest.raises(ServiceUnavailableError) as exc_info:
            proxy_client.get("/trader/v1/accounts")

        assert exc_info.value.body is None
        assert len(responses.calls) == 4


class TestDefaultModeUnchanged:
    @responses.activate
    def test_default_client_uses_schwab_host_and_file_token(self, decoy_cwd):
        responses.get("https://api.schwabapi.com/trader/v1/accounts", json=[])

        client = SchwabClient(client_id="app_key", client_secret="app_secret")
        client.get("/trader/v1/accounts")

        assert isinstance(client.auth, OAuthManager)
        assert client.base_url == "https://api.schwabapi.com"
        request = responses.calls[0].request
        assert request.url == "https://api.schwabapi.com/trader/v1/accounts"
        assert request.headers["Authorization"] == f"Bearer {DECOY_TOKEN}"

    @responses.activate
    def test_default_client_401_is_unauthorized_error(self, decoy_cwd):
        responses.get("https://api.schwabapi.com/trader/v1/accounts", status=401, json={"message": "bad token"})
        client = SchwabClient(client_id="app_key", client_secret="app_secret")

        with pytest.raises(UnauthorizedError) as exc_info:
            client.get("/trader/v1/accounts")

        assert not isinstance(exc_info.value, ProxyAuthenticationError)

    @responses.activate
    def test_default_client_accepts_base_url_override_with_oauth(self, decoy_cwd):
        responses.get(f"{PROXY}/trader/v1/accounts", json=[])
        client = SchwabClient(client_id="app_key", client_secret="app_secret", base_url=PROXY)

        client.get("/trader/v1/accounts")

        assert responses.calls[0].request.headers["Authorization"] == f"Bearer {DECOY_TOKEN}"

    @responses.activate
    def test_replaced_auth_with_only_get_access_token_still_works(self, decoy_cwd):
        """Callers that swap client.auth for an object with only get_access_token keep working."""

        class LegacyAuth:
            def get_access_token(self):
                return "LEGACY_TOKEN"

        responses.get("https://api.schwabapi.com/trader/v1/accounts", status=401, json={"message": "x"})
        responses.get("https://api.schwabapi.com/trader/v1/orders", json=[])
        client = SchwabClient(client_id="app_key", client_secret="app_secret")
        client.auth = LegacyAuth()

        client.get("/trader/v1/orders")
        with pytest.raises(UnauthorizedError):
            client.get("/trader/v1/accounts")

        assert responses.calls[0].request.headers["Authorization"] == "Bearer LEGACY_TOKEN"
