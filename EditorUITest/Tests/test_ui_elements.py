"""The controls of PandaUI one by one, on the pages of the UI Gallery (Help → UI Gallery): each is
found as an element, read, used with the pointer or the keys, and read again. What a control of
the editor does is tested where it is used; this is the control itself."""

import pandatest

SHARED_EDITOR = True  # nothing here changes the project: one editor for the whole file

G = "uiGallery/"


def page(editor, name):
    editor.command("help.uiGallery")
    editor.tap(G + "list/" + name)
    editor.expect(G + "list/" + name, selected=True)


def labels(editor):
    return editor.find("uiGallery").labels(role="label")


def test_button(editor):
    page(editor, "Buttons")
    assert "Clicks: 0" in labels(editor)
    editor.tap(G + "Click me")  # below the fold: the page scrolls to it
    editor.tap(G + "Click me")
    assert "Clicks: 2" in labels(editor)


def test_a_disabled_control_takes_no_click(editor):
    page(editor, "Buttons")
    assert editor.find(G + "Disabled").disabled
    try:
        editor.tap(G + "Disabled", wait=0.2)
        raise AssertionError("a click went to a disabled button")
    except pandatest.ToolError as refusal:
        assert "is disabled" in str(refusal)


def test_toggle(editor):
    page(editor, "Toggle")
    editor.expect(G + "toggle[0]", value="off")
    editor.tap(G + "toggle[0]")
    editor.expect(G + "toggle[0]", value="on")
    assert "On" in labels(editor)
    # The keyboard flips it too.
    editor.key("Space")
    editor.expect(G + "toggle[0]", value="off")


def test_slider(editor):
    page(editor, "Slider")
    editor.expect(G + "slider[0]", value="0")
    editor.tap(G + "slider[0]", at=(0.75, 0.5))
    value = float(editor.value(G + "slider[0]"))
    assert 0.7 < value < 0.8, value
    # A drag of the thumb to the end of the track.
    editor.drag(G + "slider[0]", G + "slider[0]", at=(0.75, 0.5), to_at=(1.0, 0.5))
    editor.expect(G + "slider[0]", value="1")
    assert "1.00" in labels(editor)


def test_stepper(editor):
    page(editor, "Stepper")
    editor.expect(G + "stepper[0]", value="3")
    editor.tap(G + "stepper[0]/Increment")
    editor.tap(G + "stepper[0]/Increment")
    editor.tap(G + "stepper[0]/Decrement")
    editor.expect(G + "stepper[0]", value="4")
    # At the end of the range the button that would leave it is off.
    assert editor.find(G + "stepper[2]/Increment").disabled


def test_segmented_control(editor):
    page(editor, "Segmented")
    editor.expect(G + "segmentedControl[0]", value="List")
    editor.tap(G + "segmentedControl[0]/Grid")
    editor.expect(G + "segmentedControl[0]", value="Grid")
    editor.expect(G + "segmentedControl[0]/Grid", selected=True)
    editor.expect(G + "segmentedControl[0]/List", selected=False)


def test_text_field(editor):
    page(editor, "TextField")
    field = G + "textField:Type here"
    editor.type_text(field, "Hello, Panda", submit=False)
    editor.expect(field, value="Hello, Panda")
    editor.key("Backspace")
    editor.expect(field, value="Hello, Pand")
    # Typing replaces a selection.
    editor.type_text(field, "again", submit=False)
    editor.expect(field, value="again")


def test_number_field_clamps_to_its_range(editor):
    page(editor, "NumberField")
    editor.expect(G + "numberField[1]", value="5")
    editor.type_text(G + "numberField[1]", "25")
    editor.expect(G + "numberField[1]", value="10")


def test_combobox(editor):
    page(editor, "Combobox")
    editor.expect(G + "combobox[0]", value="OpenGL")
    editor.tap(G + "combobox[0]")
    # The choices are a list in a layer over the window.
    assert editor.find("popup/list").labels(role="row") == ["OpenGL", "Vulkan", "Metal", "DirectX 12"]
    editor.tap("popup/list/Metal")
    editor.expect("popup", gone=True)
    editor.expect(G + "combobox[0]", value="Metal")
    assert "Renderer: Metal,  Quality: High" in labels(editor)


