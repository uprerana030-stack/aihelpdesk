"""Outbound TLS configuration for backend -> external API calls (e.g. Gemini).

Corporate networks that intercept TLS (Zscaler/Netskope-style proxies) cause

    CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate

because Python does not trust the proxy's substituted root CA. Two env-driven
remedies (see app/core/config.py and .env):

    CA_BUNDLE=C:\\path\\corp-root.pem   RECOMMENDED. Trust the corporate root CA
                                        across every HTTPS stack. Stays secure.

    DISABLE_SSL_VERIFY=true             INSECURE. Skip certificate verification
                                        entirely. Dev/demo only.

`apply_tls_settings()` is idempotent and must run before the first outbound
HTTPS request (it is called at backend import time in app/main.py).
"""
from __future__ import annotations

import logging
import os
import ssl

from app.core.config import get_settings

logger = logging.getLogger("helpdesk.tls")

_applied = False


def apply_tls_settings() -> None:
    """Apply CA-bundle or verification-disable settings, once per process."""
    global _applied
    if _applied:
        return
    _applied = True

    settings = get_settings()

    # Preferred, secure path: point every common HTTPS stack at the CA bundle.
    if settings.ca_bundle:
        for var in (
            "SSL_CERT_FILE",
            "REQUESTS_CA_BUNDLE",
            "CURL_CA_BUNDLE",
            "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH",
        ):
            os.environ.setdefault(var, settings.ca_bundle)
        logger.info("TLS: trusting CA bundle at %s", settings.ca_bundle)
        return

    if not settings.disable_ssl_verify:
        return

    logger.warning(
        "TLS: certificate verification DISABLED (insecure — dev/demo only). "
        "Prefer CA_BUNDLE with your corporate root CA for a secure fix."
    )

    # 1) stdlib ssl / urllib / httplib2
    try:
        ssl._create_default_https_context = ssl._create_unverified_context  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    os.environ["PYTHONHTTPSVERIFY"] = "0"

    # 2) requests / urllib3 (used by the Gemini REST transport). Force
    #    verify=False on every request and silence the resulting warnings.
    try:
        import urllib3

        urllib3.disable_warnings()
    except Exception:  # noqa: BLE001
        pass
    try:
        import requests

        _orig_request = requests.Session.request

        def _no_verify_request(self, *args, **kwargs):
            kwargs["verify"] = False
            return _orig_request(self, *args, **kwargs)

        requests.Session.request = _no_verify_request  # type: ignore[assignment]
    except Exception:  # noqa: BLE001
        pass

# Note: the Gemini SDK (google-genai) is built on httpx and does not honor the
# requests patch or the stdlib ssl hook above; its TLS-verify setting is applied
# per-client via HttpOptions in app/core/gemini.py.
