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

    def validation_rate(self):
        if self.total_records == 0:
            return 0
        return self.valid_records / self.total_records

    def get_quality_level(self):
        rate = self.validation_rate()

        if rate < 0.8:
            return QualityLevel.CRITICAL
        elif rate < 0.95:
            return QualityLevel.WARNING
        else:
            return QualityLevel.GOOD


class DataQualityValidator:
    def __init__(self, name):
        self.name = name

    def validate(self, record):
        errors = []

        if record is None:
            errors.append("record_is_none")

        if isinstance(record, dict):
            if not record.get("id"):
                errors.append("missing_id")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
        }

    def detect_duplicates(self, records):
        seen = set()
        duplicates = []

        for r in records:
            rid = r.get("id")
            if rid in seen:
                duplicates.append(rid)
            else:
                seen.add(rid)

        return duplicates


class DataQualityAlert:
    def __init__(self, critical_threshold=80):
        self.critical_threshold = critical_threshold

    def check_metrics(self, metrics: DataQualityMetrics):
        rate = metrics.validation_rate() * 100

        if rate < self.critical_threshold:
            return {
                "alert": True,
                "level": "CRITICAL",
                "rate": rate,
            }

        return {
            "alert": False,
            "level": "OK",
            "rate": rate,
        }
