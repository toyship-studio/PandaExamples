"""The Hierarchy: the tree of the world, the selection, and the edits made from it."""

TREE = "hierarchy/tree"


def rows(editor):
    return editor.find(TREE).labels(role="row")


def test_a_row_unfolds_and_folds(editor):
    assert "Coin A" not in rows(editor)
    # The arrow of a row is at its left edge.
    editor.tap("hierarchy/Group", at=(0.08, 0.5))
    editor.expect("hierarchy/Group", value="expanded")
    assert rows(editor) == ["world", "Group", "Coin A", "Coin B", "Camera", "Crate", "Player", "Sky", "Sun"]
    editor.tap("hierarchy/Group", at=(0.08, 0.5))
    editor.expect("hierarchy/Coin A", gone=True)


def test_selection_follows_the_click(editor):
    editor.tap("hierarchy/Crate")
    editor.expect("hierarchy/Crate", selected=True)
    editor.expect("tab:Crate", selected=True)
    editor.tap("hierarchy/Sun")
    editor.expect("hierarchy/Sun", selected=True)
    editor.expect("hierarchy/Crate", selected=False)
    # Command adds to the selection.
    editor.tap("hierarchy/Sky", super=True)
    editor.expect("hierarchy/Sky", selected=True)
    editor.expect("hierarchy/Sun", selected=True)
    assert editor.find("hierarchy").find_all(role="label", label="2 of 8 entities selected")


def test_the_search_filters_the_tree(editor):
    editor.type_text("hierarchy/textField", "Coin", submit=False)
    editor.expect("hierarchy/Coin A")
    assert set(rows(editor)) >= {"Coin A", "Coin B"}
    assert "Crate" not in rows(editor)


def test_duplicate_and_delete(editor):
    editor.tap("hierarchy/Crate")
    editor.command("entity.duplicate")
    editor.expect("hierarchy/Crate", count=2)
    editor.save()
    assert editor.world().names().count("Crate") == 2

    editor.command("entity.delete")
    editor.expect("hierarchy/Crate", count=1)
    editor.command("edit.undo")
    editor.expect("hierarchy/Crate", count=2)


def test_the_menu_of_a_row(editor):
    editor.right_tap("hierarchy/Player")
    assert editor.find("menu").labels(role="menuItem") == ["Add Child", "Rename", "Duplicate", "Copy", "Paste", "Delete"]
    editor.tap("menu/Delete")
    editor.expect("menu", gone=True)
    editor.expect("hierarchy/Player", gone=True)
    editor.save()
    assert not editor.world().has("Player")


def test_a_row_dropped_on_another_becomes_its_child(editor):
    editor.drag("hierarchy/Crate", "hierarchy/Group")
    editor.expect("hierarchy/Group", value="expanded")
    assert rows(editor)[1:5] == ["Group", "Coin A", "Coin B", "Crate"]
    editor.save()
    world = editor.world()
    assert world.parent("Crate") == "Group"
    assert world.children("Group") == ["Coin A", "Coin B", "Crate"]
