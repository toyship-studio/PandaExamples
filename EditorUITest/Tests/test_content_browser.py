"""The Content Browser: the folders and the files of Assets, and what a click on one does."""

FILES = "contentBrowser/files"
FOLDERS = "contentBrowser/folders"


def names(editor):
    return editor.find(FILES).labels(role="cell")


def test_it_lists_assets_folders_first(editor):
    assert names(editor) == ["Frames", "Levels", "Materials", "Textures", "world.world"]
    assert editor.value(FILES) == "5"


def test_names_are_in_natural_order(editor):
    # level2 before level10: a number in a name is a number.
    editor.double_tap(FILES + "/Levels")
    editor.expect(FILES + "/level1.world")
    assert names(editor) == ["level1.world", "level2.world", "level10.world", "spare.world"]


def test_a_folder_opens_from_the_tree_and_from_the_grid(editor):
    editor.tap(FOLDERS + "/Textures")
    editor.expect(FOLDERS + "/Textures", selected=True)
    assert names(editor) == ["checker.png", "dots.png", "stripes.png"]
    editor.tap(FOLDERS + "/Assets")
    editor.double_tap(FILES + "/Materials")
    editor.expect(FOLDERS + "/Materials", selected=True)
    assert names(editor) == ["blue.mat", "red.mat"]


def test_a_click_on_an_asset_opens_its_form(editor):
    editor.double_tap(FILES + "/Materials")
    editor.tap(FILES + "/red.mat")
    editor.expect(FILES + "/red.mat", selected=True)
    editor.expect("tab:red.mat", selected=True)
    editor.expect("assetEditor")


def test_a_new_folder_and_a_new_material_are_files(editor):
    editor.right_tap(FILES, at=(0.9, 0.9))
    editor.tap("menu/New Material")
    editor.expect(FILES, value="6")
    created = [name for name in names(editor) if name.endswith(".mat")]
    assert len(created) == 1
    path = editor.path("Assets/" + created[0])
    assert path.is_file() and path.with_name(path.name + ".pmeta").is_file()
