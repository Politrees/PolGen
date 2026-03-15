from __future__ import annotations

import argparse
import socket

import uvicorn

from desktop.backend.app import app


def pick_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def main():
    parser = argparse.ArgumentParser(description="PolGen local backend (FastAPI)")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="0 = auto")
    args = parser.parse_args()

    port = args.port if args.port != 0 else pick_free_port(args.host)

    # Tauri читает stdout и понимает, куда подключаться
    print(f"POLGEN_BACKEND_READY http://{args.host}:{port}", flush=True)

    uvicorn.run(
        app,
        host=args.host,
        port=port,
        log_level="warning",
        access_log=False,
        reload=False,
        workers=1,
    )


if __name__ == "__main__":
    main()