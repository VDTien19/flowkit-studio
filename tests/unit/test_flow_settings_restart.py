"""Exercise the real PowerShell settings loader and fresh Python processes offline."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
ID_A = "11111111-2222-3333-4444-555555555555"
ID_B = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SHELL = shutil.which("powershell") or shutil.which("pwsh")

# Child process: real builders/policy/provider, mocked transport, isolated plan DB.
PROBE = r'''
import asyncio, json
from unittest.mock import AsyncMock, patch, PropertyMock
from agent import config
from agent.api import flow
from agent.services import automation_policy as policy, flow_batch as fb, omni_flash
from agent.services.flow_client import FlowClient
from agent.services import flow_client as fc
from agent.services.flow_project_session import ensure_session_project
from agent.sdk.services.flow_provider import FlowProvider
from agent.sdk.services.provider_base import ProviderJob

async def main():
    target = policy.flow_target()
    local_id = "local-film-kept-across-restarts"
    try:
        plan = policy.get_plan(local_id)
        reused = True
    except policy.PolicyError:
        plan = policy.save_plan(local_id, {"story": "offline", "flow_project_id": target})
        try:
            policy.require_approval(local_id)
            raise AssertionError("Ran before approval")
        except policy.PolicyError:
            pass
        policy.approve_plan(local_id, plan["revision"], "DUY\u1ec6T")
        reused = False
    policy.require_approval(local_id)
    token = policy.approved_project.set(local_id)
    fc.FLOW_GENERATION_MIN_INTERVAL_S = 0  # offline test, no need to wait between mocks
    client = FlowClient()
    calls = []
    async def offline_send(method, params, timeout=300):
        assert method == "batch_rpc"
        policy.validate_rpc(params["rpcid"], params["freq"])
        assert target in params["freq"]
        assert params["rpcid"] != fb.RPC_CREATE_PROJECT
        calls.append(params["rpcid"])
        return {"error": "OFFLINE_TEST_STOP", "status": 502}
    client._send = offline_send
    media = "99999999-8888-7777-6666-555555555555"
    with patch.object(omni_flash, "get_flow_client", return_value=client):
        await client.generate_images("Action", "")
        await client.generate_video(media, "Action", target, "scene")
        await client.edit_image("Action", media, target)
        await client.upload_image("bytes", project_id="")
        await client.upscale_image(media, target)
        await omni_flash.generate_omni_flash_text_video(prompt="Action", project_id="")
        await omni_flash.generate_omni_flash_first_frame_video(prompt="Action", project_id=target, start_image_media_id=media, scene_id="scene")
        await omni_flash.generate_omni_flash_first_last_video(prompt="Action", project_id=target, start_image_media_id=media, end_image_media_id=media, scene_id="scene")
        await omni_flash.generate_omni_flash_video(prompt="Action", project_id=target, reference_media_ids=[media], scene_id="scene")
    assert len(calls) == 9, calls
    before = len(calls)
    assert (await client.create_project("Forbidden"))["status"] == 409
    assert (await client.batch_rpc(fb.RPC_CREATE_PROJECT, fb.create_project_request("Forbidden")))["status"] == 409
    assert (await client.generate_images("Action", media))["error"].startswith("PolicyError: FLOW_PROJECT_MISMATCH")
    assert len(calls) == before
    provider = FlowProvider(client)
    targets = []
    async def capture(job):
        targets.append(job.extra["project_id"])
        return {"ok": True}
    provider._run_approved = capture
    for kind in ("image", "edit_image", "video", "video_refs", "upscale"):
        await provider.run(ProviderJob(job_id=kind, kind=kind, extra={"project_id": local_id}))
    assert targets == [target] * 5
    with patch.object(flow, "get_flow_client", return_value=client):
        status = await flow.extension_status()
        assert status["flow_project_id"] == status["session_project"]["project_id"] == target
        assert await flow._resolve_direct_project(client, "") == target
    assert (await ensure_session_project(client))["project_id"] == target
    policy.approved_project.reset(token)
    print(json.dumps({"target": target, "media_calls": calls, "provider_targets": targets,
                      "approval_reused": reused, "revision": plan["revision"],
                      "stored_plan_target": plan["plan"]["flow_project_id"]}))
asyncio.run(main())
'''


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@pytest.mark.skipif(not SHELL, reason="PowerShell required for Windows launcher integration")
def test_settings_change_takes_effect_after_restart(tmp_path):
    launcher = tmp_path / "start-flowkit.ps1"
    shutil.copyfile(ROOT / launcher.name, launcher)
    settings = tmp_path / "flowkit-settings.ps1"
    probe = tmp_path / "probe.py"
    probe.write_text(PROBE, encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT), "FLOW_AGENT_DIR": str(tmp_path),
           "FLOW_PROJECT_ID": "stale-inherited-value"}
    results = []
    for destination in (ID_A, ID_B):
        settings.write_text("$env:FLOW_PROJECT_ID = '" + destination + "'\n", encoding="utf-8")
        command = "$ErrorActionPreference='Stop'; & " + ps_quote(launcher) + " -CheckConfig; & " + ps_quote(sys.executable) + " " + ps_quote(probe) + "; exit $LASTEXITCODE"
        result = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-Command", command],
                                env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr + result.stdout
        lines = result.stdout.strip().splitlines()
        assert lines[0] == destination
        data = json.loads(lines[-1])
        assert data["target"] == destination
        assert data["provider_targets"] == [destination] * 5
        results.append(data)
    assert not results[0]["approval_reused"] and results[1]["approval_reused"]
    assert results[0]["revision"] == results[1]["revision"]
    assert results[1]["stored_plan_target"] == ID_A  # old plan never overrides new config


@pytest.mark.skipif(not SHELL, reason="PowerShell required")
@pytest.mark.parametrize("content", [None, "# no assignment", "$env:FLOW_PROJECT_ID = ''", "$env:FLOW_PROJECT_ID = 'invalid'"])
def test_launcher_rejects_missing_or_invalid_settings(tmp_path, content):
    launcher = tmp_path / "start-flowkit.ps1"
    shutil.copyfile(ROOT / launcher.name, launcher)
    if content is not None:
        (tmp_path / "flowkit-settings.ps1").write_text(content, encoding="utf-8")
    result = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-File", str(launcher), "-CheckConfig"],
                            env={**os.environ, "FLOW_PROJECT_ID": ID_A}, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0


@pytest.mark.parametrize("destination", [ID_A, ID_B])
def test_config_has_no_default_id_and_imports_environment(destination):
    result = subprocess.run([sys.executable, "-c", "from agent.config import FLOW_PROJECT_ID; print(FLOW_PROJECT_ID)"],
                            cwd=ROOT, env={**os.environ, "FLOW_PROJECT_ID": destination}, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and result.stdout.strip() == destination
