"""The components of an entity: added from the picker, removed from the menu of their section."""


def test_a_component_is_added_from_the_picker(editor):
    editor.tap("hierarchy/Group")
    editor.expect("inspector/Sprite Renderer", gone=True)
    editor.tap("inspector/Add Component")
    # The picker is a search field over a list, in a layer of its own; the field has the keyboard.
    editor.key(text="sprite")
    editor.expect("popup/list/row", count=1)
    editor.key("Enter")
    editor.expect("popup", gone=True)
    editor.expect("inspector/Sprite Renderer", value="expanded")
    editor.save()
    assert "spriteRendererComponent" in editor.world().entity("Group")


def test_a_component_is_removed_from_its_menu(editor):
    editor.tap("hierarchy/Crate")
    editor.tap("inspector/Sprite Renderer/header/Component Actions")
    assert editor.find("menu").labels(role="menuItem") == ["Copy Values", "Paste Values", "Reset", "Remove Component"]
    editor.tap("menu/Remove Component")
    editor.expect("inspector/Sprite Renderer", gone=True)
    editor.save()
    assert "spriteRendererComponent" not in editor.world().entity("Crate")
    # One step back brings the component and its values.
    editor.command("edit.undo")
    editor.expect("inspector/Sprite Renderer/Color/colorWell", value="#FF8033FF")


def test_values_are_copied_between_components(editor):
    editor.tap("hierarchy/Crate")
    editor.tap("inspector/Sprite Renderer/header/Component Actions")
    editor.tap("menu/Copy Values")
    editor.tap("hierarchy/Player")
    editor.expect("inspector/Sprite Renderer/Color/colorWell", value="#4080FFFF")
    editor.tap("inspector/Sprite Renderer/header/Component Actions")
    editor.tap("menu/Paste Values")
    editor.expect("inspector/Sprite Renderer/Color/colorWell", value="#FF8033FF")
