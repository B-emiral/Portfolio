# ./orchestration/dagster/jobs.py
from dagster import job

from .graphs import ingest_new_documents_graph, process_new_documents_graph


@job
def ingest_new_documents_job():
    ingest_new_documents_graph()


@job
def process_new_documents_job():
    process_new_documents_graph()
