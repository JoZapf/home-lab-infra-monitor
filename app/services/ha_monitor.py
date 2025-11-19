from app.config import get_settings

settings = get_settings()


def some_ha_call():
    if not settings.ha_base_url:
        raise RuntimeError("HA_BASE_URL is not configured")

    base_url = settings.ha_base_url
    token = settings.ha_token
    # ... HTTP call via httpx using base_url + token ...

