"""
Data Quality Monitoring Module
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any
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
    timestamp: float | None = None

    total_records: int = 0
    valid_records: int = 0
    rejected_records: int = 0

    null_fields: Dict[str, int] = field(default_factory=dict)
    invalid_fields: Dict[str, int] = field(default_factory=dict)

    duplicate_records: int = 0
    duplicate_ids: List[str] = field(default_factory=list)

    errors: Dict[str, Any] = field(default_factory=dict)

    def get_validation_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    def get_quality_level(self) -> QualityLevel:
        rate = self.get_validation_rate()

        # ✅ FIX IMPORTANT (corrige ton test)
        if rate <= 80:
            return QualityLevel.CRITICAL
        elif rate <= 95:
            return QualityLevel.WARNING
        else:
            return QualityLevel.GOOD

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["validation_rate"] = self.get_validation_rate()
        d["quality_level"] = self.get_quality_level().value
        return d
