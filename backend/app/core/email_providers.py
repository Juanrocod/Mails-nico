from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    message_id_domain: str


PROVIDERS: dict[str, ProviderConfig] = {
    "yahoo": ProviderConfig(
        smtp_host="smtp.mail.yahoo.com",
        smtp_port=587,
        imap_host="imap.mail.yahoo.com",
        imap_port=993,
        message_id_domain="yahoo.com",
    ),
    "gmail": ProviderConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        imap_host="imap.gmail.com",
        imap_port=993,
        message_id_domain="gmail.com",
    ),
}

DEFAULT_PROVIDER = "yahoo"
