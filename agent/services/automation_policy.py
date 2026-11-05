"""Persistent plan approval and configured Google Flow destination policy."""
import hashlib
import json
import sqlite3
import re
from contextlib import closing
from contextvars import ContextVar

from agent import config

_PROJECT_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
approved_project = ContextVar("approved_plan_project", default=None)
PLAN_DB_PATH = config.BASE_DIR / "automation_plans.db"


class PolicyError(ValueError):
    pass


def flow_target(requested=None):
    target = config.FLOW_PROJECT_ID
    if not target:
        raise PolicyError("FLOW_PROJECT_NOT_CONFIGURED: set FLOW_PROJECT_ID in flowkit-settings.ps1 and restart")
    if not isinstance(target, str) or not _PROJECT_UUID.fullmatch(target):
        raise PolicyError("FLOW_PROJECT_INVALID: FLOW_PROJECT_ID must be a canonical UUID")
    if requested and requested != target:
        raise PolicyError(f"FLOW_PROJECT_MISMATCH: configured destination is {target}; project overrides are disabled")
    return target


def _db():
    db = sqlite3.connect(PLAN_DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS plans (project_id TEXT PRIMARY KEY, plan TEXT NOT NULL, revision TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0)")
    return db


def save_plan(project_id, plan):
    flow_target()
    encoded = json.dumps(plan, ensure_ascii=False, sort_keys=True)
    revision = hashlib.sha256(encoded.encode()).hexdigest()
    with closing(_db()) as db, db:
        db.execute("INSERT INTO plans VALUES (?, ?, ?, 0) ON CONFLICT(project_id) DO UPDATE SET plan=excluded.plan, revision=excluded.revision, approved=0", (project_id, encoded, revision))
    return get_plan(project_id)


def get_plan(project_id):
    with closing(_db()) as db:
        row = db.execute("SELECT * FROM plans WHERE project_id=?", (project_id,)).fetchone()
    if not row:
        raise PolicyError("PLAN_REQUIRED: save and present a plan first")
    return {**dict(row), "plan": json.loads(row["plan"]), "approved": bool(row["approved"])}


def approve_plan(project_id, revision, confirmation):
    if confirmation.strip().upper() != "DUYỆT":
        raise PolicyError("APPROVAL_REQUIRED: user must say DUYỆT")
    with closing(_db()) as db, db:
        result = db.execute("UPDATE plans SET approved=1 WHERE project_id=? AND revision=?", (project_id, revision))
        if result.rowcount != 1:
            raise PolicyError("PLAN_CHANGED: present the current plan for approval")
    return get_plan(project_id)


def require_approval(project_id):
    flow_target()
    if not get_plan(project_id)["approved"]:
        raise PolicyError("APPROVAL_REQUIRED: present plan and wait for DUYỆT")


def validate_rpc(rpcid, freq):
    """Inspect project context slots, never confuse media UUIDs with project IDs."""
    from agent.services import flow_batch as fb
    flow_target()
    if rpcid == fb.RPC_CREATE_PROJECT:
        raise PolicyError("FLOW_PROJECT_CREATION_DISABLED")
    targets = []

    def walk(node):
        if isinstance(node, list):
            if len(node) > 5 and node[0] is None and node[1] == fb.SURFACE_ID:
                targets.append(node[5])
            for item in node:
                walk(item)
        elif isinstance(node, str):
            if node.startswith("projects/"):
                targets.append(node.removeprefix("projects/"))
            elif node.startswith(("[", "{")):
                try:
                    walk(json.loads(node))
                except json.JSONDecodeError:
                    pass
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)

    envelope = json.loads(freq)
    if rpcid != "StreamChat":
        if not isinstance(envelope, list) or not envelope or not isinstance(envelope[0], list):
            raise PolicyError("FLOW_RPC_INVALID_ENVELOPE")
        for group in envelope:
            if not isinstance(group, list) or not group:
                raise PolicyError("FLOW_RPC_INVALID_ENVELOPE")
            for frame in group:
                if not isinstance(frame, list) or not frame or frame[0] != rpcid:
                    raise PolicyError("FLOW_RPC_ENVELOPE_MISMATCH")
    walk(envelope)
    for target in targets:
        if not target:
            raise PolicyError("FLOW_PROJECT_MISSING")
        flow_target(target)
    scoped = {fb.RPC_GEN_IMAGE, fb.RPC_GEN_VIDEO, fb.RPC_GEN_VIDEO_TEXT,
              fb.RPC_GEN_VIDEO_FIRST_LAST, fb.RPC_GEN_VIDEO_REFERENCES,
              fb.RPC_UPLOAD_IMAGE, fb.RPC_PROJECT_MEDIA, "StreamChat"}
    if rpcid in scoped and not targets:
        raise PolicyError("FLOW_PROJECT_MISSING: refusing unscoped RPC")
    if rpcid in scoped - {fb.RPC_PROJECT_MEDIA, fb.RPC_UPLOAD_IMAGE} or rpcid == fb.RPC_UPSCALE_IMAGE:
        require_approval(approved_project.get())
