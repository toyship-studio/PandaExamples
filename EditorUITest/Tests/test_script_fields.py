"""The published fields of a script (PANDA_FIELD) in the form of an entity: one value and a list
of every kind, the gestures that fill a list, and that the game gets what the form shows.

The entity is Player, its script is Probe (Scripts/EditorUITest/src/Probe.hpp): a field of every
type, and one line of log at the start of the game with what the fields got.
"""

SCRIPTS = True  # the Probe class is built before these tests

PROBE = "inspector/Probe/"


def asset_id(editor, relative):
    return editor.json(relative + ".pmeta")["id"]


def entity_id(editor, name):
    return editor.world().entity(name)["id"]


def select_player(editor):
    editor.tap("hierarchy/Player")
    editor.expect(PROBE + "count")


def test_fields_show_what_the_world_holds(editor):
    select_player(editor)
    assert editor.value(PROBE + "count/numberField") == "3"
    assert editor.value(PROBE + "speed/numberField") == "1.5"
    assert editor.value(PROBE + "target/entityWell") == "Crate"
    assert editor.value(PROBE + "icon/assetWell") == "checker.png"
    assert editor.value(PROBE + "skin/assetWell") == "red.mat"
    assert editor.value(PROBE + "next/assetWell") == "level1.world"
    # A list is a header that says how long it is, and a row per item.
    assert editor.find(PROBE + "numbers/summary").label == "3 items"
    assert [editor.value(PROBE + "numbers.%d/numberField" % index) for index in range(3)] == ["1", "2", "3"]
    assert [editor.value(PROBE + "levels.%d/assetWell" % index) for index in range(2)] == ["level1.world", "level2.world"]
    assert editor.find(PROBE + "frames/summary").label == "Empty"
    assert [editor.value(PROBE + "waypoints.%d/entityWell" % index) for index in range(2)] == ["Coin A", "Coin B"]


def test_a_number_reaches_the_world_file(editor):
    select_player(editor)
    editor.type_text(PROBE + "count/numberField", "7")
    editor.type_text(PROBE + "speed/numberField", "0.25")
    editor.save()
    fields = editor.world().fields("Player", "Probe")
    assert fields["count"] == 7
    assert fields["speed"] == 0.25


def test_a_list_grows_shrinks_and_reorders(editor):
    select_player(editor)
    numbers = lambda: editor.world().fields("Player", "Probe")["numbers"]

    editor.tap(PROBE + "numbers/Add Item")
    editor.expect(PROBE + "numbers/summary", label="4 items")
    editor.type_text(PROBE + "numbers.3/numberField", "9")
    editor.save()
    assert numbers() == [1, 2, 3, 9]

    editor.tap(PROBE + "numbers.0/Remove Item")
    editor.expect(PROBE + "numbers/summary", label="3 items")
    editor.save()
    assert numbers() == [2, 3, 9]

    # The first item has nothing above it; the arrow of another one swaps it with the one above.
    editor.expect(PROBE + "numbers.0/Move Up", disabled=True)
    editor.tap(PROBE + "numbers.2/Move Up")
    editor.expect(PROBE + "numbers.1/numberField", value="9")
    editor.save()
    assert numbers() == [2, 9, 3]


def test_an_edit_of_a_list_is_one_step_of_undo(editor):
    select_player(editor)
    editor.tap(PROBE + "numbers.1/Remove Item")
    editor.expect(PROBE + "numbers/summary", label="2 items")
    editor.command("edit.undo")
    editor.expect(PROBE + "numbers/summary", label="3 items")
    editor.expect(PROBE + "numbers.1/numberField", value="2")
    editor.command("edit.redo")
    editor.expect(PROBE + "numbers/summary", label="2 items")


def test_a_row_is_dragged_by_its_index(editor):
    select_player(editor)
    # The index is the handle of a row: the item takes the place of the row it is dropped on.
    editor.drag(PROBE + "numbers.0", PROBE + "numbers.2", at=(0.07, 0.5))
    editor.expect(PROBE + "numbers.2/numberField", value="1")
    editor.save()
    assert editor.world().fields("Player", "Probe")["numbers"] == [2, 3, 1]


