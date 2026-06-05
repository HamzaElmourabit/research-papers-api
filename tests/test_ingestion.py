import pytest
import uuid
import json
from datetime import datetime

import arxiv
from test_cassandra import CassandraConnection


def test_arxiv_ingestion_pipeline():
    # =========================
    # 1. Cassandra connection
    # =========================
    conn = CassandraConnection()
    conn.connect()
    session = conn.session

    if session is None:
        pytest.skip("Cassandra not available in CI")

    session.set_keyspace("arxiv")

    # =========================
    # 2. Prepare arxiv search
    # =========================
    search = arxiv.Search(
        query="machine learning",
        max_results=5,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    client = arxiv.Client()

    # =========================
    # 3. Prepare batch
    # =========================
    batch_id = uuid.uuid4()

    insert_statement = session.prepare("""
        INSERT INTO papers_raw (
            batch_id, arxiv_id, title, abstract, authors,
            categories, primary_category, published_date, updated_date,
            pdf_url, raw_json, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    # =========================
    # 4. Fetch + insert
    # =========================
    count = 0

    for result in client.results(search):

        paper_json = {
            "arxiv_id": result.entry_id.split("/")[-1],
            "title": result.title,
            "abstract": result.summary,
            "authors": [a.name for a in result.authors],
            "categories": result.categories,
            "primary_category": result.primary_category,
            "published_date": result.published,
            "updated_date": result.updated,
            "pdf_url": result.pdf_url,
            "raw_json": json.dumps(getattr(result, "_raw", {})),
            "ingested_at": datetime.utcnow()
        }

        session.execute(insert_statement, (
            batch_id,
            paper_json["arxiv_id"],
            paper_json["title"],
            paper_json["abstract"],
            paper_json["authors"],
            paper_json["categories"],
            paper_json["primary_category"],
            paper_json["published_date"],
            paper_json["updated_date"],
            paper_json["pdf_url"],
            paper_json["raw_json"],
            paper_json["ingested_at"]
        ))

        count += 1

    assert count > 0
