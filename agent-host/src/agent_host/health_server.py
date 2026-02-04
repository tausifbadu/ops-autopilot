"""Minimal HTTP server for ECS health checks. Serves GET /health on port 8000."""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from agent_host.logging import get_logger

logger = get_logger(__name__)

HEALTH_PORT = 8000


class HealthHandler(BaseHTTPRequestHandler):
    """Respond to GET /health with 200 OK for ECS health checks."""

    def do_GET(self):
        if self.path == "/health" or self.path == "/health/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, msg_format, *args):
        logger.debug("health %s", args[0] if args else "")


def start_health_server(port: int = HEALTH_PORT) -> None:
    """Start the health check HTTP server in a daemon thread (for ECS)."""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health server listening on port %s (GET /health)", port)
