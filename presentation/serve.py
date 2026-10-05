"""Live-reload dev server for the Reveal.js deck in this directory.

    uv run python presentation/serve.py

Serves ``deck.html`` on http://127.0.0.1:8000 and reloads the browser whenever
the file changes on disk. The file itself is never modified: the reload client
is injected into the served copy only, so the deck stays a single portable
artifact that still opens from ``file://``.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Final

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator


DECK: Final[Path] = Path(__file__).resolve().with_name("deck.html")
HOST: Final[str] = "127.0.0.1"
# 8000 belongs to the API container (Dockerfile:30, docker-compose.test.yml:9).
# Keep the deck server off it so both can run at once.
PORT: Final[int] = 8001

WATCHED_SUFFIXES: Final[frozenset[str]] = frozenset({".html", ".css", ".js", ".md"})
# The watch set is one directory holding one deck, so a stat poll is cheaper and
# one less dependency than an inotify binding. 200ms is below the threshold
# where an edit stops feeling immediate.
POLL_SECONDS: Final[float] = 0.2

# Idle SSE comment so the connection is not reaped while the author reads.
KEEPALIVE_SECONDS: Final[float] = 15

_INJECTION_POINT: Final[str] = "</body>"
_CLIENT_SCRIPT: Final[str] = """
  <script>
    // Injected by presentation/serve.py — not present in the file on disk.
    // Reveal is initialised with `hash: true`, so location.reload() lands back
    // on the slide you were editing instead of jumping to slide 0.
    new EventSource("/__reload").addEventListener("message", () => location.reload());
  </script>
"""

# One bounded queue per open browser tab. Bounded so a browser that stopped
# reading cannot grow the server's memory without limit.
_SUBSCRIBERS: Final[set[asyncio.Queue[None]]] = set()


async def broadcast_reload() -> None:
    """Wake every connected browser to reload."""
    for queue in tuple(_SUBSCRIBERS):
        with suppress(asyncio.QueueFull):
            queue.put_nowait(None)


def snapshot() -> dict[str, int]:
    """Map every watched file to its mtime, for change detection."""
    return {str(path): path.stat().st_mtime_ns for path in DECK.parent.iterdir() if path.suffix in WATCHED_SUFFIXES}


async def watch_deck() -> None:
    """Reload connected browsers whenever a watched file in this directory changes."""
    seen = snapshot()
    while True:
        await asyncio.sleep(POLL_SECONDS)
        current = snapshot()
        if current != seen:
            seen = current
            await broadcast_reload()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Run the file watcher for the lifetime of the server."""
    task = asyncio.create_task(watch_deck())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan)


def read_deck() -> str:
    """Return deck.html with the reload client injected before </body>."""
    html = DECK.read_text(encoding="utf-8")
    if _CLIENT_SCRIPT in html:
        return html
    if _INJECTION_POINT not in html:
        msg = f"{DECK.name} has no {_INJECTION_POINT}; cannot inject the reload client"
        raise RuntimeError(msg)
    return html.replace(_INJECTION_POINT, f"{_CLIENT_SCRIPT}{_INJECTION_POINT}", 1)


@app.get("/", response_class=HTMLResponse)
@app.get("/deck.html", response_class=HTMLResponse)
async def deck() -> HTMLResponse:
    """Serve the deck. no-store so a reload never renders a cached copy."""
    return HTMLResponse(read_deck(), headers={"Cache-Control": "no-store"})


@app.get("/__reload")
async def reload_events() -> StreamingResponse:
    """Stream reload signals to the browser over server-sent events."""
    queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
    _SUBSCRIBERS.add(queue)

    async def stream() -> AsyncIterator[str]:
        # StreamingResponse cancels this generator when the client disconnects,
        # so the finally block is the unsubscribe path.
        try:
            yield "retry: 500\n\n"
            while True:
                try:
                    await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                # One save can emit several events; drain them into this reload.
                with suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
                yield "data: reload\n\n"
        finally:
            _SUBSCRIBERS.discard(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


# Mounted last: a mount at "/" matches every path registered before it, so the
# deck routes above have to be declared first.
app.mount("/", StaticFiles(directory=DECK.parent), name="assets")


def main() -> None:
    """Serve the deck on localhost."""
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
