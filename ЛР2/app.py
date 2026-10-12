from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Semaphore
from time import perf_counter, sleep


slots = Semaphore(2)
lock = Lock()
buckets = (0.01, 0.02, 0.025, 0.03, 0.04, 0.05, 0.1, 0.25, 0.4, 0.45, 0.5, 0.55, 0.6, 0.75, 1.0, 2.5, 5.0)
metrics = {
    "requests": {200: 0, 503: 0},
    "buckets": [0] * len(buckets),
    "sum": 0.0,
    "count": 0,
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_metrics()
            return

        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return

        start = perf_counter()
        acquired = slots.acquire(timeout=0.5)
        if acquired:
            try:
                sleep(0.02)
                status = 200
                body = b"OK"
            finally:
                slots.release()
        else:
            status = 503
            body = b"Busy"

        duration = perf_counter() - start
        with lock:
            metrics["requests"][status] += 1
            metrics["count"] += 1
            metrics["sum"] += duration
            for index, boundary in enumerate(buckets):
                if duration <= boundary:
                    metrics["buckets"][index] += 1

        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_metrics(self):
        with lock:
            counts = metrics["requests"].copy()
            bucket_counts = metrics["buckets"].copy()
            duration_sum = metrics["sum"]
            duration_count = metrics["count"]

        lines = [
            "# HELP http_requests_total Total HTTP requests",
            "# TYPE http_requests_total counter",
            f'http_requests_total{{method="GET",endpoint="/",status="200"}} {counts[200]}',
            f'http_requests_total{{method="GET",endpoint="/",status="503"}} {counts[503]}',
            "# HELP http_errors_total Total HTTP 5xx responses",
            "# TYPE http_errors_total counter",
            f'http_errors_total{{endpoint="/"}} {counts[503]}',
            "# HELP http_request_duration_seconds HTTP request duration",
            "# TYPE http_request_duration_seconds histogram",
        ]
        for boundary, count in zip(buckets, bucket_counts):
            lines.append(f'http_request_duration_seconds_bucket{{endpoint="/",le="{boundary}"}} {count}')
        lines.extend([
            f'http_request_duration_seconds_bucket{{endpoint="/",le="+Inf"}} {duration_count}',
            f'http_request_duration_seconds_sum{{endpoint="/"}} {duration_sum:.9f}',
            f'http_request_duration_seconds_count{{endpoint="/"}} {duration_count}',
        ])
        body = ("\n".join(lines) + "\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


ThreadingHTTPServer(("0.0.0.0", 5000), Handler).serve_forever()
