"""Unit tests for JSONLogger and JSONFormatter."""

import io
import json
import logging

from src.modules.operations.services.json_logger import (
    JSONFormatter,
    JSONLogger,
)


class TestJSONFormatter:
    def test_format_emits_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test message"
        assert parsed["logger"] == "test"
        assert "timestamp" in parsed

    def test_format_includes_extra_fields(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.workflow_id = "wf-001"
        record.event_type = "workflow.start"
        record.duration_ms = 1500
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["workflow_id"] == "wf-001"
        assert parsed["event_type"] == "workflow.start"
        assert parsed["duration_ms"] == 1500


class TestJSONLogger:
    def test_workflow_start_logs_event(self):
        logger = JSONLogger("test_logger")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger._logger.handlers.clear()
        logger._logger.addHandler(handler)

        logger.workflow_start("wf-001", trace_id="trace-1")
        output = stream.getvalue()
        parsed = json.loads(output)
        assert parsed["event_type"] == "workflow.start"
        assert parsed["workflow_id"] == "wf-001"

    def test_workflow_complete_logs_duration(self):
        logger = JSONLogger("test_logger")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger._logger.handlers.clear()
        logger._logger.addHandler(handler)

        logger.workflow_complete("wf-001", duration_ms=5000)
        output = stream.getvalue()
        parsed = json.loads(output)
        assert parsed["event_type"] == "workflow.complete"
        assert parsed["duration_ms"] == 5000

    def test_workflow_fail_logs_error(self):
        logger = JSONLogger("test_logger")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger._logger.handlers.clear()
        logger._logger.addHandler(handler)

        logger.workflow_fail("wf-001", duration_ms=3000, error="Something broke")
        output = stream.getvalue()
        parsed = json.loads(output)
        assert parsed["event_type"] == "workflow.fail"
        assert "Something broke" in parsed["metadata"]["error"]

    def test_ai_request_logs_tokens(self):
        logger = JSONLogger("test_logger")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger._logger.handlers.clear()
        logger._logger.addHandler(handler)

        logger.ai_request(
            workflow_id="wf-001",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1200,
            estimated_cost_usd=0.006,
        )
        output = stream.getvalue()
        parsed = json.loads(output)
        assert parsed["metadata"]["total_tokens"] == 150
        assert parsed["metadata"]["execution_cost_usd"] == 0.006

    def test_guardrail_evaluation_logs_result(self):
        logger = JSONLogger("test_logger")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger._logger.handlers.clear()
        logger._logger.addHandler(handler)

        logger.guardrail_evaluation(
            workflow_id="wf-001",
            rule_name="cost.max",
            passed=False,
            actual_value=2.5,
            threshold=1.0,
            severity="warning",
        )
        output = stream.getvalue()
        parsed = json.loads(output)
        assert parsed["event_type"] == "guardrail.evaluation"
        assert parsed["metadata"]["passed"] is False

    def test_buffer_status_logs_fill(self):
        logger = JSONLogger("test_logger")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger._logger.handlers.clear()
        logger._logger.addHandler(handler)

        logger.buffer_status(event="flush", fill_pct=85.5, dropped=3)
        output = stream.getvalue()
        parsed = json.loads(output)
        assert parsed["event_type"] == "telemetry.buffer.status"
        assert parsed["metadata"]["fill_percentage"] == 85.5
