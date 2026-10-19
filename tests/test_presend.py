"""presend.curl must never read the previous URL's body. No network: subprocess is stubbed."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import presend  # noqa: E402


def test_a_failed_fetch_does_not_reuse_the_last_pages_body(monkeypatch, tmp_path):
    monkeypatch.setattr(presend, "BODY", str(tmp_path / "body"))
    Path(presend.BODY).write_text("<a>order online</a> 404 page not found")  # left by the previous check

    def timed_out(cmd, **kw):  # curl --max-time hit: writes no file, prints 000
        return SimpleNamespace(stdout="000")
    monkeypatch.setattr(presend.subprocess, "run", timed_out)
    code, body = presend.curl("https://example.test/menu")
    assert code == "000"
    assert body == ""
    assert not os.path.exists(presend.BODY)
