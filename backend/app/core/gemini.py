"""Shared Google Gemini client (the current `google-genai` SDK).

Centralizes client construction so the outbound-TLS policy is applied in one
place. `google-genai` is built on httpx, so disabling certificate verification
(needed behind a corporate TLS proxy — see app/core/tls.py) is expressed via
`HttpOptions.client_args={"verify": False}` rather than by patching `requests`.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger("helpdesk.gemini")


@lru_cache(maxsize=1)
def get_client():
    """Return a configured genai.Client, or None when no API key is set."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    from google import genai
    from google.genai import types

    # google-genai is built on httpx. Its `client_args` are NOT reliably applied
    # to TLS, so to control certificate verification we hand it explicit httpx
    # clients built with the desired `verify`:
    #   * default (Codespace / normal networks) -> verify=True  (secure)
    #   * CA_BUNDLE set                          -> verify=<ca.pem> (secure)
    #   * DISABLE_SSL_VERIFY=true                -> verify=False (insecure)
    verify: object = True
    if settings.disable_ssl_verify:
        verify = False
        logger.warning("Gemini client: TLS verification DISABLED (insecure — dev/demo only).")
    elif settings.ca_bundle:
        verify = settings.ca_bundle
        logger.info("Gemini client: verifying TLS against CA bundle %s", settings.ca_bundle)

    http_options = None
    if verify is not True:
        import httpx

        http_options = types.HttpOptions(
            httpx_client=httpx.Client(verify=verify),
            httpx_async_client=httpx.AsyncClient(verify=verify),
        )
    return genai.Client(api_key=settings.gemini_api_key, http_options=http_options)
