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
    CRITICAL = "CRITICAL"  # < 80%
    WARNING = "WARNING"    # 80–95%
    GOOD = "GOOD"          # >= 95%


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
        if self.total_records <= 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    def get_quality_level(self) -> QualityLevel:
        rate = self.get_validation_rate()

        if self.total_records == 0:
            return QualityLevel.CRITICAL

        if rate < 80:
            return QualityLevel.CRITICAL
        elif rate < 95:
            return QualityLevel.WARNING
        else:
            return QualityLevel.GOOD

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        d["validation_rate"] = self.get_validation_rate()
        d["quality_level"] = self.get_quality_level().value
        return d


class DataQualityValidator:
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.metrics = DataQualityMetrics(batch_id=batch_id)
        self.validation_errors = []

    def validate_record(self, record: Dict[str, Any], record_id: str) -> bool:
        self.metrics.total_records += 1

        required_fields = ["arxiv_id", "title", "abstract", "authors"]

        for field in required_fields:
            if field not in record or not record[field]:
                self.metrics.rejected_records += 1
                return False

        if not isinstance(record.get("authors"), list):
            self.metrics.rejected_records += 1
            return False

        self.metrics.valid_records += 1
        return True

    def check_duplicates(self, records, id_field="arxiv_id") -> int:
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
    def __init__(self, critical_threshold=80, warning_threshold=95):
        self.critical_threshold = critical_threshold
        self.warning_threshold = warning_threshold

    def check_metrics(self, metrics: DataQualityMetrics) -> Optional[Dict]:
        rate = metrics.get_validation_rate()

        if rate < self.critical_threshold:
            return {
                "severity": "CRITICAL",
                "batch_id": metrics.batch_id,
                "validation_rate": rate
            }

        if rate < self.warning_threshold:
            return {
                "severity": "WARNING",
                "batch_id": metrics.batch_id,
                "validation_rate": rate
            }

        return None
