from unittest.mock import MagicMock
import pytest
from agent.services import flow_project_session as fps
from agent.services.automation_policy import PolicyError

TEST_PROJECT_ID = "b29b7ca7-17c0-4bde-ade8-c7f458bc2625"


async def test_session_project_is_permanently_pinned():
    client = MagicMock()
    for _ in range(2):
        result = await fps.ensure_session_project(client, title="Ignored")
        assert result["project_id"] == TEST_PROJECT_ID
        assert result["pinned"] and result["active"]
    client.create_project.assert_not_called()


async def test_session_project_cannot_force_new():
    client = MagicMock()
    with pytest.raises(PolicyError, match="CREATION_DISABLED"):
        await fps.ensure_session_project(client, force_new=True)
    client.create_project.assert_not_called()
