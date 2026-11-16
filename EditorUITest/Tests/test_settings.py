"""The Settings window: a window of its own, whose form writes .Panda/project.json."""


def test_a_project_setting_reaches_project_json(editor):
    assert "wind" not in editor.json(".Panda/project.json")["rendering"]["features"]
    editor.show(settings="project")
    # The window is in front: the elements and the input are its.
    editor.expect("RENDERING/Wind/toggle", value="off")
    editor.tap("RENDERING/Wind/toggle")
    editor.expect("RENDERING/Wind/toggle", value="on")
    editor.save()
    assert "wind" in editor.json(".Panda/project.json")["rendering"]["features"]
    editor.show(settings="close")
    # The main window is in front again.
    editor.expect("hierarchy/tree")


def test_the_pages_of_the_settings(editor):
    editor.show(settings="editor")
    assert editor.find("list").labels(role="label") == ["Editor", "Project", "Keymap"]
    editor.tap("list/Project")
    editor.expect("WORLD/Start World/assetWell", value="world.world")
    editor.show(settings="close")
