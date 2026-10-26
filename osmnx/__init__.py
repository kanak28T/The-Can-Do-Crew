"""Lightweight stub of the osmnx package for testing purposes.
Provides only the minimal API required by the project's tests.
"""

class _Settings:
    def __init__(self):
        self.overpass_url: str = ""
        self.requests_timeout: int = 0
        # Additional attributes can be added as needed.

# expose a singleton settings object similar to real osmnx
settings = _Settings()
