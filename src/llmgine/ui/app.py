import json
import math
from pathlib import Path
from typing import Any, Dict

from fastapi import Body, FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .hub import hub
from .state import state


class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles infinity and NaN values."""
    def encode(self, obj):
        if isinstance(obj, dict):
            obj = self._sanitize_dict(obj)
        elif isinstance(obj, list):
            obj = self._sanitize_list(obj)
        return super().encode(obj)

    def _sanitize_dict(self, obj: dict) -> dict:
        """Recursively sanitize dictionary values."""
        sanitized = {}
        for key, value in obj.items():
            if isinstance(value, float):
                if math.isinf(value):
                    sanitized[key] = "Infinity" if value > 0 else "-Infinity"
                elif math.isnan(value):
                    sanitized[key] = "NaN"
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list(value)
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_list(self, obj: list) -> list:
        """Recursively sanitize list values."""
        sanitized = []
        for item in obj:
            if isinstance(item, float):
                if math.isinf(item):
                    sanitized.append("Infinity" if item > 0 else "-Infinity")
                elif math.isnan(item):
                    sanitized.append("NaN")
                else:
                    sanitized.append(item)
            elif isinstance(item, dict):
                sanitized.append(self._sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self._sanitize_list(item))
            else:
                sanitized.append(item)
        return sanitized


def safe_json_response(data: Any) -> Response:
    """Create a Response with safe JSON encoding."""
    encoder = SafeJSONEncoder()
    json_str = encoder.encode(data)
    return Response(
        content=json_str,
        media_type="application/json"
    )

static_dir = Path(__file__).with_suffix("").parent / "static"
templates_dir = Path(__file__).with_suffix("").parent / "templates"

app = FastAPI(title="LLMgine Bus Playground", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))


@app.on_event("startup")
async def _startup() -> None:
    # Lazy: don't auto-start bus; let user hit "Start"
    pass


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


# ---------------- WebSocket: live stream ----------------
@app.websocket("/ws")
async def ws_handler(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        # Initial state snapshot
        metrics = await state.gather_metrics()
        await ws.send_json({"type": "snapshot", "data": metrics})
        while True:
            await ws.receive_text()  # we don't need inbound messages; keepalive
    except Exception:
        pass
    finally:
        await hub.disconnect(ws)


# ---------------- Bus controls ----------------
@app.post("/api/bus/start")
async def api_bus_start(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    kind = payload.get("kind", "resilient")
    qsize = int(payload.get("queue_size", 10000))
    backpressure = payload.get("backpressure", "drop_oldest")
    state.config.bus_kind = "resilient" if kind == "resilient" else "basic"
    state.config.queue_size = qsize
    state.config.backpressure = backpressure
    await state.start_bus()
    await hub.broadcast({"type": "notice", "data": {"msg": f"Bus started ({state.config.bus_kind})"}})
    return JSONResponse({"ok": True})

@app.post("/api/bus/stop")
async def api_bus_stop() -> JSONResponse:
    await state.stop_bus()
    await hub.broadcast({"type": "notice", "data": {"msg": "Bus stopped"}})
    return JSONResponse({"ok": True})

@app.post("/api/bus/reset")
async def api_bus_reset() -> JSONResponse:
    await state.reset_bus()
    await hub.broadcast({"type": "notice", "data": {"msg": "Bus reset"}})
    return JSONResponse({"ok": True})

@app.post("/api/bus/batch")
async def api_bus_batch(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    await state.apply_batch_config(int(payload.get("size", 10)), float(payload.get("timeout", 0.01)))
    await hub.broadcast({"type": "notice", "data": {"msg": "Batch parameters updated"}})
    return JSONResponse({"ok": True})

# ---------------- Middleware toggles ----------------
@app.post("/api/mw")
async def api_middleware_toggle(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    name = payload.get("name")
    enabled = bool(payload.get("enabled", True))
    if name == "logging":
        state.toggle_logging_mw(enabled)
    elif name == "validation":
        state.toggle_validation_mw(enabled)
    elif name == "timing":
        state.toggle_timing_mw(enabled)
    elif name == "retry":
        state.toggle_retry_mw(enabled)
    elif name == "rate_limit":
        state.toggle_rate_limit_mw(enabled, float(payload.get("max_per_second", 10.0)))
    else:
        return JSONResponse({"ok": False, "error": "unknown middleware"}, status_code=400)
    return JSONResponse({"ok": True})

# ---------------- Filters ----------------
@app.post("/api/filters/session")
async def api_filters_session(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    state.add_session_filter(payload.get("include"), payload.get("exclude"))
    return JSONResponse({"ok": True})

@app.post("/api/filters/type")
async def api_filters_type(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    state.add_event_type_filter(payload.get("include"), payload.get("exclude"))
    return JSONResponse({"ok": True})

@app.post("/api/filters/pattern")
async def api_filters_pattern(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    state.add_pattern_filter(payload.get("include"), payload.get("exclude"))
    return JSONResponse({"ok": True})

@app.post("/api/filters/metadata")
async def api_filters_metadata(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    state.add_metadata_filter(payload.get("required"), payload.get("keys"))
    return JSONResponse({"ok": True})

@app.post("/api/filters/rate")
async def api_filters_rate(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    state.add_rate_limit_filter(float(payload.get("max_per_sec", 100.0)),
                                bool(payload.get("per_session", True)),
                                bool(payload.get("per_type", False)))
    return JSONResponse({"ok": True})

# ---------------- Playground: commands/events ----------------
@app.post("/api/commands/echo")
async def api_cmd_echo(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    res = await state.exec_echo(str(payload.get("text", "")), payload.get("session"))
    return JSONResponse({"ok": True, "result": res.__dict__})

@app.post("/api/commands/fail")
async def api_cmd_fail(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    res = await state.exec_fail(str(payload.get("message", "boom")),
                                bool(payload.get("raise_exception", True)),
                                payload.get("session"))
    return JSONResponse({"ok": True, "result": res.__dict__})

@app.post("/api/commands/sleep")
async def api_cmd_sleep(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    res = await state.exec_sleep(float(payload.get("seconds", 0.25)), payload.get("session"))
    return JSONResponse({"ok": True, "result": res.__dict__})

@app.post("/api/commands/generate")
async def api_cmd_gen(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    res = await state.exec_generate(int(payload.get("count", 100)),
                                    int(payload.get("delay_ms", 0)),
                                    str(payload.get("payload", "ping")),
                                    payload.get("session"))
    return JSONResponse({"ok": True, "result": res.__dict__})

@app.post("/api/events/log")
async def api_evt_log(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    await state.publish_log(str(payload.get("message", "")), payload.get("session"))
    return JSONResponse({"ok": True})

@app.post("/api/events/schedule_ping")
async def api_schedule_ping(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    await state.schedule_ping(float(payload.get("in_seconds", 3.0)),
                              str(payload.get("message", "scheduled ping")),
                              payload.get("session"))
    return JSONResponse({"ok": True})

# ---------------- Resilience panels ----------------
@app.get("/api/metrics")
async def api_metrics() -> JSONResponse:
    return safe_json_response(await state.gather_metrics())

@app.post("/api/loadgen/start")
async def api_load_start(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    name = state.start_firehose(float(payload.get("rps", 200.0)),
                                float(payload.get("duration_s", 10.0)),
                                str(payload.get("prefix", "firehose")),
                                payload.get("session"))
    return JSONResponse({"ok": True, "name": name})

@app.post("/api/loadgen/stop")
async def api_load_stop(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    state.stop_task(str(payload.get("name")))
    return JSONResponse({"ok": True})
