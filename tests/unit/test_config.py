"""P1-1: settings read from the environment (F14 settings hook)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    # Ignore any developer .env so defaults and env overrides are what we assert.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_offline_defaults():
    s = Settings()
    assert s.demo_mode is True
    assert s.llm_provider == "fake"
    assert s.vector_store == "memory"
    assert s.approval_required_for_refunds is True
    assert s.max_refund_without_approval == 0
    assert s.rate_limit_per_minute == 120
    assert s.qdrant_collection == "clouddesk_knowledge"


def test_reads_demo_mode_and_llm_provider_from_env(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    s = Settings()
    assert s.demo_mode is False
    assert s.llm_provider == "anthropic"


def test_get_settings_is_cached():
    assert get_settings() is get_settings()


def test_effective_jwt_secret_prefers_supabase(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "local")
    assert Settings().effective_jwt_secret == "local"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "supabase")
    assert Settings().effective_jwt_secret == "supabase"


def test_empty_supabase_secret_falls_back(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "local")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    assert Settings().effective_jwt_secret == "local"


def test_secrets_are_masked_in_repr(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-super-secret")
    assert "sk-super-secret" not in repr(Settings())


def test_cors_origin_list(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test,")
    assert Settings().cors_origin_list == ["http://a.test", "http://b.test"]


def test_empty_redis_url_means_fakeredis(monkeypatch):
    assert Settings().use_fakeredis is True
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    assert Settings().use_fakeredis is False


def test_rejects_unknown_vector_store(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE", "pinecone")
    with pytest.raises(ValidationError):
        Settings()


def test_rejects_negative_refund_ceiling(monkeypatch):
    monkeypatch.setenv("MAX_REFUND_WITHOUT_APPROVAL", "-1")
    with pytest.raises(ValidationError):
        Settings()
