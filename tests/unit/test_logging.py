"""P1-1: JSON logs carry request_id and workflow_id (CLAUDE.md §16)."""

import json
import logging

import pytest

from app.core.logging import request_id_var, setup_logging, workflow_id_var


@pytest.fixture
def log_lines(capsys):
    setup_logging("DEBUG")

    def read() -> list[dict]:
        out = capsys.readouterr().out
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    yield read
    logging.getLogger().handlers.clear()


def test_line_is_json_with_ids(log_lines):
    rid = request_id_var.set("req-123")
    wid = workflow_id_var.set("wf-456")
    try:
        logging.getLogger("clouddesk.test").info("hello %s", "world")
    finally:
        request_id_var.reset(rid)
        workflow_id_var.reset(wid)

    [line] = log_lines()
    assert line["message"] == "hello world"
    assert line["level"] == "INFO"
    assert line["logger"] == "clouddesk.test"
    assert line["request_id"] == "req-123"
    assert line["workflow_id"] == "wf-456"
    assert "timestamp" in line


def test_ids_are_null_outside_a_request(log_lines):
    logging.getLogger("clouddesk.test").warning("no context")
    [line] = log_lines()
    assert line["request_id"] is None
    assert line["workflow_id"] is None


def test_extra_fields_are_included(log_lines):
    logging.getLogger("clouddesk.test").info("node done", extra={"node": "triage", "duration_ms": 12})
    [line] = log_lines()
    assert line["node"] == "triage"
    assert line["duration_ms"] == 12


def test_exception_is_serialised(log_lines):
    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("clouddesk.test").exception("failed")
    [line] = log_lines()
    assert line["level"] == "ERROR"
    assert "ValueError: boom" in line["exc_info"]


def test_setup_is_idempotent(log_lines):
    setup_logging("INFO")
    setup_logging("INFO")
    assert len(logging.getLogger().handlers) == 1
    logging.getLogger("clouddesk.test").info("once")
    assert len(log_lines()) == 1
