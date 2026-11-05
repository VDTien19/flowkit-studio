"""No-network regression coverage for destination pinning and approval gates."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent import config
from agent.api import automation, requests, projects, flow
from agent.services import automation_policy as policy, flow_batch as fb
from agent.services.flow_client import FlowClient
from agent.services import flow_project_session as session
from agent.sdk.services.flow_provider import FlowProvider
from agent.sdk.services.provider_base import ProviderJob, KIND_IMAGE

PID = "b29b7ca7-17c0-4bde-ade8-c7f458bc2625"
OTHER = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "FLOW_PROJECT_ID", PID)
    token = policy.approved_project.set(None)
    yield
    policy.approved_project.reset(token)


def approve(pid=OTHER):
    plan = policy.save_plan(pid, {"story": "fiction", "scenes": 2, "retry_limit": 2})
    policy.approve_plan(pid, plan["revision"], "DUYỆT")


def test_plan_revision_and_restart_persistence():
    plan = policy.save_plan(OTHER, {"scenes": 2})
    with pytest.raises(policy.PolicyError):
        policy.require_approval(OTHER)
    with pytest.raises(policy.PolicyError):
        policy.approve_plan(OTHER, plan["revision"], "continue")
    policy.approve_plan(OTHER, plan["revision"], "DUYỆT")
    policy.require_approval(OTHER)  # a fresh database connection, no memory cache
    policy.save_plan(OTHER, {"scenes": 3})
    with pytest.raises(policy.PolicyError):
        policy.approve_plan(OTHER, plan["revision"], "DUYỆT")
    with pytest.raises(policy.PolicyError):
        policy.require_approval(OTHER)


@pytest.mark.parametrize("builder,rpc", [
    (lambda p: fb.image_request("action", p), fb.RPC_GEN_IMAGE),
    (lambda p: fb.video_request("action", p, OTHER), fb.RPC_GEN_VIDEO),
    (lambda p: fb.text_video_request("action", p), fb.RPC_GEN_VIDEO_TEXT),
    (lambda p: fb.omni_first_frame_request("action", p, OTHER), fb.RPC_GEN_VIDEO),
    (lambda p: fb.omni_first_last_request("action", p, OTHER, OTHER), fb.RPC_GEN_VIDEO_FIRST_LAST),
    (lambda p: fb.omni_reference_video_request("action", p, [OTHER]), fb.RPC_GEN_VIDEO_REFERENCES),
    (lambda p: fb.upload_request("bytes", p), fb.RPC_UPLOAD_IMAGE),
    (fb.project_media_request, fb.RPC_PROJECT_MEDIA),
    (lambda p: fb.stream_chat_request("action", p), "StreamChat"),
])
def test_wire_destination(builder, rpc):
    approve()
    token = policy.approved_project.set(OTHER)
    try:
        policy.validate_rpc(rpc, builder(PID))
        with pytest.raises(policy.PolicyError, match="MISMATCH"):
            policy.validate_rpc(rpc, builder(OTHER))
        with pytest.raises(policy.PolicyError):
            policy.validate_rpc(rpc, builder(""))
    finally:
        policy.approved_project.reset(token)


async def test_raw_rpc_cannot_create_or_generate_before_approval(monkeypatch):
    client = FlowClient()
    send = AsyncMock()
    monkeypatch.setattr(client, "_send", send)
    created = await client.create_project("Never create")
    raw_create = await client.batch_rpc(fb.RPC_CREATE_PROJECT, fb.create_project_request("No"))
    raw_image = await client.batch_rpc(fb.RPC_GEN_IMAGE, fb.image_request("action", PID))
    assert all(r["status"] == 409 for r in (created, raw_create, raw_image))
    send.assert_not_called()


async def test_transport_rejects_spoofed_rpc_and_wrong_target():
    client = FlowClient()
    result = await client._send("batch_rpc", {
        "rpcid": fb.RPC_PROJECT_MEDIA,
        "freq": fb.create_project_request("disguised create"),
    })
    assert result["status"] == 409
    assert "ENVELOPE_MISMATCH" in result["error"]
    result = await client._send("batch_rpc", {
        "rpcid": fb.RPC_PROJECT_MEDIA,
        "freq": fb.project_media_request(OTHER),
    })
    assert result["status"] == 409
    assert "PROJECT_MISMATCH" in result["error"]


async def test_provider_maps_local_id_and_rejects_override(monkeypatch):
    approve()
    provider = FlowProvider(MagicMock())
    run = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(provider, "_run_approved", run)
    job = ProviderJob(job_id="job", kind=KIND_IMAGE, extra={"project_id": OTHER})
    assert await provider.run(job) == {"ok": True}
    assert run.call_args.args[0].extra["project_id"] == PID
    assert job.extra["project_id"] == OTHER
    job.extra["flow_project_id"] = OTHER
    assert (await provider.run(job))["status"] == 409
    assert run.await_count == 1


async def test_local_projects_never_call_google(monkeypatch):
    client = MagicMock(connected=True)
    client.create_project = AsyncMock()
    repo = MagicMock()
    repo.create_project = AsyncMock(side_effect=lambda **kw: kw)
    monkeypatch.setattr(projects, "get_flow_client", lambda: client)
    monkeypatch.setattr(projects, "_get_repo", lambda: repo)
    from agent.models.project import ProjectCreate
    a = await projects.create(ProjectCreate(name="Film A"))
    b = await projects.create(ProjectCreate(name="Film B", flow_project_id=PID))
    assert a["id"] != b["id"] and a["id"] != PID
    client.create_project.assert_not_called()
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await projects.create(ProjectCreate(name="Invalid", flow_project_id=OTHER))
    assert exc.value.status_code == 409


async def test_session_never_rotates_or_creates():
    client = MagicMock()
    assert (await session.ensure_session_project(client))["project_id"] == PID
    with pytest.raises(policy.PolicyError):
        await session.ensure_session_project(client, force_new=True)
    client.create_project.assert_not_called()
    assert await flow._resolve_direct_project(client, "") == PID


def test_bad_environment_fails_closed(monkeypatch):
    monkeypatch.setattr(config, "FLOW_PROJECT_ID", "invalid-uuid")
    with pytest.raises(policy.PolicyError):
        policy.flow_target(PID)
    assert session.current_session_project()["active"] is False


def test_api_batch_blocks_before_any_mutation(monkeypatch):
    app = FastAPI()
    app.include_router(automation.router, prefix="/api")
    app.include_router(requests.router, prefix="/api")
    client = TestClient(app)
    mutate = AsyncMock()
    monkeypatch.setattr(requests.crud, "create_request", mutate)
    item = {"type": "GENERATE_CHARACTER_IMAGE", "project_id": OTHER, "character_id": OTHER}
    assert client.post("/api/requests/batch", json={"requests": [item]}).status_code == 409
    plan = client.put(f"/api/automation/plans/{OTHER}", json={"plan": {"scenes": 2}}).json()
    assert client.post(f"/api/automation/plans/{OTHER}/approve", json={"revision": plan["revision"], "confirmation": "DUYỆT"}).status_code == 200
    mutate.assert_not_called()  # approving a plan itself never dispatches media


async def test_worker_checks_approval_before_operations(monkeypatch):
    from agent.worker.processor import _dispatch
    from agent.sdk.services import operations
    get_ops = MagicMock()
    monkeypatch.setattr(operations, "get_operations", get_ops)
    result = await _dispatch({"id": OTHER, "project_id": OTHER, "type": "GENERATE_IMAGE"}, "VERTICAL")
    assert result["status"] == 409
    get_ops.assert_not_called()
