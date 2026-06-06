"""
Data Quality Monitoring Module
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    GOOD = "GOOD"


@dataclass
class DataQualityMetrics:
    batch_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    total_records: int = 0
    valid_records: int = 0
    rejected_records: int = 0

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

        if rate < 80:
            return QualityLevel.CRITICAL
        elif rate < 95:
            return QualityLevel.WARNING
        return QualityLevel.GOOD

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["validation_rate"] = self.get_validation_rate()
        data["quality_level"] = self.get_quality_level().value
        return data


class DataQualityValidator:
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.metrics = DataQualityMetrics(batch_id=batch_id)
        self.errors: List[Dict[str, Any]] = []

    def validate_record(self, record: Dict[str, Any], record_id: str) -> bool:
        self.metrics.total_records += 1

        required_fields = ["arxiv_id", "title", "abstract", "authors"]

        try:
            for f in required_fields:
                if f not in record or not record[f]:
                    self.metrics.rejected_records += 1
                    return False

            if not isinstance(record.get("authors"), list):
                self.metrics.invalid_fields["authors"] = 1
                self.metrics.rejected_records += 1
                return False

            self.metrics.valid_records += 1
            return True

        except Exception as e:
            self.metrics.rejected_records += 1
            self.errors.append({"id": record_id, "error": str(e)})
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


class DataQualityAlert:
    def __init__(self, critical_threshold=80, warning_threshold=95, duplicate_threshold=5):
        self.critical_threshold = critical_threshold
        self.warning_threshold = warning_threshold
        self.duplicate_threshold = duplicate_threshold

    def check_metrics(self, metrics: DataQualityMetrics) -> Optional[Dict[str, Any]]:
        rate = metrics.get_validation_rate()

        if rate < self.critical_threshold:
            return {
                "severity": "CRITICAL",
                "batch_id": metrics.batch_id,
                "validation_rate": rate,
            }

        if rate < self.warning_threshold:
            return {
                "severity": "WARNING",
                "batch_id": metrics.batch_id,
                "validation_rate": rate,
            }

        if metrics.duplicate_records > self.duplicate_threshold:
            return {
                "severity": "WARNING",
                "batch_id": metrics.batch_id,
                "duplicates": metrics.duplicate_records,
            }

        return None
