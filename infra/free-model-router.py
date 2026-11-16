#!/usr/bin/env python3
"""free-model-router.py — AURORA 开发专用多车道自动路由器
- 汇聚全部免费车道（NIM / OFM free 池 / EAC / kilo 兜底）
- lkgp：优先走上次成功的车道；失败自动 failover 下一个
- 连续 3 次失败进 5 分钟冷却，冷却结束自动回归
- 后台线程每 90 秒全车道健康探测
- 对外暴露 OpenAI 兼容接口（模型名固定 free-pool）
监听 127.0.0.1:18970
"""
import json, time, threading, logging, sys
import requests
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN = ("127.0.0.1", 18970)
LOG = "/home/zyt/abrowser/router.log"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)])
log = logging.getLogger("free-model-router")

OR_KEY = open("/tmp/or_gk_full.txt").read().strip()
_OFM_SETTINGS = "/home/zyt/.dsh/our-free-model/settings.json"
def _ofm_key():
    """OFM forwardKey 会动态轮换，每次实时读取，永不过期"""
    try:
        with open(_OFM_SETTINGS) as f:
            return json.load(f).get("forwardKey", "")
    except Exception:
        return ""
OFM_KEY = _ofm_key()

LANES = [
    {"name": "nim-step5",          "base": "http://127.0.0.1:20128/v1", "key": OR_KEY,  "model": "nvidia/stepfun-ai/step-5-preview"},
    {"name": "nim-mistral-large",  "base": "http://127.0.0.1:20128/v1", "key": OR_KEY,  "model": "nvidia/mistralai/mistral-large-4-1t-a52b"},
    {"name": "nim-nemotron-ultra", "base": "http://127.0.0.1:20128/v1", "key": OR_KEY,  "model": "nvidia/nvidia/nemotron-3-ultra-550b-a55b"},
    {"name": "nim-nemotron-35-super-120b", "base": "http://127.0.0.1:20128/v1", "key": OR_KEY, "model": "nvidia/nvidia/nemotron-3.5-super-vl-120b-a12b"},
    {"name": "ofm-nemotron-ultra", "base": "http://127.0.0.1:18899/v1", "key": OFM_KEY, "model": "nvidia/nemotron-3-ultra-550b-a55b:free"},
    {"name": "ofm-nemotron-35-super", "base": "http://127.0.0.1:18899/v1", "key": OFM_KEY, "model": "nvidia/nemotron-3.5-super-vl:free"},
    {"name": "ofm-ernie-55-flash", "base": "http://127.0.0.1:18899/v1", "key": OFM_KEY, "model": "baidu/ernie-5.5-flash-preview:free"},
    {"name": "ofm-dots-3-note",    "base": "http://127.0.0.1:18899/v1", "key": OFM_KEY, "model": "dots-studio/dots-3-note-preview:free"},
    {"name": "ofm-minimax-m31",    "base": "http://127.0.0.1:18899/v1", "key": OFM_KEY, "model": "minimaxai/minimax-m3.1-flash"},
    {"name": "ofm-eac-glm53",      "base": "http://127.0.0.1:18899/v1", "key": OFM_KEY, "model": "z-ai/glm-5.3-flash", "slow": True},
]
COOLDOWN_S = 300
FAIL_TO_COOL = 3

lock = threading.Lock()
state = {  # name -> dict(failures, cool_until, ok_count, last_ok_ts, last_err)
    l["name"]: {"failures": 0, "cool_until": 0, "ok": 0, "last_ok": 0, "last_err": ""} for l in LANES
}
preferred = LANES[0]["name"]  # lkgp 指针

def lane_available(l):
    st = state[l["name"]]
    return time.time() >= st["cool_until"]

def ordered_lanes():
    with lock:
        avail = [l for l in LANES if lane_available(l)]
        # lkgp：preferred 排最前；slow 车道垫底；其余保持原序
        avail.sort(key=lambda l: (l.get("slow", False), 0 if l["name"] == preferred else 1))
        cooling = [l for l in LANES if not lane_available(l)]
        return avail + cooling  # 冷却中的作为最后手段（万一全冷却）