def test_an_asset_dropped_on_the_header_joins_the_list(editor):
    select_player(editor)
    editor.double_tap("contentBrowser/files/Levels")
    editor.drag("contentBrowser/files/level10.world", PROBE + "levels")
    editor.expect(PROBE + "levels/summary", label="3 items")
    editor.expect(PROBE + "levels.2/assetWell", value="level10.world")
    editor.save()
    assert editor.world().fields("Player", "Probe")["levels"] == [
        asset_id(editor, "Assets/Levels/level1.world"),
        asset_id(editor, "Assets/Levels/level2.world"),
        asset_id(editor, "Assets/Levels/level10.world"),
    ]


def test_a_folder_dropped_on_the_header_gives_its_assets_of_the_kind(editor):
    select_player(editor)
    # Frames holds three pictures and a material: a list of textures takes the pictures, in the
    # order of their names (frame2 before frame10), as one edit.
    editor.drag("contentBrowser/files/Frames", PROBE + "frames")
    editor.expect(PROBE + "frames/summary", label="3 items")
    editor.save()
    assert editor.world().fields("Player", "Probe")["frames"] == [
        asset_id(editor, "Assets/Frames/frame1.png"),
        asset_id(editor, "Assets/Frames/frame2.png"),
        asset_id(editor, "Assets/Frames/frame10.png"),
    ]
    editor.command("edit.undo")
    editor.expect(PROBE + "frames/summary", label="Empty")


def test_several_assets_go_to_the_list_of_a_pinned_tab(editor):
    # The form of an entity gives way to the form of the assets when assets are selected — unless
    # its tab is pinned (a double click on the tab). Then a selection of several assets is taken
    # to its list at once, and the tab stays in front after the drop.
    select_player(editor)
    editor.expect("tab:Player", value="preview")
    editor.double_tap("tab:Player")
    editor.expect("tab:Player", value="")
    editor.double_tap("contentBrowser/files/Textures")
    editor.tap("contentBrowser/files/checker.png")
    editor.tap("contentBrowser/files/stripes.png", shift=True)  # a range: checker, dots, stripes
    editor.expect("tab:3 assets", selected=True)
    editor.tap("tab:Player")
    editor.drag("contentBrowser/files/dots.png", PROBE + "frames")
    editor.expect("tab:Player", selected=True)
    editor.expect(PROBE + "frames/summary", label="3 items")
    editor.save()
    assert editor.world().fields("Player", "Probe")["frames"] == [
        asset_id(editor, "Assets/Textures/checker.png"),
        asset_id(editor, "Assets/Textures/dots.png"),
        asset_id(editor, "Assets/Textures/stripes.png"),
    ]


def test_an_entity_dropped_on_the_header_joins_the_list(editor):
    select_player(editor)
    editor.drag("hierarchy/Crate", PROBE + "waypoints")
    editor.expect(PROBE + "waypoints/summary", label="3 items")
    editor.expect(PROBE + "waypoints.2/entityWell", value="Crate")
    editor.save()
    assert editor.world().fields("Player", "Probe")["waypoints"][-1] == entity_id(editor, "Crate")


def test_a_drop_on_a_value_replaces_it(editor):
    select_player(editor)
    editor.double_tap("contentBrowser/files/Textures")
    editor.drag("contentBrowser/files/dots.png", PROBE + "icon/assetWell")
    editor.expect(PROBE + "icon/assetWell", value="dots.png")
    editor.save()
    assert editor.world().fields("Player", "Probe")["icon"] == asset_id(editor, "Assets/Textures/dots.png")


def test_the_game_gets_what_the_form_shows(editor):
    select_player(editor)
    editor.type_text(PROBE + "count/numberField", "5")
    editor.tap(PROBE + "numbers.0/Remove Item")
    editor.expect(PROBE + "numbers/summary", label="2 items")
    editor.play()
    line = editor.wait_log("PROBE ")
    editor.stop_game()
    values = dict(part.split("=", 1) for part in line.split("PROBE ", 1)[1].split())
    assert values["count"] == "5"
    assert values["numbers"] == "[2,3]"
    assert values["target"] == str(entity_id(editor, "Crate"))
    assert values["icon"] == str(asset_id(editor, "Assets/Textures/checker.png"))
    assert values["skin"] == str(asset_id(editor, "Assets/Materials/red.mat"))
    assert values["next"] == str(asset_id(editor, "Assets/Levels/level1.world"))
    assert values["levels"] == "[%d,%d]" % (
        asset_id(editor, "Assets/Levels/level1.world"),
        asset_id(editor, "Assets/Levels/level2.world"),
    )
    assert values["waypoints"] == "[%d,%d]" % (entity_id(editor, "Coin A"), entity_id(editor, "Coin B"))
