#!/usr/bin/env python3
"""Expose Windows-loopback PAOS only on an explicit WSL adapter address.

The PAOS HTTP server keeps binding to 127.0.0.1. This adapter forwards an
explicit listen address (normally the Windows WSL virtual-adapter IPv4) to the
loopback service without changing PAOS routes or widening the server bind.
"""

from __future__ import annotations

import argparse
import ipaddress
import select
import socket
import socketserver


def validate_listen_host(value: str) -> str:
    """Require one explicit IP address and reject wildcard exposure."""
    try:
        address = ipaddress.ip_address(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("listen host must be an IP address") from error
    if address.is_unspecified:
        raise argparse.ArgumentTypeError("wildcard listen addresses are forbidden")
    if address.version != 4:
        raise argparse.ArgumentTypeError("PAOS WSL bridge currently requires IPv4")
    return str(address)


class PaosBridgeHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        with socket.create_connection(
            (self.server.target_host, self.server.target_port), timeout=5
        ) as upstream:
            sockets = (self.request, upstream)
            while True:
                readable, _, _ = select.select(sockets, (), (), 30)
                if not readable:
                    continue
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    destination = upstream if source is self.request else self.request
                    destination.sendall(data)


class PaosBridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        target_address: tuple[str, int],
    ) -> None:
        self.target_host, self.target_port = target_address
        super().__init__(server_address, PaosBridgeHandler)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Forward a Windows WSL-adapter endpoint to the Windows-loopback "
            "PAOS service."
        )
    )
    parser.add_argument("--listen-host", required=True, type=validate_listen_host)
    parser.add_argument("--listen-port", type=int, default=8766)
    parser.add_argument("--target-host", default="127.0.0.1")
    parser.add_argument("--target-port", type=int, default=8766)
    args = parser.parse_args()

    with PaosBridgeServer(
        (args.listen_host, args.listen_port),
        (args.target_host, args.target_port),
    ) as server:
        print(
            f"PAOS bridge {args.listen_host}:{args.listen_port} -> "
            f"{args.target_host}:{args.target_port}",
            flush=True,
        )
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
