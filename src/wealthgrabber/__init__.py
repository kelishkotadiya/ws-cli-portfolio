"""wealthgrabber - Wealthsimple Account Viewer CLI."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("wealthgrabber")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
