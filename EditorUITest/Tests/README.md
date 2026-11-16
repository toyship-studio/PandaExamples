# UI tests of the Panda editor

This project is what the tests of the editor run on: a small world, a script with a field of
every type, a few assets of every kind. A test starts PandaEditor on a copy of the project, uses
it the way a person does — clicks a row, types into a field, drags an asset onto a list, presses
Play — and checks what the editor shows and what it writes to the files.

The tests are not part of a build and nothing runs them by itself. Run them when the editor or
the engine has changed and you want to know that what worked still works.

## Running

```sh
python3 Tests/run.py                # every test, about a minute
python3 Tests/run.py inspector      # the tests whose file or name has "inspector" in it
python3 Tests/run.py test_rename    # one test
python3 Tests/run.py --slow         # also the tests that build the game (minutes)
python3 Tests/run.py --list         # what there is
python3 Tests/run.py --open         # no tests: the editor a test would get, kept open
```

In Zed: the tasks **UI Tests: Run All**, **Run This File**, **Run The Test Under The Cursor**.

Python 3.9 or newer, nothing else to install. The editor under test is found in this order:
`--editor <path>`, the `PANDA_EDITOR` variable, the build of the engine checked out next to this
repository (`../../Panda/bin/PandaEditor.app`).

```
  ok    test_inspector.test_rename                 0.9 s
  FAIL  test_hierarchy.test_duplicate_and_delete   3.1 s
        pandatest.ToolError: ui: `hierarchy/Crate` names 1 element(s), not 2
        see Tests/.results/test_hierarchy.test_duplicate_and_delete
```

A failed test leaves what it saw in `Tests/.results/<file>.<test>/`: `error.txt` (where it
stopped), `window.png` (the editor at that moment), `ui.json` (every element of the window),
`log.txt` (the log of the editor), `editor-output.txt` (what the process printed).

While the tests run, an editor window opens and closes for each of them. It does not take the
keyboard and does not hear the mouse: keep working. Do not close it by hand.

## How a run works

- **The project folder is never written to.** A run works on a copy in the temporary folder of
  the system (`<tmp>/panda-ui-tests/EditorUITest/project`). Before every test the copy is made
  equal to the project again: what the test before changed is put back, what it created is gone.
  The caches of the copy (the shaders, the script build) stay, so only the first run is slow.
- **Every test gets an editor of its own**, started with `--unattended` (the mouse and the
  keyboard of the machine do not reach it, its window has one size, it shows no native dialog),
  with empty user data and a free port for its MCP server. A file that says
  `SHARED_EDITOR = True` runs its tests in one editor, in the order they are written — for tests
  that change nothing in the project (`test_ui_elements.py`).
- **A test fails when the editor logs an error** during it, whatever the test checked. A test
  that means to cause one says `editor.expects_errors = True`.

## Writing a test

A test is a function `test_*(editor)` in a file `test_*.py` of this folder. `editor`
(`pandatest.Editor`) is the running editor:

```python
def test_position_reaches_the_world_file(editor):
    editor.tap("hierarchy/Crate")                                  # a click on a row of the Hierarchy
    editor.type_text("inspector/Transform/Position/X", "2.5")      # into a field of the form
    editor.expect("inspector/Transform/Position/X", value="2.50")  # what the field shows
    editor.save()
    assert editor.world().position("Crate") == (2.5, 0.0, 0.0)     # what the file holds
```

### Paths

A control is named by a path, not by where it is on the screen. A path is segments separated by
`/`; each segment names an element inside the one before it, at any depth; the first one —
anywhere in the window.

A segment is, in this order: the **id** of an element (given in the code of the editor:
`inspector`, `hierarchy`, `contentBrowser`, `toolbar`, `viewport`, the name of a script field);
its **label** (what it shows: the title of a row, of a button, of a tab; a button of an icon alone
goes by its tooltip); its **role** (`menu`, `dialog`, `popup`, `tree`, `numberField`, …).

