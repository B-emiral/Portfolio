# ./orchestration/dagster/jobs.py
from dagster import job

from .graphs import (
    analyse_new_sentences_sentiment_graph,
    ingest_new_documents_graph,
    scraping_raw_graph,
    split_new_docs_into_sentences_and_persist_graph,
)


@job
def ingest_new_documents_job():
    ingest_new_documents_graph()


@job
def split_new_docs_into_sentences_and_persist_job():
    split_new_docs_into_sentences_and_persist_graph()


@job
def analyse_new_sentences_sentiment_job():
    analyse_new_sentences_sentiment_graph()


###

scraping_meta_job = scraping_raw_graph.to_job(
    name="scraping_meta_job",
    config={
        "ops": {
            "get_unscraped_colls_op": {"config": {"field_name": "coll_meta_raw"}},
            "scraping_op": {"config": {"field_name": "coll_meta_raw"}},
        }
    },
)

scraping_data_job = scraping_raw_graph.to_job(
    name="scraping_data_job",
    config={
        "ops": {
            "get_unscraped_colls_op": {"config": {"field_name": "coll_data_raw"}},
            "scraping_op": {"config": {"field_name": "coll_data_raw"}},
        }
    },
)
