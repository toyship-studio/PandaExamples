"""Documents: what the editor holds against what the files hold — Reload, Save, the conflict
between an edit in the editor and an edit of the file, a second world."""

import json

import pandatest

WORLD = "Assets/world.world"


def rename_on_disk(editor, old, new):
    """An edit of the world file made outside the editor, as a text editor or an agent makes it."""
    path = editor.path(WORLD)
    document = json.loads(path.read_text())
    for entity in document["entities"]:
        if entity["tagComponent"]["tag"] == old:
            entity["tagComponent"]["tag"] = new
    path.write_text(json.dumps(document, indent=4) + "\n")


def rename_in_the_editor(editor, old, new):
    editor.tap("hierarchy/" + old)
    editor.type_text("inspector/name", new)
    editor.expect("hierarchy/" + new)


def test_reload_takes_what_changed_on_disk(editor):
    rename_on_disk(editor, "Crate", "Barrel")
    editor.reload()
    editor.expect("hierarchy/Barrel")
    editor.expect("hierarchy/Crate", gone=True)


def test_reload_does_not_lose_an_unsaved_edit(editor):
    rename_in_the_editor(editor, "Player", "Hero")
    rename_on_disk(editor, "Crate", "Barrel")
    # Both sides changed the world: Reload names the conflict and touches nothing.
    try:
        editor.reload()
        raise AssertionError("Reload took the file over an unsaved edit")
    except pandatest.ToolError as conflict:
        assert "changed on disk and has unsaved changes" in str(conflict)
    editor.expect("hierarchy/Hero")
    editor.expect("hierarchy/Crate")
    # Told that the disk wins, it drops the edit.
    editor.reload(discard=True)
    editor.expect("hierarchy/Barrel")
    editor.expect("hierarchy/Player")
    editor.expect("hierarchy/Hero", gone=True)


def test_save_does_not_overwrite_a_changed_file(editor):
    rename_in_the_editor(editor, "Player", "Hero")
    rename_on_disk(editor, "Crate", "Barrel")
    try:
        editor.save()
        raise AssertionError("Save wrote over a file that had changed on disk")
    except pandatest.ToolError as conflict:
        assert "changed on disk and has unsaved changes" in str(conflict)
    assert editor.world().has("Barrel") and not editor.world().has("Hero")
    # Told that the editor wins, it writes its version.
    editor.call("save", overwrite=True)
    world = editor.world()
    assert world.has("Hero") and world.has("Crate") and not world.has("Barrel")


def test_a_second_world_opens_in_a_tab(editor):
    editor.open_world("Assets/Levels/level2.world")
    editor.expect("tab:level2.world", selected=True)
    editor.expect("hierarchy/Flag 2")
    editor.expect("hierarchy/Crate", gone=True)
    worlds = {world["file"]: world["active"] for world in editor.status()["worlds"]}
    assert worlds == {WORLD: False, "Assets/Levels/level2.world": True}
    # The tab of the first world brings it back.
    editor.tap("tab:world.world")
    editor.expect("hierarchy/Crate")
