import http.server
import io
import os
import socket
import socketserver
import threading
import urllib.request

import pytest

import wikimapper.download
from wikimapper import download_wikidumps
from wikimapper.download import USER_AGENT


def test_download(tmpdir):
    path = tmpdir.mkdir("download").strpath

    download_wikidumps("ndswiki-latest", path)
    files = os.listdir(path)

    expected = {
        "ndswiki-latest-redirect.sql.gz",
        "ndswiki-latest-page_props.sql.gz",
        "ndswiki-latest-page.sql.gz",
    }
    assert set(files) == expected

    for e in files:
        statinfo = os.stat(os.path.join(path, e))
        assert statinfo.st_size > 0, "[{0}] should be a non-empty file".format(e)


class _FakeResponse(io.BytesIO):
    def __init__(self, content: bytes):
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content))}


@pytest.mark.parametrize(
    "mirror, expected_url",
    [
        ("https://dumps.wikimedia.org/", "https://dumps.wikimedia.org/barwiki/latest/"),
        ("https://dumps.wikimedia.org", "https://dumps.wikimedia.org/barwiki/latest/"),
        (
            "https://mirror.org/wikimedia/dumps",
            "https://mirror.org/wikimedia/dumps/barwiki/latest/",
        ),
        (
            "https://mirror.org/wikimedia/dumps/",
            "https://mirror.org/wikimedia/dumps/barwiki/latest/",
        ),
    ],
)
def test_download_request(tmpdir, monkeypatch, mirror: str, expected_url: str):
    requests = []

    def urlopen(request, timeout):
        requests.append(request)
        return _FakeResponse(b"content")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    download_wikidumps("barwiki-latest", tmpdir.strpath, mirror)

    assert [r.full_url for r in requests] == [
        expected_url + "barwiki-latest-page.sql.gz",
        expected_url + "barwiki-latest-page_props.sql.gz",
        expected_url + "barwiki-latest-redirect.sql.gz",
    ]
    # Wikimedia blocks the default `Python-urllib` user agent
    assert all(r.get_header("User-agent") == USER_AGENT for r in requests)
    assert sorted(os.listdir(tmpdir.strpath)) == [
        "barwiki-latest-page.sql.gz",
        "barwiki-latest-page_props.sql.gz",
        "barwiki-latest-redirect.sql.gz",
    ]


class _StalledServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def test_download_times_out_on_stalled_server(tmpdir, monkeypatch):
    released = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # Accept the request, then stop sending data, like the hang seen with Wikimedia
            self.send_response(200)
            self.send_header("Content-Length", "1000")
            self.end_headers()
            self.wfile.flush()
            released.wait(30)

        def log_message(self, *args):
            pass

    server = _StalledServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(wikimapper.download, "_TIMEOUT", 1)
    try:
        with pytest.raises(socket.timeout):
            download_wikidumps(
                "barwiki-latest", tmpdir.strpath, "http://127.0.0.1:{0}".format(server.server_port)
            )
    finally:
        released.set()
        server.shutdown()
        server.server_close()

    # The incomplete download is not saved as a dump
    assert os.listdir(tmpdir.strpath) == []

