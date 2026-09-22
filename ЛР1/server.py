from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Semaphore
from time import sleep


slots = Semaphore(2)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with slots:
            sleep(0.02)
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
