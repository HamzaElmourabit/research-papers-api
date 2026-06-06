from enum import Enum
from datetime import datetime


class QualityLevel(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    GOOD = "GOOD"


class DataQualityMetrics:
    def __init__(
        self,
        batch_id,
        timestamp=None,
        total_records=0,
        valid_records=0,
        rejected_records=0,
        null_fields=None,
        invalid_fields=None,
        duplicate_records=0,
        duplicate_ids=None,
        errors=None,
    ):
        self.batch_id = batch_id
        self.timestamp = timestamp or datetime.utcnow().timestamp()

        self.total_records = total_records
        self.valid_records = valid_records
        self.rejected_records = rejected_records

        self.null_fields = null_fields or {}
        self.invalid_fields = invalid_fields or {}
        self.duplicate_records = duplicate_records
        self.duplicate_ids = duplicate_ids or []
        self.errors = errors or {}

    def get_validation_rate(self):
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    def get_quality_level(self):
        rate = self.get_validation_rate()

        # IMPORTANT FIX: test expects 90 => WARNING, not CRITICAL
        if rate < 80:
            return QualityLevel.CRITICAL
        elif rate < 95:
            return QualityLevel.WARNING
        else:
            return QualityLevel.GOOD


class DataQualityValidator:
    def __init__(self, name):
        self.name = name

        # ✅ REQUIRED by tests
        self.metrics = DataQualityMetrics(
            batch_id=name,
            total_records=0,
            valid_records=0,
        )

    def validate_record(self, record, expected_id=None):
        if not record:
            return False

        required_fields = ["arxiv_id", "title", "abstract", "authors", "categories"]

        is_valid = all(f in record for f in required_fields)

        # update metrics (IMPORTANT for test)
        self.metrics.total_records += 1

        if is_valid:
            self.metrics.valid_records += 1

        if expected_id and record.get("arxiv_id") != expected_id:
            return False

        return is_valid

    def check_duplicates(self, data, key):
        seen = set()
        duplicates = set()

        for item in data:
            value = item.get(key)
            if value in seen:
                duplicates.add(value)
            else:
                seen.add(value)

        # test expects COUNT, not list
        return len(duplicates)


class DataQualityAlert:
    def __init__(self, critical_threshold=80):
        self.critical_threshold = critical_threshold

    def check_metrics(self, metrics: DataQualityMetrics):
        rate = metrics.get_validation_rate()

        return {
            "severity": "CRITICAL" if rate < self.critical_threshold else "OK",
            "alert": rate < self.critical_threshold,
            "rate": rate,
        }
