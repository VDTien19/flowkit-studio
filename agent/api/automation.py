"""Local plan storage; approval never dispatches generation by itself."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from agent.services import automation_policy as policy

router = APIRouter(prefix="/automation", tags=["automation"])


class PlanBody(BaseModel):
    plan: dict = Field(min_length=1)


class ApprovalBody(BaseModel):
    revision: str
    confirmation: str


def _call(fn, *args):
    try:
        return fn(*args)
    except policy.PolicyError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.put("/plans/{project_id}")
async def save(project_id: str, body: PlanBody):
    return _call(policy.save_plan, project_id, body.plan)


@router.get("/plans/{project_id}")
async def get(project_id: str):
    return _call(policy.get_plan, project_id)


@router.post("/plans/{project_id}/approve")
async def approve(project_id: str, body: ApprovalBody):
    return _call(policy.approve_plan, project_id, body.revision, body.confirmation)
