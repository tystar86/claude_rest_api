from django.conf import settings


def test_secure_proxy_ssl_header_uses_forwarded_proto() -> None:
    assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
