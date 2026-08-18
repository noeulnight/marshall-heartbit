import pytest

import marshall_heartbit


def test_config(monkeypatch):
    monkeypatch.setenv("MARSHALL_MAC", "00:12:6F:12:C2:EC")
    assert marshall_heartbit.config() == (
        "00:12:6F:12:C2:EC",
        "44FA50B2-D0A3-472E-A939-D80CF17638BB",
        30,
        60,
    )

    monkeypatch.setenv("HEARTBEAT_INTERVAL", "0")
    with pytest.raises(ValueError, match="at least 1 second"):
        marshall_heartbit.config()
