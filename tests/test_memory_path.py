"""memory ids are UUIDs: anything else must not reach the HTTP path."""

import pytest
from fastmcp.exceptions import ToolError

from clr_mem0_mcp.server import _memory_path


def test_uuid_builds_the_path():
    assert (
        _memory_path("6F9619FF-8B86-D011-B42D-00C04FC964FF")
        == "/memories/6f9619ff-8b86-d011-b42d-00c04fc964ff"
    )
    assert _memory_path(" 6f9619ff-8b86-d011-b42d-00c04fc964ff ", "/history").endswith("/history")


@pytest.mark.parametrize(
    "bad", ["../reset", "abc", "", "6f9619ff-8b86-d011-b42d-00c04fc964ff/history", "x?user_id=all"]
)
def test_non_uuid_is_refused(bad):
    with pytest.raises(ToolError):
        _memory_path(bad)
