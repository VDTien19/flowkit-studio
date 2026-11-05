"""Compatibility session interface: never rotates or creates Google projects."""
from agent.services.automation_policy import flow_target, PolicyError


def current_session_project() -> dict:
    try:
        pid = flow_target()
        return {"project_id": pid, "active": True, "pinned": True}
    except PolicyError as exc:
        return {"project_id": None, "active": False, "pinned": True, "error": str(exc)}


def touch_session_project(project_id: str) -> None:
    flow_target(project_id)


async def ensure_session_project(client, *, title=None, force_new=False) -> dict:
    if force_new:
        raise PolicyError("FLOW_PROJECT_CREATION_DISABLED")
    flow_target()
    return current_session_project()
