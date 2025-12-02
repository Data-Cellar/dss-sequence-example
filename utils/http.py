from urllib.parse import urlparse
from config import AUTHORIZATION_HEADER, CONTENT_TYPE_HEADER, ACCEPT_HEADER, JSON_CONTENT_TYPE, SSE_CONTENT_TYPE


def build_headers(token: str, sse: bool = False, bearer: bool = True) -> dict:
    """
    Construct headers for API requests.

    Args:
        token (str): Access token or API key.
        sse (bool, optional): If True, sets Accept header to SSE content type. Defaults to False.
        bearer (bool, optional): If True, prepends "Bearer " to the token. Defaults to True.

    Returns:
        dict: Headers dictionary.
    """
    headers = {
        AUTHORIZATION_HEADER: f"Bearer {token}" if bearer else token
    }

    if sse:
        headers[ACCEPT_HEADER] = SSE_CONTENT_TYPE
    else:
        headers[CONTENT_TYPE_HEADER] = JSON_CONTENT_TYPE

    return headers


def _extract_hostname(host: str) -> str:
    """
    Extract the hostname from a URL or host string by removing the scheme, port, and path.

    If the input string does not contain a scheme (e.g., "http://"), a temporary
    scheme is prepended to allow `urlparse` to correctly extract the hostname.
    If `urlparse` cannot determine the hostname, the function falls back to
    splitting the input at the colon and taking the first part.

    Args:
        host (str): The input URL or host string. Can include scheme, port, or path.

    Returns:
        str: The extracted hostname.

    Examples:
        >>> _extract_hostname("https://example.com:8080/path")
        'example.com'
        >>> _extract_hostname("example.com:5000")
        'example.com'
        >>> _extract_hostname("localhost")
        'localhost'
    """

    if "://" not in host:
        host_for_parse = f"//{host}"
    else:
        host_for_parse = host

    parsed = urlparse(host_for_parse)

    if parsed.hostname:
        return parsed.hostname

    # Fallback: extract hostname from netloc by removing port
    netloc = parsed.netloc or host
    # Remove userinfo if present (user:pass@host)
    if "@" in netloc:
        netloc = netloc.split("@", 1)[1]
    # Remove port if present
    if ":" in netloc:
        netloc = netloc.split(":", 1)[0]

    return netloc
