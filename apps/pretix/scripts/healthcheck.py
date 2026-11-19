"""Check the internal pretix login page using the configured public HTTP host."""
import os
import sys
import urllib.request
from urllib.parse import urlsplit


def main() -> int:
    """Request the login page and return a Docker-healthcheck compatible status.

    Reads PRETIX_PRETIX_URL from the container environment and sends its Host
    header to the internal web endpoint. No application data is changed.
    Returns:
        Zero for HTTP 200, or one with a short diagnostic when the page is unavailable.
    """
    try:
        request = urllib.request.Request(
            "http://127.0.0.1:8345/control/login",
            headers={"Host": urlsplit(os.environ["PRETIX_PRETIX_URL"]).netloc},
        )
        with urllib.request.urlopen(request, timeout=4) as response:
            if response.status == 200:
                return 0
            print(f"Pretix login page returned HTTP {response.status}; expected HTTP 200.", file=sys.stderr)
    except (OSError, KeyError, ValueError) as error:
        print(f"Pretix login page is not ready: {error}. Check the pretix service log.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
