"""The game as it ships: what a cook packs, and what the built game gets."""

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


def test_a_world_named_by_a_list_joins_the_game(editor):
    # level10 is in no field: a drop on the list of the Probe names it, and the next cook packs it.
    editor.tap("hierarchy/Player")
    editor.double_tap("contentBrowser/files/Levels")
    editor.drag("contentBrowser/files/level10.world", "inspector/Probe/levels")
    editor.expect("inspector/Probe/levels/summary", label="3 items")
    editor.save()
    editor.export("cook")
    report = editor.json(".Panda/Cooked/report.json")
    assert "Worlds/Assets/Levels/level10.pworld" in [file["path"] for file in report["files"]]
    assert "Assets/Levels/level10.world" not in [file["path"] for file in report["unused"]]


@pandatest.slow
@pandatest.scripts
def test_the_built_game_gets_the_fields(editor):
    editor.export("cook")
    editor.build("export")
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
