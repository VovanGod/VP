import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


root = Path(__file__).parent
results = root / "results"
results.mkdir(exist_ok=True)
names = ("up", "rps", "success_rps", "errors_rps", "errors_percent", "p95_ms", "p99_ms", "cpu_percent", "memory_mb")
queries = dict(zip(names, (root / "queries.promql").read_text().splitlines()))


def query(expression):
    url = "http://127.0.0.1:9090/api/v1/query?" + urlencode({"query": expression})
    with urlopen(url, timeout=5) as response:
        data = json.load(response)
    values = data["data"]["result"]
    return float(values[0]["value"][1]) if values else None


records = []
for vus in (10, 50, 200):
    print(f"Начат тест: {vus} VU", flush=True)
    summary = results / f"k6_{vus}.json"
    log = results / f"k6_{vus}.txt"
    environment = os.environ.copy()
    environment.update(VUS=str(vus), DURATION="90s", K6_NO_USAGE_REPORT="true")
    command = ["k6", "run", "--quiet", "--no-color", "--summary-mode", "full", "--summary-export", str(summary), str(root / "test-load.js")]
    snapshots = []
    with log.open("w") as output:
        process = subprocess.Popen(command, env=environment, stdout=output, stderr=subprocess.STDOUT)
        started = time.monotonic()
        for second in (45, 60, 75, 82):
            while process.poll() is None and time.monotonic() - started < second:
                time.sleep(0.5)
            if process.poll() is not None:
                break
            values = {name: query(expression) for name, expression in queries.items()}
            snapshots.append({"elapsed_seconds": second, **values})
            print(f"  Сняты метрики на {second}-й секунде", flush=True)
        code = process.wait()
    if code != 0:
        raise RuntimeError(f"k6 завершился с кодом {code}: {log}")
    records.append({"vus": vus, "summary": str(summary.relative_to(root)), "log": str(log.relative_to(root)), "snapshots": snapshots})
    (results / "measurements.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    print(f"Завершён тест: {vus} VU", flush=True)
