from backend.app.services.task_registry import TASKS


def get_supported_tasks():
    return {"tasks": TASKS}
