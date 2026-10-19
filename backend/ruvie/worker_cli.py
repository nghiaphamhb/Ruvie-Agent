"""Run the private document-ingestion worker as a separate process."""

import logging
import signal
import threading
from collections.abc import Callable

import httpx

from ruvie.adapters.blob_storage import DEFAULT_BLOB_ROOT, LocalBlobStore
from ruvie.adapters.embedding import create_query_embedder
from ruvie.config import load_settings
from ruvie.database import create_database_engine, create_session_factory
from ruvie.services.documents.ingestion import DocumentIngestionWorker


def run_worker_loop(
    run_once: Callable[[], str | None],
    stop_event: threading.Event,
    *,
    poll_interval: float = 2.0,
) -> None:
    """Run jobs until stopped; wait poll_interval seconds only when the queue is empty."""
    while not stop_event.is_set():
        job_id = run_once()
        if job_id is None:
            stop_event.wait(poll_interval)


def main() -> int:
    """Build worker resources and handle shutdown signals; return the process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings()
    engine = create_database_engine(settings.database_url)
    client = httpx.Client(proxy=settings.embedding_proxy_url, trust_env=False)
    # The signal handler sets this event; waiting workers wake up and stop cleanly.
    stop_event = threading.Event()
    previous_handlers = {}

    def stop(_signum, _frame):
        stop_event.set()

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, stop)
        session_factory = create_session_factory(engine)
        embedder = create_query_embedder(settings, client)
        blob_store = LocalBlobStore(DEFAULT_BLOB_ROOT)

        # One fresh session per job; the worker heartbeat uses separate sessions.
        def run_once() -> str | None:
            with session_factory() as session:
                return DocumentIngestionWorker(
                    session, blob_store, embedder, settings.embedding_profile,
                    session_factory=session_factory,
                ).run_next()

        logging.info("Document ingestion worker started")
        run_worker_loop(run_once, stop_event)
        logging.info("Document ingestion worker stopped")
        return 0
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        client.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
