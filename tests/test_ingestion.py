import arxiv
from test_cassandra import CassandraConnection      
import uuid
import json
from datetime import datetime


# 1️⃣ Connect to Cassandra
session = conn.session

if session is None:
    import pytest
    pytest.skip("Cassandra not available in CI")

session.set_keyspace("arxiv")

# 2️⃣ Prepare arXiv query
search = arxiv.Search(
    query="machine learning",
    max_results=5,
    sort_by=arxiv.SortCriterion.SubmittedDate
)

# 3️⃣ Prepare batch
batch_id = uuid.uuid4()

insert_statement = session.prepare("""
    INSERT INTO papers_raw (
        batch_id, arxiv_id, title, abstract, authors,
        categories, primary_category, published_date, updated_date,
        pdf_url, raw_json, ingested_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""")

# 4️⃣ Fetch papers and insert
import arxiv

client = arxiv.Client()

search = arxiv.Search(
    query="machine learning",
    max_results=5,
    sort_by=arxiv.SortCriterion.SubmittedDate
)

for result in client.results(search):
    print(result.title)
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
        "raw_json": json.dumps(result._raw),
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

print(f"Ingested batch {batch_id} successfully!")

conn.disconnect()
