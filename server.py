from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path


PAGE = Path(__file__).with_name("index.html")


def schedule(processes, quantum):
    arrivals = [p["arrival"] for p in processes]
    bursts = [p["burst"] for p in processes]
    remaining = bursts.copy()
    completion = [0] * len(processes)
    queue, added, gantt = [], set(), []
    time = 0

    while any(remaining):
        for i in range(len(processes)):
            if arrivals[i] <= time and i not in added:
                queue.append(i)
                added.add(i)

        if not queue:
            next_arrival = min(arrivals[i] for i in range(len(processes)) if i not in added)
            gantt.append({"process": "Idle", "start": time, "end": next_arrival})
            time = next_arrival
            continue

        p = queue.pop(0)
        start = time
        run = min(quantum, remaining[p])
        time += run
        remaining[p] -= run
        gantt.append({"process": f"P{p + 1}", "start": start, "end": time})

        # New arrivals at the slice boundary enter before the preempted process.
        for i in range(len(processes)):
            if arrivals[i] <= time and i not in added:
                queue.append(i)
                added.add(i)
        if remaining[p]:
            queue.append(p)
        else:
            completion[p] = time

    rows = []
    for i in range(len(processes)):
        tat = completion[i] - arrivals[i]
        rows.append({
            "process": f"P{i + 1}", "completion": completion[i],
            "waiting": tat - bursts[i], "turnaround": tat
        })
    return {
        "gantt": gantt, "processes": rows,
        "averageWaiting": sum(p["waiting"] for p in rows) / len(rows),
        "averageTurnaround": sum(p["turnaround"] for p in rows) / len(rows)
    }


class App(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.reply(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        else:
            self.reply(404, {"error": "Страница не найдена."})

    def do_POST(self):
        if self.path != "/api/schedule":
            self.reply(404, {"error": "Страница не найдена."})
            return
        try:
            size = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(size))
            quantum = int(data["quantum"])
            processes = [
                {"arrival": int(p["arrival"]), "burst": int(p["burst"])}
                for p in data["processes"]
            ]
            if quantum < 1 or not processes:
                raise ValueError("Введите квант больше нуля и хотя бы один процесс.")
            if any(p["arrival"] < 0 or p["burst"] < 1 for p in processes):
                raise ValueError("Arrival не может быть меньше нуля, Burst должен быть больше нуля.")
            self.reply(200, schedule(processes, quantum))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
            self.reply(400, {"error": str(e) or "Проверьте введённые данные."})


if __name__ == "__main__":
    print("Откройте http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), App).serve_forever()

