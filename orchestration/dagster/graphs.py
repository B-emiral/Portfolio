# ./orchestration/dagster/graphs.py
from dagster import graph

from .ops import (
    analyse_new_sentences_sentiment_and_persist_op,
    ingest_add_document_op,
    split_sentences_and_persist_op,
)


@graph
def ingest_new_documents_graph():
    ingest_add_document_op()


@graph
def split_new_docs_into_sentences_and_persist_graph():
    split_sentences_and_persist_op()


@graph
def analyse_new_sentences_sentiment_graph():
    # CHECK: must be async
    analyse_new_sentences_sentiment_and_persist_op()
