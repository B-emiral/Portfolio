# ./orchestration/dagster/graphs.py
from dagster import graph

from .ops import (
    analyse_sentiment_sentence_op,
    get_documents_without_sentences_op,
    ingest_add_document_op,
    split_sentences_op,
)


@graph
def ingest_new_documents_graph():
    ingest_add_document_op()


@graph
def process_new_documents_graph():
    documents = get_documents_without_sentences_op()
    sentences = split_sentences_op(documents)
    # TODO: must be async
    analyse_sentiment_sentence_op(sentences)