def test_menu(editor):
    page(editor, "Menu")
    assert "Nothing selected" in labels(editor)
    editor.tap(G + "Options")
    assert editor.find("menu").labels(role="menuItem") == ["New", "Open", "Save", "Settings"]
    editor.tap("menu/Save")
    editor.expect("menu", gone=True)
    assert "Nothing selected" not in labels(editor)
    # Escape closes a menu without a choice.
    editor.tap(G + "Options")
    editor.expect("menu")
    editor.key("Escape")
    editor.expect("menu", gone=True)


def test_dialog_blocks_what_is_under_it(editor):
    page(editor, "Modal")
    editor.tap(G + "Delete…")
    dialog = editor.find("dialog")
    assert dialog.label == "Delete 3 assets?"
    assert dialog.labels(role="button") == ["Cancel", "Delete"]
    try:
        editor.tap(G + "New Layer…", wait=0.2)
        raise AssertionError("a click went through a dialog")
    except pandatest.ToolError as refusal:
        assert "is covered by dialog" in str(refusal)
    editor.tap("dialog/Cancel")
    editor.expect("dialog", gone=True)
    editor.tap(G + "New Layer…")
    editor.expect("dialog")
    editor.key("Escape")
    editor.expect("dialog", gone=True)


def test_tooltip_comes_after_a_pause(editor):
    page(editor, "Tooltip")
    assert not editor.exists("tooltip")
    editor.hover(G + "Save")
    tooltip = editor.find("tooltip", wait=3)
    assert tooltip.labels() == ["Save changes"]
    # It goes when the pointer leaves.
    editor.hover(G + "list/Tooltip")
    editor.expect("tooltip", gone=True)


def test_collapsible_section(editor):
    page(editor, "Collapsible")
    editor.expect(G + "Transform", value="expanded")
    editor.tap(G + "Transform/header")
    editor.expect(G + "Transform", value="collapsed")
    editor.tap(G + "Transform/header")
    editor.expect(G + "Transform", value="expanded")


def test_list_selection(editor):
    page(editor, "List")
    editor.tap(G + "list[1]/Cherry")
    editor.expect(G + "list[1]/Cherry", selected=True)
    editor.tap(G + "list[1]/Apple")
    editor.expect(G + "list[1]/Apple", selected=True)
    editor.expect(G + "list[1]/Cherry", selected=False)
    # The arrows move the selection of a list that has the keyboard.
    editor.key("Down")
    editor.expect(G + "list[1]/Banana", selected=True)


def test_a_row_out_of_sight_is_scrolled_to(editor):
    page(editor, "List")
    assert editor.find(G + "list[1]/Kiwi").out_of_sight
    editor.tap(G + "list[1]/Kiwi")
    kiwi = editor.expect(G + "list[1]/Kiwi", selected=True)
    assert not kiwi.out_of_sight


def test_tree(editor):
    page(editor, "Tree")
    editor.expect(G + "tree", value="8")
    editor.expect(G + "tree/Environment", value="collapsed")
    editor.tap(G + "tree/Environment", at=(0.08, 0.5))  # its arrow: a row of the second level
    editor.expect(G + "tree/Environment", value="expanded")
    editor.expect(G + "tree", value="10")
    assert editor.find(G + "tree").labels(role="row")[3:6] == ["Environment", "Sky", "Fog"]
    editor.tap(G + "tree/Main Camera")
    editor.expect(G + "tree/Main Camera", selected=True)
    # The arrows of the keyboard walk the tree: right unfolds, left folds.
    editor.tap(G + "tree/Scripts")
    editor.key("Right")
    editor.expect(G + "tree/Scripts", value="expanded")
    editor.key("Left")
    editor.expect(G + "tree/Scripts", value="collapsed")
