from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any


class QualityLevel(Enum):
    GOOD = "GOOD"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class DataQualityMetrics:
    batch_id: str
    timestamp: int
    total_records: int
    valid_records: int = 0
    rejected_records: int = 0
    null_fields: Dict[str, int] = field(default_factory=dict)
    invalid_fields: Dict[str, int] = field(default_factory=dict)
    duplicate_records: int = 0
    duplicate_ids: List[str] = field(default_factory=list)
    errors: Dict[str, Any] = field(default_factory=dict)

    def validation_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return self.valid_records / self.total_records

    def get_quality_level(self) -> QualityLevel:
        rate = self.validation_rate()

        if rate >= 0.9:
            return QualityLevel.GOOD
        elif rate >= 0.75:
            return QualityLevel.WARNING
        else:
            return QualityLevel.CRITICAL


class DataQualityAlert:
    def __init__(self, critical_threshold: float = 80):
        self.critical_threshold = critical_threshold
        self.alerts = []

    def check(self, metrics: DataQualityMetrics) -> bool:
        rate = metrics.validation_rate() * 100
        if rate < self.critical_threshold:
            self.alerts.append(
                {
                    "batch_id": metrics.batch_id,
                    "level": "CRITICAL",
                    "rate": rate,
                }
            )
            return True
        return False
