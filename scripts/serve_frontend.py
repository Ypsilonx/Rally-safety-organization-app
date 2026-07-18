"""Serve Rally frontend as web root and expose project data files.

This local development server maps:
- / -> frontend/index.html
- /<asset> -> frontend/<asset>
- /data/* -> data/*

It keeps the common app URL at http://127.0.0.1:8080 while preserving
access to runtime map payloads stored in the repository data directory.
"""

from __future__ import annotations

import argparse
import posixpath
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
DATA_ROOT = PROJECT_ROOT / "data"


class RallyFrontendHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves frontend assets and data payloads.

    The handler intentionally avoids exposing arbitrary files from repository
    root. Only `frontend/` and `data/` trees are reachable.
    """

    def translate_path(self, path: str) -> str:
        """Map URL path to local filesystem path.

        Args:
            path: Request path from the HTTP client.

        Returns:
            Absolute filesystem path for the requested resource.
        """
        url_path = self._normalized_url_path(path)
        local_path = self._resolve_local_path(url_path)
        return str(local_path)

    def send_head(self):
        """Serve directory requests as index files when possible.

        Returns:
            A file object to stream to the client, or None on handled errors.
        """
        url_path = self._normalized_url_path(self.path)
        local_path = self._resolve_local_path(url_path)

        if local_path.is_dir():
            index_path = local_path / "index.html"
            if index_path.exists():
                self.path = f"{url_path.rstrip('/')}/index.html"
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "File not found")
                return None

        return super().send_head()

    def _normalized_url_path(self, path: str) -> str:
        """Normalize requested URL path to a clean POSIX-style path.

        Args:
            path: Raw request path.

        Returns:
            Normalized path starting with a slash.
        """
        raw_path = urlsplit(path).path or "/"
        decoded = unquote(raw_path)
        normalized = posixpath.normpath(decoded)
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized

    def _resolve_local_path(self, url_path: str) -> Path:
        """Resolve a safe local path for the normalized URL path.

        Args:
            url_path: Normalized path beginning with `/`.

        Returns:
            Path inside frontend or data directory.
        """
        if url_path == "/":
            return FRONTEND_ROOT / "index.html"

        if url_path.startswith("/data/"):
            relative = url_path.removeprefix("/data/").strip("/")
            return self._safe_join(DATA_ROOT, relative)

        relative = url_path.lstrip("/")
        return self._safe_join(FRONTEND_ROOT, relative)

    def _safe_join(self, root: Path, relative: str) -> Path:
        """Join and validate path to prevent traversal outside allowed roots.

        Args:
            root: Allowed filesystem root.
            relative: Relative URL-derived path segment.

        Returns:
            Resolved safe filesystem path.
        """
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root.resolve()):
            return root / "__forbidden__"
        return candidate


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Serve frontend at '/' with project data available at '/data/*'.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host, default 127.0.0.1")
    parser.add_argument("--port", default=8080, type=int, help="Bind port, default 8080")
    return parser.parse_args()


def main() -> None:
    """Start local HTTP server for frontend development."""
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), RallyFrontendHandler)
    print(f"Serving HTTP on {args.host} port {args.port} (Rally frontend)")
    print(f"App URL: http://{args.host}:{args.port}/")
    print(f"Data URL base: http://{args.host}:{args.port}/data/")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down frontend server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
