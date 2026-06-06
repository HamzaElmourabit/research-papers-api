class DataQualityValidator:
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.metrics = DataQualityMetrics(batch_id=batch_id)

    def validate_record(self, record, record_id):
        self.metrics.total_records += 1

        required_fields = [
            "arxiv_id",
            "title",
            "abstract",
            "authors",
        ]

        for field in required_fields:
            if field not in record:
                self.metrics.rejected_records += 1
                return False

        self.metrics.valid_records += 1
        return True

    def check_duplicates(self, records, id_field="arxiv_id"):
        seen = set()
        duplicates = 0

        for record in records:
            rid = record.get(id_field)

            if rid in seen:
                duplicates += 1
                self.metrics.duplicate_records += 1
            else:
                seen.add(rid)

        return duplicates

    def get_summary(self):
        return {
            "batch_id": self.batch_id,
            "metrics": self.metrics.to_dict(),
        }
