"""Play: the game runs in a copy of the world, Stop returns to the world being edited."""

SCRIPTS = True


def test_play_and_stop_from_the_toolbar(editor):
    editor.expect("toolbar/stop", disabled=True)
    editor.tap("toolbar/play")
    editor.wait_log("PROBE ")
    assert editor.status()["state"] == "play"
    editor.expect("toolbar/stop", disabled=False)
    editor.tap("toolbar/stop")
    editor.expect("toolbar/stop", disabled=True)
    assert editor.status()["state"] == "edit"


def test_what_happens_in_play_stays_in_play(editor):
    editor.play()
    editor.tap("hierarchy/Crate")
    editor.type_text("inspector/Transform/Position/X", "3")
    editor.expect("inspector/Transform/Position/X", value="3.00")
    editor.stop_game()
    # The tab that was open in Play shows the entity of the world being edited again: the copy
    # the game ran in is gone, and so is what was done to it.
    editor.expect("tab:Crate", selected=True)
    editor.expect("inspector/Transform/Position/X", value="0.00")
    assert editor.status()["unsaved"] == []
    editor.save()
    assert editor.world().position("Crate") == (0.0, 0.0, 0.0)


def test_an_open_form_follows_the_game(editor):
    # A tab opened while editing shows the entity of the playing copy during Play.
    editor.tap("hierarchy/Player")
    editor.type_text("inspector/Probe/count/numberField", "8")
    editor.play()
    line = editor.wait_log("PROBE ")
    assert " count=8 " in line
    editor.expect("inspector/Probe/count/numberField", value="8")
    editor.stop_game()
    editor.expect("inspector/Probe/count/numberField", value="8")