def mark(name, ok, err=""):
    with lock:
        st = state[name]
        if ok:
            st.update(failures=0, ok=st["ok"] + 1, last_ok=time.time(), last_err="")
            global preferred
            preferred = name
        else:
            st["failures"] += 1
            st["last_err"] = err[:120]
            if st["failures"] >= FAIL_TO_COOL:
                st["cool_until"] = time.time() + COOLDOWN_S
                st["failures"] = 0
                log.info(f"[COOLDOWN] {name} 冷却 {COOLDOWN_S}s（连续失败）: {err[:80]}")

def probe_loop():
    while True:
        for l in LANES:
            if not lane_available(l):
                continue
            try:
                r = requests.post(f"{l['base']}/chat/completions",
                    headers={"Authorization": f"Bearer {l['key']}", "Content-Type": "application/json"},
                    json={"model": l["model"], "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                    timeout=45)
                mark(l["name"], r.status_code == 200, f"probe HTTP {r.status_code}")
            except Exception as e:
                mark(l["name"], False, f"probe {type(e).__name__}")
        time.sleep(90)

def try_lane(l, body, stream, timeout):
    payload = dict(body)
    payload["model"] = l["model"]
    key = _ofm_key() if "18899" in l["base"] else l["key"]  # OFM 车道每次实时取 key
    r = requests.post(f"{l['base']}/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      json=payload, stream=stream, timeout=timeout)
    return r

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # 静默默认访问日志
        pass

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/v1/models", "/models"):
            self._json(200, {"object": "list", "data": [
                {"id": "free-pool", "object": "model", "owned_by": "free-model-router"},
                {"id": "free-fast", "object": "model", "owned_by": "free-model-router"}]})
        elif self.path == "/health":
            with lock:
                now = time.time()
                table = [{"name": l["name"], "model": l["model"], "preferred": l["name"] == preferred,
                          "cooling": now < state[l["name"]]["cool_until"],
                          "ok_count": state[l["name"]]["ok"],
                          "last_err": state[l["name"]]["last_err"]} for l in LANES]
            self._json(200, {"lanes": table, "preferred": preferred})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.endswith("/chat/completions"):
            return self._json(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n))
        except Exception:
            return self._json(400, {"error": "bad json"})
        stream = bool(body.get("stream"))
        ask = body.get("model", "free-pool")
        timeout = (20, 200)  # connect/read；EAC 慢车道留给兜底
        errors = []
        for l in ordered_lanes():
            if ask == "free-fast" and l.get("slow"):
                continue  # free-fast 跳过慢车道
            try:
                r = try_lane(l, body, stream, timeout)
                if r.status_code == 200:
                    mark(l["name"], True)
                    log.info(f"[OK] {l['name']} ({'stream' if stream else 'json'})")
                    self.send_response(200)
                    self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
                    if stream:
                        self.send_header("Transfer-Encoding", "chunked")
                        self.end_headers()
                        for chunk in r.iter_content(chunk_size=1024):
                            if chunk:
                                self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
                        self.wfile.write(b"0\r\n\r\n")
                    else:
                        data = r.content
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                    return
                errors.append(f"{l['name']}: HTTP {r.status_code}")
                mark(l["name"], False, f"HTTP {r.status_code}")
            except Exception as e:
                errors.append(f"{l['name']}: {type(e).__name__}")
                mark(l["name"], False, f"{type(e).__name__}: {str(e)[:80]}")
        log.info(f"[ALL-FAIL] {errors}")
        self._json(502, {"error": "all lanes failed", "detail": errors})

if __name__ == "__main__":
    threading.Thread(target=probe_loop, daemon=True).start()
    log.info(f"free-model-router up on {LISTEN}, {len(LANES)} lanes")
    ThreadingHTTPServer(LISTEN, Handler).serve_forever()
