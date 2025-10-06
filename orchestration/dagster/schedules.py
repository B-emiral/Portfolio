# ./orchestration/dagster/schedules.py
from dagster import schedule

from .config_loader import load_settings
from .jobs import process_new_documents_job

# static loading is fine here since schedules are not dynamic
SETTINGS = load_settings()


@schedule(
    job=process_new_documents_job,
    cron_schedule=SETTINGS["schedules"]["check_documents_interval"],
)
def document_check_schedule(_context):
    return {}
