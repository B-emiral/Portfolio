# ./orchestration/dagster/graphs.py
from dagster import graph

from .ops import (
    analyze_sentences_op,
    get_unprocessed_documents_op,
    ingest_add_document_op,
    split_sentences_op,
)


@graph
def ingest_new_documents_graph():
    ingest_add_document_op()


@graph
def process_new_documents_graph():
    documents = get_unprocessed_documents_op()
    sentences = split_sentences_op(documents)
    analyze_sentences_op(sentences)
