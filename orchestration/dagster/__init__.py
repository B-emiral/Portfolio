# ./orchestration/dagster/__init__.py
from dagster import Definitions

from .config_loader import load_settings
from .graphs import *  # noqa: F403
from .jobs import *  # noqa: F403
from .ops import *  # noqa: F403
from .schedules import *  # noqa: F403
from .sensors import *  # noqa: F403

# DAGster uses these defs implicitly
# ```
# if hasattr(module, "defs"):
#     return module.defs
# ```
defs = Definitions(
    jobs=[ingest_new_documents_job, process_new_documents_job],  # noqa: F405
    schedules=[document_check_schedule],  # noqa: F405
    sensors=[new_files_sensor],  # noqa: F405
    # context.resources.settings
    resources={"settings": load_settings()},
)
