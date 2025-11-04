# ./orchestration/dagster/__init__.py
from dagster import Definitions

from .config_loader import load_settings
from .graphs import *  # noqa: F403
from .jobs import (
    analyse_new_sentences_sentiment_job,
    ingest_new_documents_job,
    scraping_data_job,
    scraping_meta_job,
    split_new_docs_into_sentences_and_persist_job,
)
from .ops import *  # noqa: F403
from .schedules import *  # noqa: F403
from .sensors import (
    analyse_new_sentences_sentiment_sensor,
    ingest_new_documents_sensor,
    split_new_docs_into_sentences_and_persist_sensor,
)

# DAGster uses these defs implicitly
# ```
# if hasattr(module, "defs"):
#     return module.defs
# ```
defs = Definitions(
    jobs=[
        ingest_new_documents_job,
        split_new_docs_into_sentences_and_persist_job,
        analyse_new_sentences_sentiment_job,
        scraping_meta_job,
        scraping_data_job,
    ],  # noqa: F405
    schedules=[analyse_new_sentences_sentiment_schedule],  # noqa: F405
    sensors=[
        ingest_new_documents_sensor,
        split_new_docs_into_sentences_and_persist_sensor,
        analyse_new_sentences_sentiment_sensor,
    ],
    # context.resources.settings
    resources={"settings": load_settings()},
)
