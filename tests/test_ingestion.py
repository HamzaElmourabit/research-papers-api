import pytest
import arxiv
import uuid
import json
from datetime import datetime
from test_cassandra import CassandraConnection


def test_arxiv_ingestion_pipeline():
    conn = CassandraConnection()
    conn.connect()
    session = conn.session

    if session is None:
        pytest.skip("Cassandra not available")

    try:
        session.set_keyspace("arxiv")
    except Exception:
        pytest.skip("Keyspace arxiv not available in CI")

    search = arxiv.Search(
        query="machine learning",
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    batch_id = uuid.uuid4()

    insert = session.prepare("""
        INSERT INTO papers_raw (
            batch_id, arxiv_id, title, abstract, authors,
            categories, primary_category, published_date, updated_date,
            pdf_url, raw_json, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    for result in search.results():
        session.execute(insert, (
            batch_id,
            result.entry_id.split("/")[-1],
            result.title,
            result.summary,
            [a.name for a in result.authors],
            result.categories,
            result.primary_category,
            result.published,
            result.updated,
            result.pdf_url,
            json.dumps(result._raw),
            datetime.utcnow()
        ))

    conn.disconnect()
