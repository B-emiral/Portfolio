# ./orchestration/dagster/sensors.py
from pathlib import Path

from dagster import RunRequest, sensor

from .jobs import ingest_new_documents_job


@sensor(job=ingest_new_documents_job, required_resource_keys={"settings"})
def new_files_sensor(context):
    settings = context.resources.settings
    watch_dirs = [Path(d) for d in settings["watch"]["dirs"]]
    for watch_dir in watch_dirs:
        for file in watch_dir.glob(settings["watch"]["glob"]):
            yield RunRequest(
                run_key=str(file),
                run_config={
                    "ops": {
                        "ingest_new_documents_graph": {
                            "ops": {
                                "ingest_add_document_op": {
                                    "inputs": {"json_path": {"value": str(file)}}
                                }
                            }
                        }
                    }
                },
            )
