import threading

import pytest
from werkzeug.serving import make_server

from fake_pinterest.app import create_app


@pytest.fixture(scope="session")
def api_url():
    server = make_server("127.0.0.1", 0, create_app())  # porta libera scelta dal sistema
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
