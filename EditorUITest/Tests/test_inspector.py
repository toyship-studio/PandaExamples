"""The form of an entity: what it shows, and that an edit made in it reaches the world file."""


def test_selecting_an_entity_shows_its_form(editor):
    editor.tap("hierarchy/Player")
    editor.expect("hierarchy/Player", selected=True)
    editor.expect("inspector/name", value="Player")
    assert editor.value("inspector/Transform/Position/Y") == "-1.50"
    assert editor.value("inspector/Sprite Renderer/Color/colorWell") == "#4080FFFF"
    # A tab of the entity opens next to the viewport.
    editor.expect("tab:Player", selected=True)


def test_position_reaches_the_world_file(editor):
    editor.tap("hierarchy/Crate")
    editor.type_text("inspector/Transform/Position/X", "2.5")
    editor.expect("inspector/Transform/Position/X", value="2.50")
    # The world has an edit its file does not: the dot on its tab says so until it is saved.
    editor.expect("tab:world.world", value="unsaved")
    assert editor.status()["worlds"][0]["unsaved"]
    editor.save()
    editor.expect("tab:world.world", value="")
    assert editor.status()["unsaved"] == []
    assert editor.world().position("Crate") == (2.5, 0.0, 0.0)


def test_undo_and_redo_of_an_edit(editor):
    editor.tap("hierarchy/Crate")
    editor.type_text("inspector/Transform/Position/X", "4")
    editor.expect("inspector/Transform/Position/X", value="4.00")
    editor.tap("toolbar/undo")
    editor.expect("inspector/Transform/Position/X", value="0.00")
    editor.tap("toolbar/redo")
    editor.expect("inspector/Transform/Position/X", value="4.00")
    editor.command("edit.undo")
    editor.expect("inspector/Transform/Position/X", value="0.00")


def test_rename(editor):
    editor.tap("hierarchy/Crate")
    editor.type_text("inspector/name", "Box")
    editor.expect("hierarchy/Box")
    editor.expect("hierarchy/Crate", gone=True)
    editor.save()
    names = editor.world().names()
    assert "Box" in names and "Crate" not in names


def test_static_flag(editor):
    editor.tap("hierarchy/Crate")
    editor.expect("inspector/static", value="off")
    editor.tap("inspector/static")
    editor.expect("inspector/static", value="on")
    editor.save()
    assert editor.world().entity("Crate").get("isStatic") is True


def test_a_section_folds(editor):
    editor.tap("hierarchy/Crate")
    editor.expect("inspector/Transform", value="expanded")
    editor.tap("inspector/Transform/header")
    editor.expect("inspector/Transform", value="collapsed")
    editor.tap("inspector/Transform/header")
    editor.expect("inspector/Transform", value="expanded")
