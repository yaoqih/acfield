"""Run with: python -m backend.app (one process, one event-loop owner)."""
import asyncio
import contextlib
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import Body, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from .models import Command, Settings
from .recording import Recorder
from .simulator import Simulator
from .state import Fleet
from .storage import Store
from .udp import DeviceProtocol
from .vision import watch

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger(__name__)


class ArmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool


def create_app(*, mode: Literal["demo", "hardware"] | None = None, db_path: Path | None = None,
               udp_host: str | None = None, udp_port: int | None = None, vision_url: str | None = None):
    mode = mode or os.getenv("ROBOT_MODE", "demo")
    if mode not in ("demo", "hardware"):
        raise ValueError("ROBOT_MODE must be demo or hardware")
    db_path = db_path or Path(os.getenv("ROBOT_DB", str(ROOT / "data/config.sqlite3")))
    vision_url = (vision_url or os.getenv("ROBOT_VISION_URL", "")).rstrip("/")
    if vision_url and urlparse(vision_url).scheme not in ("http", "https"):
        raise ValueError("ROBOT_VISION_URL must be an HTTP URL")

    async def clockwork(fleet):
        simulator = Simulator(fleet) if mode == "demo" else None
        while True:
            now = time.monotonic()
            # Interlocks run before integration, so an expired command never keeps moving.
            fleet.tick(now)
            if simulator:
                simulator.step(now)
            await asyncio.sleep(.025)

    @asynccontextmanager
    async def lifespan(app):
        store = Store(db_path)
        fleet = Fleet(store.load(), mode)
        app.state.store, app.state.fleet = store, fleet
        recorder = Recorder(Path(os.getenv("ROBOT_LOG_DIR", str(db_path.parent/"runs"))),
                            {"session": fleet.session, "mode": mode, "settings": fleet.settings.model_dump(),
                             "vision_url": vision_url, "protocol": "v1/explicit-arm"})
        fleet.record = recorder.record
        fleet.record("startup", {"session": fleet.session})
        app.state.recorder = recorder
        transport = None
        tasks = {}
        app.state.tasks = tasks

        async def supervise(name, coroutine):
            try:
                await coroutine
                raise RuntimeError("后台任务意外结束")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                fleet.runtime_fault = name+": "+type(exc).__name__
                fleet.stop_all()
                fleet.event("后台任务故障，请重启服务："+fleet.runtime_fault)
                log.exception("Critical task %s failed", name)
        try:
            if mode == "hardware":
                transport, protocol = await asyncio.get_running_loop().create_datagram_endpoint(
                    lambda: DeviceProtocol(fleet), local_addr=(udp_host or os.getenv("ROBOT_UDP_HOST", "127.0.0.1"),
                    udp_port if udp_port is not None else int(os.getenv("ROBOT_UDP_PORT", "9999"))))
                app.state.udp = protocol
            tasks["control"] = asyncio.create_task(supervise("control", clockwork(fleet)))
            if mode == "hardware" and vision_url:
                tasks["vision"] = asyncio.create_task(supervise("vision", watch(fleet, vision_url)))
            yield
        finally:
            fleet.stop_all()
            for task in tasks.values():
                task.cancel()
            for task in tasks.values():
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            if transport:
                await asyncio.sleep(.05)
                transport.close()
            store.close()
            await asyncio.to_thread(recorder.close)

    app = FastAPI(title="ACField Control API", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not echo raw NaN/Infinity inputs into a JSON error response.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
            for e in exc.errors()]})

    def robot(ident):
        try:
            return app.state.fleet.robot(ident)
        except KeyError:
            raise HTTPException(404, "小车不存在") from None

    @app.get("/api/health")
    async def health():
        fleet, recorder = app.state.fleet, app.state.recorder
        tasks = {name: "stopped" if task.done() else "running" for name, task in app.state.tasks.items()}
        healthy = (not fleet.runtime_fault and all(v == "running" for v in tasks.values())
                   and time.monotonic()-fleet.control_at < .5 and not recorder.error and recorder.dropped == 0)
        return JSONResponse(status_code=200 if healthy else 503, content={
            "status": "ok" if healthy else "degraded", "mode": mode, "tasks": tasks,
            "fault": fleet.runtime_fault, "vision_connected": fleet.camera["connected"],
            "ready": healthy and all(fleet.ready(r, time.monotonic()) is None for r in fleet.robots.values()),
            "run_id": recorder.run_id, "recording_error": recorder.error, "recording_dropped": recorder.dropped})

    @app.get("/api/state")
    async def state():
        return app.state.fleet.snapshot()

    @app.get("/api/config")
    async def config():
        return app.state.fleet.settings

    @app.put("/api/config")
    async def configure(settings: Settings):
        fleet = app.state.fleet
        if any(r.armed or (r.pending and r.pending["action"] == "arm") for r in fleet.robots.values()):
            raise HTTPException(409, "请先锁定所有小车再修改配置")
        # Save first; failed writes must not replace live state.
        app.state.store.save(settings)
        fleet.stop_all()
        fresh = Fleet(settings, mode)
        fresh.send, fresh.estop, fresh.record = fleet.send, fleet.estop, fleet.record
        fresh.runtime_fault = fleet.runtime_fault
        fleet.__dict__.update(fresh.__dict__)
        fleet.record("configuration", {"session": fleet.session, "settings": settings.model_dump()})
        if mode == "demo":
            Simulator(fleet)
        fleet.event("配置已保存 · 全车锁定，请释放全局停止后重新解锁")
        return settings

    @app.post("/api/robots/{ident}/arm")
    async def arm(ident: str, body: ArmRequest, x_control_id: str | None = Header(default=None, min_length=1, max_length=64)):
        if body.enabled and not x_control_id:
            raise HTTPException(422, "解锁需提供 X-Control-ID 控制页面标识")
        try:
            app.state.fleet.arm(robot(ident), body.enabled, x_control_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        r = robot(ident)
        return {"armed": r.armed, "pending": bool(r.pending and r.pending["action"] == "arm")}

    @app.post("/api/robots/{ident}/release")
    async def release(ident: str, x_control_id: str = Header(min_length=1, max_length=64)):
        # Conditional cleanup must not race a new controller's acquisition.
        return {"released": app.state.fleet.release(robot(ident), x_control_id)}

    @app.post("/api/robots/{ident}/command")
    async def command(ident: str, body: Command, x_control_id: str | None = Header(default=None, min_length=1, max_length=64)):
        if (body.v or body.omega) and not x_control_id:
            raise HTTPException(422, "运动需提供 X-Control-ID 控制页面标识")
        try:
            return app.state.fleet.command(robot(ident), body, x_control_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/commands")
    async def commands(body: dict[str, Command] = Body(min_length=1, max_length=16),
                       x_control_id: str | None = Header(default=None, min_length=1, max_length=64)):
        if any(cmd.v or cmd.omega for cmd in body.values()) and not x_control_id:
            raise HTTPException(422, "运动需提供 X-Control-ID 控制页面标识")
        try:
            return app.state.fleet.commands(body, x_control_id)
        except KeyError:
            raise HTTPException(404, "小车不存在") from None
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/stop")
    async def stop():
        app.state.fleet.stop_all()
        return {"estop": True}

    @app.post("/api/reset-stop")
    async def reset_stop():
        app.state.fleet.estop = False
        app.state.fleet.event("全局停止已释放 · 小车仍需逐车解锁")
        return {"estop": False}

    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                # No queues: slow clients get the next current snapshot, never a backlog.
                await asyncio.wait_for(ws.send_json(app.state.fleet.snapshot()), timeout=1.)
                await asyncio.sleep(.1)
        except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
            with contextlib.suppress(RuntimeError):
                await ws.close()

    @app.get("/api/camera/stream")
    async def camera():
        if mode == "demo" or not vision_url:
            raise HTTPException(404, "未配置真实相机；模拟模式仅展示合成场地")
        client = httpx.AsyncClient(timeout=httpx.Timeout(5, read=10))
        try:
            response = await client.send(client.build_request("GET", vision_url+"/stream.mjpg"), stream=True)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            await client.aclose()
            raise HTTPException(502, "无法连接相机流") from exc

        async def chunks():
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()
        return StreamingResponse(chunks(), media_type=response.headers.get("content-type", "multipart/x-mixed-replace; boundary=frame"))

    dist = ROOT / "frontend/dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/")
    async def index():
        if not (dist / "index.html").is_file():
            raise HTTPException(503, "请先在 frontend 执行 npm install && npm run build")
        return FileResponse(dist / "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    from .startup import startup_summary
    host = os.getenv("ROBOT_HOST", "127.0.0.1")
    port = int(os.getenv("ROBOT_PORT", "8000"))
    print(startup_summary(host, port, os.getenv("ROBOT_MODE", "demo")), flush=True)
    uvicorn.run("backend.app:app", host=host, port=port, workers=1)
