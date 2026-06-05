"""
Tests pour les modules d'amélioration
Exécuter avec: pytest tests/test_improvements.py -v
"""

import sys
import os
import pytest

# FIX PATH (important pour CI)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.error_handling import (
    CircuitBreaker,
    CircuitBreakerError,
    retry_with_backoff
)

from utils.data_quality import (
    DataQualityValidator,
    DataQualityAlert,
    QualityLevel,
    DataQualityMetrics
)

from utils.logging_config import (
    setup_logging,
    get_logger,
    ContextFilter
)


class TestErrorHandling:

    def test_retry_with_backoff_success(self):
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        assert succeeds() == "success"
        assert call_count == 1

    def test_retry_with_backoff_recovers(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        assert fails_then_succeeds() == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def always_fails():
            raise ValueError("Permanent error")

        with pytest.raises(ValueError):
            always_fails()

    def test_circuit_breaker(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        def failing():
            raise ValueError("Error")

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(failing)

        assert cb.state == "OPEN"

        with pytest.raises(CircuitBreakerError):
            cb.call(failing)


class TestDataQuality:

    def test_validation_rate(self):
        metrics = DataQualityMetrics(
            batch_id="TEST-001",
            total_records=100,
            valid_records=95
        )
        assert metrics.get_validation_rate() == 95.0

    def test_quality_levels(self):
        m1 = DataQualityMetrics("T1", 100, 70)
        assert m1.get_quality_level() == QualityLevel.CRITICAL

        m2 = DataQualityMetrics("T2", 100, 90)
        assert m2.get_quality_level() == QualityLevel.WARNING

        m3 = DataQualityMetrics("T3", 100, 96)
        assert m3.get_quality_level() == QualityLevel.GOOD

    def test_validator(self):
        v = DataQualityValidator("TEST")

        record = {
            "arxiv_id": "123",
            "title": "Test",
            "abstract": "Test",
            "authors": ["A"],
            "categories": ["cs.AI"]
        }

        assert v.validate_record(record, "123") is True
        assert v.metrics.valid_records == 1

    def test_duplicates(self):
        v = DataQualityValidator("TEST")

        data = [
            {"arxiv_id": "1"},
            {"arxiv_id": "2"},
            {"arxiv_id": "1"}
        ]

        dup = v.check_duplicates(data, "arxiv_id")
        assert dup == 1

    def test_alert(self):
        alert = DataQualityAlert(critical_threshold=80)

        m = DataQualityMetrics("T", 100, 70)
        result = alert.check_metrics(m)

        assert result is not None
        assert result["severity"] == "CRITICAL"


class TestLogging:

    def test_logging(self):
        logger = setup_logging(log_level="DEBUG", use_json=True)
        assert logger is not None

    def test_context(self):
        ContextFilter.clear_context()
        ContextFilter.set_context("batch", "123")

        assert ContextFilter.get_context("batch") == "123"

    def test_get_logger(self):
        logger = get_logger("test")
        assert logger.name == "test"
