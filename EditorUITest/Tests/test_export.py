"""The game as it ships: what a cook packs, and what the built game gets."""

import time

import pandatest


def asset_id(editor, relative):
    return editor.json(relative + ".pmeta")["id"]


def test_a_cook_packs_what_the_start_world_reaches(editor):
    editor.export("cook")
    report = editor.json(".Panda/Cooked/report.json")
    assert report["startWorld"] == "Assets/world.world"
    assert report["warnings"] == []
    # The pack holds the start world and what its entities and the fields of its script name —
    # one value (next, icon, skin) and a list (levels) — next to the files of the engine.
    packed = sorted(file["path"] for file in report["files"] if file["kind"] != "engine")
    assert packed == [
        "Materials/Assets/Materials/red.pmaterial",
        "Textures/Assets/Textures/checker.ptex",
        "Worlds/Assets/Levels/level1.pworld",
        "Worlds/Assets/Levels/level2.pworld",
        "Worlds/Assets/world.pworld",
    ]
    # What nothing names stays out of the game, and the cook says which files those are.
    left_out = sorted(file["path"] for file in report["unused"])
    assert left_out == [
        "Assets/Frames/frame1.png",
        "Assets/Frames/frame10.png",
        "Assets/Frames/frame2.png",
        "Assets/Frames/tint.mat",
        "Assets/Levels/level10.world",
        "Assets/Levels/spare.world",
        "Assets/Materials/blue.mat",
        "Assets/Textures/dots.png",
        "Assets/Textures/stripes.png",
    ]


def left_out_of_the_game(editor):
    """The assets the Left Out tab of the Export window lists, as paths in the project."""
    return editor.find("exportWindow/leftOut").labels(role="cell")


def test_a_world_named_by_a_list_joins_the_game(editor):
    # The Export window, Cook Only: what the game would carry and what it leaves out. level10 is
    # in no field, so the cook leaves it out, with the world nothing names.
    editor.command("export.open")
    editor.tap("exportWindow/cook")
    editor.expect("exportWindow/tabs/segment[1]", label="Left Out · 9")
    editor.expect("exportWindow/steps/Cook", value="done")
    editor.tap("exportWindow/tabs/segment[1]")
    left_out = left_out_of_the_game(editor)
    assert "Assets/Levels/level10.world" in left_out and "Assets/Levels/spare.world" in left_out
    assert "Assets/Levels/level1.world" not in left_out

    # A row of the list shows its asset in the Content Browser: the folder of level10 opens there.
    editor.tap("exportWindow/leftOut/cell[%d]" % left_out.index("Assets/Levels/level10.world"))
    editor.call("show", settings="close")
    editor.expect("contentBrowser/files/level10.world")

    # A drop on the list of the Probe names the world. The game is made of the saved files, and
    # the window says what is not saved; Save All there clears the way.
    editor.tap("hierarchy/Player")
    editor.drag("contentBrowser/files/level10.world", "inspector/Probe/levels")
    editor.expect("inspector/Probe/levels/summary", label="3 items")
    editor.command("export.open")
    assert any(label.startswith("Not saved") for label in editor.find("exportWindow/notices").labels(role="label"))
    editor.tap("exportWindow/notices/saveAll")
    editor.expect("exportWindow/notices/saveAll", gone=True)

    # The next cook packs the world: it is not left out any more, the world nothing names still is.
    editor.tap("exportWindow/cook")
    editor.expect("exportWindow/tabs/segment[1]", label="Left Out · 8")
    editor.tap("exportWindow/tabs/segment[1]")
    left_out = left_out_of_the_game(editor)
    assert "Assets/Levels/level10.world" not in left_out
    assert "Assets/Levels/spare.world" in left_out
    report = editor.json(".Panda/Cooked/report.json")
    assert "Worlds/Assets/Levels/level10.pworld" in [file["path"] for file in report["files"]]


def wait_for_the_export(editor, seconds=900):
    """Waits for the Build step of the Export window; a step that failed fails the test with the output."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        states = {step.label: step.value for step in editor.find("exportWindow/steps").find_all(role="step")}
        if states["Build"] == "done":
            return
        if "failed" in states.values() or "canceled" in states.values():
            editor.tap("exportWindow/tabs/Log")
            raise AssertionError("the export ended %s:\n%s" % (states, "\n".join(editor.find("exportWindow/log").labels(role="cell")[-40:])))
        time.sleep(2)
    raise AssertionError("the export did not end in %d s" % seconds)


@pandatest.slow
@pandatest.scripts
def test_the_built_game_gets_the_fields(editor):
    # The whole export the way a user does it: the window, Build, the three steps, the game.
    editor.command("export.open")
    editor.tap("exportWindow/build")
    wait_for_the_export(editor)
    assert editor.find("exportWindow/result/game").label == "EditorUITest.app"
    editor.expect("exportWindow/result/run")
    log = editor.export("run", frames=30, limit=200)
    lines = [line for line in log.splitlines() if "PROBE " in line]
    assert lines, "the game logged no PROBE line:\n" + log
    values = dict(part.split("=", 1) for part in lines[0].split("PROBE ", 1)[1].split())
    assert values["count"] == "3"
    assert values["numbers"] == "[1,2,3]"
    assert values["levels"] == "[%d,%d]" % (
        asset_id(editor, "Assets/Levels/level1.world"),
        asset_id(editor, "Assets/Levels/level2.world"),
    )
    assert values["icon"] == str(asset_id(editor, "Assets/Textures/checker.png"))
