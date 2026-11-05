"""Destination and legacy-identity regressions; all transport calls are mocked."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from agent.api import flow, projects
from agent.db import crud
from agent.db.schema import get_db
from agent.models.project import ProjectCreate
from agent.sdk.services.flow_provider import FlowProvider
from agent.sdk.services.provider_base import ProviderJob
from agent.services import automation_policy as policy, flow_batch as fb
from agent.services import flow_project_session as session, omni_flash
from agent.services.flow_client import FlowClient

PIN = "b29b7ca7-17c0-4bde-ade8-c7f458bc2625"
LOCAL = "940aa3e2-eab1-456c-9418-acf9c7556b11"
MEDIA = "11111111-2222-3333-4444-555555555555"


async def test_many_local_films_preserve_legacy_graph(test_db, monkeypatch):
    # Older databases used a Google UUID as a local PK. Never rewrite that PK.
    await crud.create_project(id=PIN, name="Legacy film", material="3d_pixar")
    video = await crud.create_video(PIN, "Legacy video", orientation="VERTICAL")
    scene = await crud.create_scene(video["id"], 1, "Existing scene")
    char = await crud.create_character("Existing cat", media_id=MEDIA)
    await crud.link_character_to_project(PIN, char["id"])
    request = await crud.create_request("GENERATE_IMAGE", project_id=PIN,
                                        video_id=video["id"], scene_id=scene["id"])
    await crud.update_request(request["id"], status="COMPLETED", media_id=MEDIA)

    async def graph():
        return (await crud.get_project(PIN), await crud.get_video(video["id"]),
                await crud.get_scene(scene["id"]), await crud.get_character(char["id"]),
                await crud.get_request(request["id"]), await crud.get_project_characters(PIN))

    before = await graph()
    # Creating local records must not even obtain a Google client.
    getter = MagicMock(side_effect=AssertionError("Unexpected Google client"))
    monkeypatch.setattr(projects, "get_flow_client", getter)
    first = await projects.create(ProjectCreate(name="Film A", material="3d_pixar"))
    second = await projects.create(ProjectCreate(name="Film B", flow_project_id=PIN))
    assert len({first.id, second.id, PIN}) == 3
    assert policy.flow_target() == PIN
    assert await graph() == before
    db = await get_db()
    assert await (await db.execute("PRAGMA foreign_key_check")).fetchall() == []
    pk = await (await db.execute("PRAGMA table_info(project)")).fetchall()
    assert [(r[1], r[5]) for r in pk if r[5]] == [("id", 1)]
    getter.assert_not_called()


@pytest.mark.parametrize("kind", ["image", "edit_image", "video", "video_refs", "upscale"])
async def test_all_provider_kinds_share_google_target(kind, monkeypatch):
    provider = FlowProvider(MagicMock())
    run = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(provider, "_run_approved", run)
    for local_id in (LOCAL, MEDIA):
        plan = policy.save_plan(local_id, {"film": local_id})
        policy.approve_plan(local_id, plan["revision"], "DUYỆT")
        job = ProviderJob(job_id=local_id, kind=kind, extra={"project_id": local_id})
        assert await provider.run(job) == {"ok": True}
        assert run.call_args.args[0].extra["project_id"] == PIN
        assert job.extra["project_id"] == local_id


@pytest.mark.parametrize("method", ["image", "video", "edit", "upload", "upscale", "omni_text", "omni_first", "omni_last", "omni_refs"])
@pytest.mark.parametrize("target", [PIN, MEDIA])
async def test_high_level_media_checks_before_transport(method, target, monkeypatch, approved_test_plan):
    client = FlowClient()
    # Capture, then terminate locally; never contact the browser or Google.
    send = AsyncMock(return_value={"error": "TEST_TRANSPORT_STOP"})
    monkeypatch.setattr(client, "_send", send)
    monkeypatch.setattr(omni_flash, "get_flow_client", lambda: client)
    if method == "image":
        result = await client.generate_images("Action", target)
    elif method == "video":
        result = await client.generate_video(MEDIA, "Action", target, "scene")
    elif method == "edit":
        result = await client.edit_image("Action", MEDIA, target)
    elif method == "upload":
        result = await client.upload_image("bytes", project_id=target)
    elif method == "upscale":
        result = await client.upscale_image(MEDIA, target)
    elif method == "omni_text":
        result = await omni_flash.generate_omni_flash_text_video(prompt="Action", project_id=target)
    elif method == "omni_first":
        result = await omni_flash.generate_omni_flash_first_frame_video(prompt="Action", project_id=target, start_image_media_id=MEDIA, scene_id="scene")
    elif method == "omni_last":
        result = await omni_flash.generate_omni_flash_first_last_video(prompt="Action", project_id=target, start_image_media_id=MEDIA, end_image_media_id=MEDIA, scene_id="scene")
    else:
        result = await omni_flash.generate_omni_flash_video(prompt="Action", project_id=target, reference_media_ids=[MEDIA], scene_id="scene")
    if target != PIN:
        assert "FLOW_PROJECT_MISMATCH" in str(result)
        send.assert_not_called()
    else:
        send.assert_awaited_once()
        params = send.call_args.args[1]
        policy.validate_rpc(params["rpcid"], params["freq"])


@pytest.mark.parametrize("method", ["edit", "upscale"])
async def test_direct_api_rejects_override_before_client(method, monkeypatch):
    client = MagicMock(connected=True)
    monkeypatch.setattr(flow, "get_flow_client", lambda: client)
    with pytest.raises(HTTPException) as exc:
        if method == "edit":
            await flow.edit_image(flow.EditImageRequest(prompt="Action", source_media_id=MEDIA, project_id=LOCAL))
        else:
            await flow.export_image(flow.UpscaleImageRequest(media_id=MEDIA, project_id=LOCAL))
    assert exc.value.status_code == 409
    assert client.method_calls == []


async def test_stale_session_file_cannot_create_or_switch(tmp_path, monkeypatch):
    stale = tmp_path / "old-session.json"
    stale.write_text(json.dumps({"project_id": MEDIA, "last_activity_at": 1}))
    before = stale.read_bytes()
    monkeypatch.setenv("FLOW_SESSION_PROJECT_STATE", str(stale))
    client = MagicMock()
    assert (await session.ensure_session_project(client))["project_id"] == PIN
    with pytest.raises(policy.PolicyError, match="CREATION_DISABLED"):
        await session.ensure_session_project(client, force_new=True)
    assert client.method_calls == []
    assert stale.read_bytes() == before


async def test_create_rpc_hidden_in_later_envelope_group_is_blocked(monkeypatch):
    client = FlowClient()
    send = AsyncMock()
    monkeypatch.setattr(client, "_send", send)
    safe = json.loads(fb.media_request(MEDIA))
    create = json.loads(fb.create_project_request("Forbidden"))
    result = await client.batch_rpc(fb.RPC_MEDIA, json.dumps(safe + create))
    assert result["status"] == 409
    assert "ENVELOPE_MISMATCH" in result["error"]
    send.assert_not_called()
