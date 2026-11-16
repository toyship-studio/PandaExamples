"""The Scene: the picking, the gizmo and the editor camera, all driven by the pointer."""

SCENE = "viewport/scene"


def look_at_the_crate(editor):
    editor.call("camera", position=[0, 0, 6], target=[0, 0, 0])


def test_a_click_selects_what_is_under_the_pointer(editor):
    look_at_the_crate(editor)
    editor.tap(SCENE)  # the crate is in the middle of the picture
    editor.expect("hierarchy/Crate", selected=True)
    editor.expect("inspector/name", value="Crate")


def test_the_gizmo_moves_an_entity(editor):
    look_at_the_crate(editor)
    editor.tap("hierarchy/Crate")
    editor.expect("inspector/Transform/Position/X", value="0.00")
    # The arrow of the X axis starts at the middle of the picture and points right.
    width = editor.find(SCENE).frame[2]
    grab = 0.5 + 30.0 / width
    editor.drag(SCENE, SCENE, at=(grab, 0.5), to_at=(grab + 0.12, 0.5), steps=12)
    moved = float(editor.value("inspector/Transform/Position/X"))
    assert moved > 0.5, "the crate did not follow the gizmo: x = %s" % moved
    assert editor.value("inspector/Transform/Position/Y") == "0.00"
    editor.save()
    assert abs(editor.world().position("Crate")[0] - moved) < 0.01
    # The whole drag is one step of the history.
    editor.command("edit.undo")
    editor.expect("inspector/Transform/Position/X", value="0.00")


def test_the_wheel_and_the_right_button_move_the_camera(editor):
    look_at_the_crate(editor)
    before = editor.status()["camera"]
    editor.scroll(SCENE, dy=3)
    after_wheel = editor.status()["camera"]
    assert after_wheel["position"] != before["position"]
    assert after_wheel["forward"] == before["forward"]
    editor.drag(SCENE, SCENE, at=(0.5, 0.5), to_at=(0.6, 0.5), button="right")
    after_turn = editor.status()["camera"]
    assert after_turn["forward"] != before["forward"]
    assert after_turn["position"] == after_wheel["position"]


def test_the_tools_of_the_gizmo(editor):
    editor.expect("viewport/Move (1)", selected=True)
    editor.tap("viewport/Rotate (2)")
    editor.expect("viewport/Rotate (2)", selected=True)
    editor.expect("viewport/Move (1)", selected=False)
