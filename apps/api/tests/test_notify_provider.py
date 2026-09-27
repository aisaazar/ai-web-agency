import agency.providers.notify as notify


def test_console_provider_can_send_without_network(capsys):
    provider = notify.get_notify_provider("console")
    provider.send(notify.Notification(
        to="owner@example.com",
        subject="New lead",
        body="A lead arrived.",
    ))
    captured = capsys.readouterr()
    assert "[notification]" in captured.out
    assert "owner@example.com" in captured.out


def test_smtp_provider_sends_message_without_exposing_password(monkeypatch):
    monkeypatch.setenv("AGENCY_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("AGENCY_SMTP_PORT", "587")
    monkeypatch.setenv("AGENCY_SMTP_USERNAME", "sender@example.com")
    monkeypatch.setenv("AGENCY_SMTP_PASSWORD", "secret-value")
    monkeypatch.setenv("AGENCY_SMTP_FROM", "sender@example.com")

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, username, password):
            sent["login"] = (username, password)

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setattr(notify.smtplib, "SMTP", FakeSMTP)
    notify.SMTPNotifyProvider().send(notify.Notification(
        to="owner@example.com",
        subject="New lead",
        body="A lead arrived.",
    ))

    assert sent["connection"] == ("smtp.example.com", 587, 15)
    assert sent["starttls"] is True
    assert sent["login"] == ("sender@example.com", "secret-value")
    assert sent["message"]["To"] == "owner@example.com"
    assert sent["message"]["Subject"] == "New lead"
    assert "A lead arrived." in sent["message"].get_content()
