"""The editor opens the project and shows what its files hold."""


def test_project_opens(editor):
    state = editor.status()
    assert state["state"] == "edit"
    assert [world["file"] for world in state["worlds"]] == ["Assets/world.world"]
    assert state["unsaved"] == []
    assert editor.find("tab:world.world").selected


def test_hierarchy_lists_the_world(editor):
    # The root of the world, then its entities: the ones with children first, then by name. An
    # entity with children starts folded.
    rows = editor.find("hierarchy/tree").labels(role="row")
    assert rows == ["world", "Group", "Camera", "Crate", "Player", "Sky", "Sun"]
    assert editor.find("hierarchy/Group").value == "collapsed"