| Path | What it names |
| --- | --- |
| `hierarchy/Crate` | the row of the entity in the Hierarchy |
| `inspector/Transform/Position/X` | a number field of the form of the selected entity |
| `inspector/Probe/numbers/Add Item` | the "+" of a list field of a script |
| `inspector/Probe/numbers.1/Remove Item` | the bin of the second item of that list |
| `contentBrowser/files/red.mat` | a file in the grid of the Content Browser |
| `contentBrowser/folders/Levels` | a folder in its tree |
| `toolbar/play` | the Play button |
| `viewport/scene` | the surface of the Scene |
| `tab:Player` | the tab named Player — `role:name` where a row is named Player too |
| `menu/Duplicate` | an item of the menu that is open |
| `hierarchy/Crate[1]` | the second of two entities named Crate |

To see what there is to name, ask the editor: `editor.ui()` is the whole window as elements,
`editor.ui("inspector")` a part of it. `python3 Tests/run.py --open` starts the editor a test
would get and keeps it open: its MCP server (the address is printed) answers `ui` for a coding
agent or a script while you write a test. A path that names nothing fails with the names that
are there:

```
No element `Nope` in `inspector/Transform`. There: `Position`, `Rotation`, `Scale`.
```

### What `editor` does

| | |
| --- | --- |
| `tap(path)`, `double_tap`, `right_tap`, `hover` | a gesture on the middle of the element; `at=(0.1, 0.5)` — on another place in it, in shares of its size |
| `drag(path, to)` | press on one element, release on another: a row onto a row, an asset onto a field |
| `scroll(path, dy)` | the wheel over the element |
| `type_text(path, text)` | replaces what a field holds and presses Enter |
| `key("Escape")`, `key(text="abc")` | keys to the element in focus |
| `command("edit.undo")` | a command of the editor by its id (the palette lists them) |
| `expect(path, value=…, label=…, selected=…, disabled=…, count=…, gone=True)` | waits for it to be so, fails with what is there instead |
| `find(path)`, `find_all(path)`, `exists(path)`, `value(path)` | the elements: `role`, `id`, `label`, `value`, `frame`, `selected`, `disabled`, `children` |
| `save()`, `reload()`, `play()`, `stop_game()`, `show(…)`, `open_world(…)`, `build()`, `export()` | what the buttons of the editor do |
| `status()`, `logs()`, `wait_log(text)`, `errors()` | the state and the log of the editor |
| `world()`, `json(file)`, `path(file)` | the files of the project copy: what the editor wrote |
| `call(tool, …)` | any tool of the MCP server of the editor |

A gesture waits for its element: for the form to be rebuilt, for a row out of sight to be
scrolled to. It fails when the element is disabled or something lies over it — a click never
lands on something else. So a test has no pauses.

Marks: `@pandatest.slow` — the test takes minutes and runs with `--slow` or when it is named;
`@pandatest.scripts` (or `SCRIPTS = True` in the file) — the C++ scripts of the project are built
before it.

### What to check

- **What the editor shows**: `expect` and `find` — the elements, not a picture.
- **What the editor writes**: `save()`, then the file. The files of a project are its contract,
  and a wrong edit shows there.
- **What the game gets**: the `Probe` script logs its fields when the game starts; `wait_log`
  reads the line in Play, `export("run")` in the built game.

What a test cannot tell: how a gesture feels, an animation, a sound. Those are looked at.

## The content of the project

`Tools/make_project.py` writes it — the worlds, the textures, the materials. Change the script
and run it; do not edit the generated files by hand. Ids are made of names, so they do not change
between runs. After a new texture or a change of a script class: run it, open the project in the
editor and build the scripts, run it again (the script says so itself).

| | |
| --- | --- |
| `Assets/world.world` | the start world: Camera, Sun, Sky, Crate (in the middle of the picture), Group with Coin A and Coin B, Player with the `Probe` script |
| `Assets/Levels/` | `level1`, `level2`, `level10` (the Probe names the first two in a list), `spare` (nothing names it) |
| `Assets/Textures/`, `Assets/Materials/` | three textures, two materials |
| `Assets/Frames/` | three numbered textures and a material: a folder to drop on a list |
| `Scripts/EditorUITest/src/Probe.*` | a script with a field of every type and a list of every kind |
