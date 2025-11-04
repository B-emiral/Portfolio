# ./orchestration/dagster/schedules.py
from orchestration.dagster.jobs import analyse_new_sentences_sentiment_job

from dagster import schedule

from .config_loader import load_settings

# static loading is fine here since schedules are not dynamic
SETTINGS = load_settings()


@schedule(
    job=analyse_new_sentences_sentiment_job,
    cron_schedule=SETTINGS["schedules"]["check_documents_interval"],
)
def analyse_new_sentences_sentiment_schedule(_context):
    return {}
