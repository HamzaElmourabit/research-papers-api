"""
Tests pour les modules d'amélioration
Exécuter avec: pytest tests/test_improvements.py -v
"""

import pytest
from utils.error_handling import (
    CircuitBreaker,
    CircuitBreakerError,
    retry_with_backoff
)

from utils.data_quality import (
    DataQualityValidator,
    DataQualityAlert,
    QualityLevel
)

from utils.logging_config import (
    setup_logging,
    get_logger,
    ContextFilter
)

class TestErrorHandling:
    """Tests for error handling module"""
    
    def test_retry_with_backoff_success(self):
        """Test successful call on first attempt"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = succeeds()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_with_backoff_recovers(self):
        """Test recovery after failures"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = fails_then_succeeds()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """Test max retries exceeded"""
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def always_fails():
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError):
            always_fails()
    
    def test_circuit_breaker(self):
        """Test circuit breaker opens after failures"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        call_count = 0
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Error")
        
        # Call 3 times to trigger circuit break
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_function)
        
        # Now circuit should be open
        assert cb.state == "OPEN"
        
        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            cb.call(failing_function)


class TestDataQuality:
    """Tests for data quality module"""
    
    def test_validation_rate(self):
        """Test validation rate calculation"""
        metrics = DataQualityMetrics(
            batch_id="TEST-001",
            total_records=100,
            valid_records=95
        )
        assert metrics.get_validation_rate() == 95.0
    
    def test_quality_level_critical(self):
        """Test critical quality level"""
        metrics = DataQualityMetrics(
            batch_id="TEST-001",
            total_records=100,
            valid_records=70  # 70% < 80% threshold
        )
        assert metrics.get_quality_level() == QualityLevel.CRITICAL
    
    def test_quality_level_warning(self):
        """Test warning quality level"""
        metrics = DataQualityMetrics(
            batch_id="TEST-001",
            total_records=100,
            valid_records=90  # 90% is between 80% and 95%
        )
        assert metrics.get_quality_level() == QualityLevel.WARNING
    
    def test_quality_level_good(self):
        """Test good quality level"""
        metrics = DataQualityMetrics(
            batch_id="TEST-001",
            total_records=100,
            valid_records=96  # 96% >= 95%
        )
        assert metrics.get_quality_level() == QualityLevel.GOOD
    
    def test_data_quality_validator(self):
        """Test data quality validator"""
        validator = DataQualityValidator("TEST-001")
        
        valid_paper = {
            "arxiv_id": "2023.01234",
            "title": "Test Paper",
            "abstract": "Test abstract",
            "authors": ["Author One"],
            "categories": ["cs.AI"]
        }
        
        is_valid = validator.validate_record(valid_paper, "2023.01234")
        assert is_valid
        assert validator.metrics.valid_records == 1
    
    def test_duplicate_detection(self):
        """Test duplicate detection"""
        validator = DataQualityValidator("TEST-001")
        
        papers = [
            {"arxiv_id": "2023.01", "title": "Paper 1"},
            {"arxiv_id": "2023.02", "title": "Paper 2"},
            {"arxiv_id": "2023.01", "title": "Paper 1 duplicate"}  # Duplicate
        ]
        
        duplicates = validator.check_duplicates(papers, id_field='arxiv_id')
        assert duplicates == 1
        assert validator.metrics.duplicate_records == 1
    
    def test_quality_alert_critical(self):
        """Test critical alert"""
        alert = DataQualityAlert(critical_threshold=80)
        
        metrics = DataQualityMetrics(
            batch_id="TEST-001",
            total_records=100,
            valid_records=70  # Below critical threshold
        )
        
        alert_result = alert.check_metrics(metrics)
        assert alert_result is not None
        assert alert_result['severity'] == 'CRITICAL'
    
    def test_quality_alert_none(self):
        """Test no alert when quality is good"""
        alert = DataQualityAlert(
            critical_threshold=80,
            warning_threshold=95
        )
        
        metrics = DataQualityMetrics(
            batch_id="TEST-001",
            total_records=100,
            valid_records=96  # Above warning threshold
        )
        
        alert_result = alert.check_metrics(metrics)
        assert alert_result is None


class TestLogging:
    """Tests for logging module"""
    
    def test_setup_logging(self):
        """Test logging setup"""
        logger = setup_logging(log_level="DEBUG", use_json=True)
        assert logger is not None
        assert len(logger.handlers) > 0
    
    def test_context_filter_set_get(self):
        """Test context filter set and get"""
        ContextFilter.clear_context()
        
        ContextFilter.set_context('batch_id', 'TEST-001')
        assert ContextFilter.get_context('batch_id') == 'TEST-001'
        
        ContextFilter.clear_context()
        assert ContextFilter.get_context('batch_id') is None
    
    def test_get_logger(self):
        """Test get logger"""
        logger = get_logger(__name__)
        assert logger is not None
        assert logger.name == __name__


# Import after class definition to avoid forward reference issues
from utils.data_quality import DataQualityMetrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
