from enum import Enum
from collections import defaultdict


# =========================
# ENUM QUALITY LEVEL
# =========================
class QualityLevel(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    GOOD = "GOOD"


# =========================
# DATA QUALITY METRICS
# =========================
class DataQualityMetrics:
    def __init__(
        self,
        batch_id,
        total_records,
        valid_records,
        timestamp=None,
        rejected_records=0,
        null_fields=None,
        invalid_fields=None,
        duplicate_records=0,
        duplicate_ids=None,
        errors=None
    ):
        self.batch_id = batch_id
        self.total_records = total_records
        self.valid_records = valid_records
        self.timestamp = timestamp
        self.rejected_records = rejected_records
        self.null_fields = null_fields or {}
        self.invalid_fields = invalid_fields or {}
        self.duplicate_records = duplicate_records
        self.duplicate_ids = duplicate_ids or []
        self.errors = errors or {}

    # -------------------------
    # VALIDATION RATE
    # -------------------------
    def get_validation_rate(self):
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    # -------------------------
    # QUALITY LEVEL LOGIC
    # -------------------------
    def get_quality_level(self):
        rate = self.get_validation_rate()

        if rate < 80:
            return QualityLevel.CRITICAL
        elif rate <= 90:  # CORRIGÉ : Inclut maintenant la valeur 90 pile
            return QualityLevel.WARNING
        else:
            return QualityLevel.GOOD


# =========================
# DATA QUALITY VALIDATOR
# =========================
class DataQualityValidator:
    def __init__(self, name):
        self.name = name
        self.metrics = DataQualityMetrics(
            batch_id=name,
            total_records=0,
            valid_records=0
        )
        self._seen_ids = set()

    # -------------------------
    # VALIDATE SINGLE RECORD
    # -------------------------
    def validate_record(self, record, record_id):
        self.metrics.total_records += 1

        required_fields = ["arxiv_id", "title", "abstract", "authors", "categories"]

        # check missing fields
        for field in required_fields:
            if field not in record or record[field] is None:
                return False

        # valid record
        self.metrics.valid_records += 1
        return True

    # -------------------------
    # DUPLICATES CHECK
    # -------------------------
    def check_duplicates(self, data, key):
        seen = set()
        duplicates = []

        for item in data:
            value = item.get(key)
            if value in seen:
                duplicates.append(value)
            else:
                seen.add(value)

        self.metrics.duplicate_ids = duplicates
        self.metrics.duplicate_records = len(duplicates)

        return len(duplicates)


# =========================
# ALERT SYSTEM
# =========================
class DataQualityAlert:
    def __init__(self, critical_threshold=80):
        self.critical_threshold = critical_threshold

    def check_metrics(self, metrics: DataQualityMetrics):
        rate = metrics.get_validation_rate()

        if rate < self.critical_threshold:
            return {
                "severity": "CRITICAL",
                "message": f"Validation rate too low: {rate:.2f}%",
                "batch_id": metrics.batch_id
            }

        return {
            "severity": "OK",
            "message": f"Validation rate acceptable: {rate:.2f}%",
            "batch_id": metrics.batch_id
        }
