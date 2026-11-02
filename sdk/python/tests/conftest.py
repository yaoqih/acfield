import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app


@pytest.fixture
def server(tmp_path):
    with TestClient(create_app(mode="demo", db_path=tmp_path / "config.db")) as api:
        yield api


def forward(api, request):
    response = api.request(request.method, request.url.raw_path.decode(),
                           content=request.content, headers=request.headers)
    return httpx.Response(response.status_code, content=response.content,
                          headers=response.headers)


@pytest.fixture
def transport(server):
    return httpx.MockTransport(lambda request: forward(server, request))
