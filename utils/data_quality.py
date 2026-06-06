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

    # ✅ REQUIRED by tests
    def get_validation_rate(self):
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    def validation_rate(self):
        return self.get_validation_rate()

    # ✅ REQUIRED by tests
    def get_quality_level(self):
        rate = self.get_validation_rate()

        if rate < 80:
            return QualityLevel.CRITICAL
        elif rate < 95:
            return QualityLevel.WARNING
        else:
            return QualityLevel.GOOD


class DataQualityValidator:
    def __init__(self, name):
        self.name = name
        self.seen_ids = set()

    # ✅ REQUIRED by tests
    def validate_record(self, record, expected_id=None):
        if not record:
            return False

        required_fields = ["arxiv_id", "title", "abstract", "authors", "categories"]

        for f in required_fields:
            if f not in record:
                return False

        if expected_id and record.get("arxiv_id") != expected_id:
            return False

        return True

    # (compat alias)
    def validate(self, record, expected_id=None):
        return self.validate_record(record, expected_id)

    # ✅ REQUIRED by tests
    def check_duplicates(self, data, key):
        seen = set()
        duplicates = []

        for item in data:
            value = item.get(key)
            if value in seen:
                duplicates.append(value)
            else:
                seen.add(value)

        return duplicates


class DataQualityAlert:
    def __init__(self, critical_threshold=80):
        self.critical_threshold = critical_threshold

    # ✅ REQUIRED by tests
    def check_metrics(self, metrics: DataQualityMetrics):
        rate = metrics.get_validation_rate()

        if rate < self.critical_threshold:
            return {
                "severity": "CRITICAL",
                "alert": True,
                "rate": rate,
            }

        return {
            "severity": "OK",
            "alert": False,
            "rate": rate,
        }
