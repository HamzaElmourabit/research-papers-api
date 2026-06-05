import arxiv
import uuid
import json
import pytest
from datetime import datetime
from test_cassandra import CassandraConnection


def test_arxiv_ingestion_pipeline():
    conn = CassandraConnection()
    conn.connect()
    session = conn.session

    if session is None:
        pytest.skip("Cassandra not available")

    KEYSPACE = "arxiv"

    # CREATE KEYSPACE SAFE
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
    """)

    session.set_keyspace(KEYSPACE)

    # CREATE TABLE SAFE
    session.execute("""
    CREATE TABLE IF NOT EXISTS papers_raw (
        batch_id uuid,
        arxiv_id text PRIMARY KEY,
        title text,
        abstract text,
        authors list<text>,
        categories list<text>,
        primary_category text,
        published_date timestamp,
        updated_date timestamp,
        pdf_url text,
        raw_json text,
        ingested_at timestamp
    )
    """)

    batch_id = uuid.uuid4()

    insert_stmt = session.prepare("""
        INSERT INTO papers_raw (
            batch_id, arxiv_id, title, abstract, authors,
            categories, primary_category, published_date,
            updated_date, pdf_url, raw_json, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    client = arxiv.Client()

    search = arxiv.Search(
        query="machine learning",
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    count = 0

    for result in client.results(search):
        session.execute(insert_stmt, (
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
        count += 1

    assert count > 0

    conn.disconnect()
