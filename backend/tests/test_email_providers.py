import pytest
from app.core.email_providers import PROVIDERS, DEFAULT_PROVIDER, ProviderConfig


def test_default_provider_is_yahoo():
    assert DEFAULT_PROVIDER == "yahoo"


def test_providers_has_yahoo_and_gmail():
    assert set(PROVIDERS.keys()) == {"yahoo", "gmail"}


def test_yahoo_provider_config_matches_current_hardcoded_values():
    yahoo = PROVIDERS["yahoo"]
    assert yahoo.smtp_host == "smtp.mail.yahoo.com"
    assert yahoo.smtp_port == 587
    assert yahoo.imap_host == "imap.mail.yahoo.com"
    assert yahoo.imap_port == 993
    assert yahoo.message_id_domain == "yahoo.com"


def test_gmail_provider_config():
    gmail = PROVIDERS["gmail"]
    assert gmail.smtp_host == "smtp.gmail.com"
    assert gmail.smtp_port == 587
    assert gmail.imap_host == "imap.gmail.com"
    assert gmail.imap_port == 993
    assert gmail.message_id_domain == "gmail.com"


def test_provider_config_is_frozen():
    yahoo = PROVIDERS["yahoo"]
    with pytest.raises(Exception):
        yahoo.smtp_host = "changed"
