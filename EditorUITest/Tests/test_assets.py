"""The form of an asset: a material is a document of its own, saved into its own file."""

RED = "Assets/Materials/red.mat"


def inputs(editor):
    return {entry["name"]: entry["value"] for entry in editor.json(RED)["inputs"]}


def open_red(editor):
    editor.show(asset=RED)
    editor.expect("tab:red.mat", selected=True)
    editor.expect("assetEditor/Roughness Factor/numberField", value="0.5")


def test_a_material_field_reaches_its_file(editor):
    open_red(editor)
    editor.type_text("assetEditor/Roughness Factor/numberField", "0.25")
    # The material has an edit its file does not have; the world is not touched.
    editor.expect("tab:red.mat", value="unsaved")
    assert editor.status()["worlds"][0]["unsaved"] is False
    assert inputs(editor)["roughnessFactor"] == 0.5
    editor.save()
    editor.expect("tab:red.mat", value="")
    assert inputs(editor)["roughnessFactor"] == 0.25


def test_a_toggle_and_a_choice_of_a_material(editor):
    open_red(editor)
    editor.tap("assetEditor/Double Sided/toggle")  # below the fold: the form scrolls to it
    editor.expect("assetEditor/Double Sided/toggle", value="on")
    editor.tap("assetEditor/Alpha Mode/combobox")
    choices = editor.find("popup/list").labels(role="row")
    assert choices[0] == "Opaque" and len(choices) > 1
    editor.tap("popup/list/" + choices[1])
    editor.expect("assetEditor/Alpha Mode/combobox", value=choices[1])
    editor.save()
    saved = inputs(editor)
    assert saved["doubleSided"] == 1
    assert saved["alphaMode"] == 1


def test_undo_belongs_to_the_document_in_front(editor):
    # An edit of the world, then an edit of the material: Undo in the tab of the material takes
    # back the edit of the material and leaves the world alone.
    editor.tap("hierarchy/Crate")
    editor.type_text("inspector/Transform/Position/X", "2")
    open_red(editor)
    editor.type_text("assetEditor/Roughness Factor/numberField", "0.75")
    editor.command("edit.undo")
    editor.expect("assetEditor/Roughness Factor/numberField", value="0.5")
    editor.save()
    assert inputs(editor)["roughnessFactor"] == 0.5
    assert editor.world().position("Crate") == (2.0, 0.0, 0.0)
