import logging

import anyio
import httpx

from agency.api import create_app


def test_error_report_does_not_log_exception_text(caplog):
    from agency.services.error_reporting import report_exception

    secret_like = "token=do-not-log-this"
    with caplog.at_level(logging.ERROR, logger="agency.errors"):
        event = report_exception(
            RuntimeError(secret_like),
            request_id="req-123",
            method="POST",
            path="/v1/test",
        )

    assert event.request_id == "req-123"
    assert secret_like not in caplog.text
    assert "RuntimeError" in caplog.text
    assert "message_fingerprint" in caplog.text


def test_unhandled_api_errors_return_request_id_and_emit_event(caplog):
    app = create_app("sqlite:///:memory:")

    def explode():
        raise RuntimeError("synthetic failure")

    app.add_api_route("/test/unhandled", explode, methods=["GET"])

    async def request():
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/test/unhandled")

    with caplog.at_level(logging.ERROR, logger="agency.errors"):
        response = anyio.run(request)

    assert response.status_code == 500
    request_id = response.headers.get("x-request-id")
    assert request_id
    assert request_id in caplog.text
    assert "RuntimeError" in caplog.text
    assert "synthetic failure" not in caplog.text
