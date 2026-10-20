"""Loopback-only transport captures for integration tests; no external recipients."""

import http.server
import socketserver
import threading
from contextlib import contextmanager


class SMTPHandler(socketserver.StreamRequestHandler):
	def handle(self):
		self.wfile.write(b"220 localhost test SMTP\r\n")
		while line := self.rfile.readline():
			command = line.decode("ascii", errors="replace").strip().upper()
			if command.startswith(("EHLO", "HELO")):
				self.wfile.write(b"250-localhost\r\n250-8BITMIME\r\n250 SIZE 1048576\r\n")
			elif command.startswith("DATA"):
				self.wfile.write(b"354 End with dot\r\n")
				parts = []
				while (part := self.rfile.readline()) not in (b".\r\n", b"", b".\n"):
					parts.append(part[1:] if part.startswith(b"..") else part)
				self.server.messages.append(b"".join(parts))
				self.wfile.write(b"250 Message accepted\r\n")
			elif command.startswith("QUIT"):
				self.wfile.write(b"221 Bye\r\n")
				return
			else:
				self.wfile.write(b"250 OK\r\n")


class SMTPServer(socketserver.ThreadingTCPServer):
	allow_reuse_address = True
	daemon_threads = True


class WebhookHandler(http.server.BaseHTTPRequestHandler):
	def do_POST(self):
		body = self.rfile.read(int(self.headers["Content-Length"]))
		self.server.messages.append((body, self.headers.get("X-Ghost-Signature")))
		self.send_response(200)
		self.send_header("Content-Type", "application/json")
		self.end_headers()
		self.wfile.write(b'{"status":"ok"}')

	def log_message(self, *args):
		pass


@contextmanager
def smtp_capture():
	with SMTPServer(("127.0.0.1", 0), SMTPHandler) as server:
		server.messages = []
		thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
		thread.start()
		try:
			yield server
		finally:
			server.shutdown()
			thread.join(timeout=5)


@contextmanager
def webhook_capture():
	with http.server.ThreadingHTTPServer(("127.0.0.1", 0), WebhookHandler) as server:
		server.messages = []
		thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
		thread.start()
		try:
			yield server
		finally:
			server.shutdown()
			thread.join(timeout=5)
