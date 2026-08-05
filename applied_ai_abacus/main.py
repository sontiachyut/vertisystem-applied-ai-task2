from __future__ import annotations

import argparse

import uvicorn

from .app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Applied AI abacus microservice.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional SQLAlchemy database URL override. Defaults to ABACUS_DATABASE_URL or the local PostgreSQL demo URL.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    app = create_app(database_url=args.database_url)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
