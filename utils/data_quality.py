"""
Data Quality Monitoring Module
Provides metrics tracking, validation, and alerting
"""

import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    CRITICAL = "CRITICAL"  # < 80% valid
    WARNING = "WARNING"    # 80-95% valid
    GOOD = "GOOD"          # >= 95% valid


@dataclass
class DataQualityMetrics:
    batch_id: str
    total_records: int = 0
    valid_records: int = 0
    rejected_records: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    null_fields: Dict[str, int] = field(default_factory=dict)
    invalid_fields: Dict[str, int] = field(default_factory=dict)

    duplicate_records: int = 0
    duplicate_ids: List[str] = field(default_factory=list)

    errors: Dict[str, int] = field(default_factory=dict)

    def get_validation_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    def get_quality_level(self) -> QualityLevel:
        rate = self.get_validation_rate()

        # FIX IMPORTANT : bornes corrigées
        if rate <= 80:
            return QualityLevel.CRITICAL
        elif 80 < rate < 95:
            return QualityLevel.WARNING
        else:
            return QualityLevel.GOOD

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["validation_rate"] = self.get_validation_rate()
        data["quality_level"] = self.get_quality_level().value
        return data

    def log_summary(self):
        rate = self.get_validation_rate()
        quality = self.get_quality_level()

        logger.info(
            f"Data Quality Report - {self.batch_id}",
            extra={
                "batch_id": self.batch_id,
                "total": self.total_records,
                "valid": self.valid_records,
                "rejected": self.rejected_records,
                "validation_rate": f"{rate:.2f}%",
                "quality_level": quality.value,
                "duplicates": self.duplicate_records,
            },
        )

        if quality == QualityLevel.CRITICAL:
            logger.critical(
                f"Critical data quality issue in batch {self.batch_id}",
                extra={"validation_rate": rate, "threshold": 80},
            )
        elif quality == QualityLevel.WARNING:
            logger.warning(
                f"Data quality below target in batch {self.batch_id}",
                extra={"validation_rate": rate, "target": 95},
            )


class DataQualityValidator:
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.metrics = DataQualityMetrics(batch_id=batch_id)
        self.validation_errors: List[Dict[str, Any]] = []

    def validate_record(self, record: Dict[str, Any], record_id: str) -> bool:
        self.metrics.total_records += 1

        required_fields = ["arxiv_id", "title", "abstract", "authors"]

        for field in required_fields:
            if field not in record or record[field] is None:
                self.metrics.null_fields[field] = (
                    self.metrics.null_fields.get(field, 0) + 1
                )
                return self._error(record_id, f"Missing field: {field}")

        if not isinstance(record.get("authors"), list) or len(record["authors"]) == 0:
            self.metrics.invalid_fields["authors"] = (
                self.metrics.invalid_fields.get("authors", 0) + 1
            )
            return self._error(record_id, "Authors must be non-empty list")

        self.metrics.valid_records += 1
        return True

    def _error(self, record_id: str, msg: str) -> bool:
        self.metrics.rejected_records += 1
        self.validation_errors.append(
            {
                "record_id": record_id,
                "error": msg,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self.metrics.errors[msg] = self.metrics.errors.get(msg, 0) + 1
        return False

    def check_duplicates(self, records: List[Dict[str, Any]], id_field="arxiv_id") -> int:
        seen = set()
        duplicates = 0

        for r in records:
            rid = r.get(id_field)
            if rid in seen:
                duplicates += 1
                self.metrics.duplicate_records += 1
                self.metrics.duplicate_ids.append(rid)
            else:
                seen.add(rid)

        return duplicates

    def get_summary(self):
        return {
            "batch_id": self.batch_id,
            "metrics": self.metrics.to_dict(),
            "errors": self.validation_errors[:10],
        }


class DataQualityAlert:
    def __init__(self, critical=80, warning=95, dup_threshold=5):
        self.critical_threshold = critical
        self.warning_threshold = warning
        self.duplicate_threshold = dup_threshold

    def check_metrics(self, metrics: DataQualityMetrics):
        rate = metrics.get_validation_rate()

        if rate <= self.critical_threshold:
            return {
                "severity": "CRITICAL",
                "rate": rate,
                "batch_id": metrics.batch_id,
            }

        if rate < self.warning_threshold:
            return {
                "severity": "WARNING",
                "rate": rate,
                "batch_id": metrics.batch_id,
            }

        if metrics.duplicate_records > self.duplicate_threshold:
            return {
                "severity": "WARNING",
                "reason": "duplicates",
                "count": metrics.duplicate_records,
            }

        return None
