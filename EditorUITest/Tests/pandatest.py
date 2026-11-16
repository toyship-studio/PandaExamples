"""The client side of the UI tests of the Panda editor.

A test is a function `test_*(editor)` in a file `test_*.py` next to this one. `editor` is a
running PandaEditor with a fresh copy of this project open in it; the test drives it through its
MCP server, the way an agent does: `ui` reads the window as elements, `pointer` and `key` use a
control by its path, `save`, `play`, `export` do what the buttons do. What a test checks is what
the editor shows (the elements) and what it writes (the files of the project copy).

    def test_rename(editor):
        editor.tap("hierarchy/Crate")
        editor.type_text("inspector/name", "Box")
        editor.expect("hierarchy/Box")
        editor.save()
        assert "Box" in editor.world().names()

Run the tests with `python3 Tests/run.py` (see README.md). Only the standard library is used.
"""

from __future__ import annotations

import fnmatch
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TESTS_DIR.parent
RESULTS_DIR = TESTS_DIR / ".results"
# Where the copy of the project a run works on lives: one place, so that what the editor and the
# builds make there (the shader cache, the script build) is warm on the next run.
WORK_DIR = Path(tempfile.gettempdir()) / "panda-ui-tests" / PROJECT_DIR.name


class ToolError(AssertionError):
    """A tool of the editor ran and failed: the text is what the editor said."""


# ------------------------------------------------------------------ the copy of the project

# What the editor and the builds make in a project folder. The copy keeps it between runs; it is
# never taken from the project and never deleted.
_CACHES = (
    ".Panda/Shaders",
    ".Panda/Textures",
    ".Panda/Cooked",
    ".Panda/ScriptCache",
    ".Panda/SaveData",
    "Export/build",
)
# The same, by the name of a file or a folder wherever it lies (the script library is built into
# Scripts/<project>/bin).
_CACHE_NAMES = ("cmake-build-*", "bin", ".ShaderCache", "*.pdb")
# What is in the project folder and is not the project.
_NOT_PROJECT = ("Tests", ".git", ".idea", ".DS_Store", "__pycache__", ".Panda/session.json")


def _is_cache(relative: PurePosixPath) -> bool:
    text = relative.as_posix()
    if any(text == cache or text.startswith(cache + "/") for cache in _CACHES):
        return True
    return any(fnmatch.fnmatch(part, pattern) for part in relative.parts for pattern in _CACHE_NAMES)


def _is_not_project(relative: PurePosixPath) -> bool:
    text = relative.as_posix()
    if any(text == name or text.startswith(name + "/") for name in _NOT_PROJECT if "/" in name):
        return True
    return any(part == name for part in relative.parts for name in _NOT_PROJECT if "/" not in name)


def _files(root: Path, keep) -> dict[PurePosixPath, Path]:
    """Every file under `root` that `keep` accepts, by its path relative to `root`."""
    found = {}
    for folder, folders, names in os.walk(root):
        relative_folder = PurePosixPath(Path(folder).relative_to(root).as_posix())
        folders[:] = [name for name in folders if keep(relative_folder / name)]
        for name in names:
            relative = relative_folder / name
            if keep(relative):
                found[relative] = Path(folder) / name
    return found


def sync_project(source: Path = PROJECT_DIR, target: Path | None = None) -> Path:
    """Makes `target` the project as it is in `source`: what a test before changed is put back,
    what it added is gone. The caches of the copy stay. A file that did not change is not
    touched, so a build of the copy sees nothing new."""
    target = target or WORK_DIR / "project" / PROJECT_DIR.name
    target.mkdir(parents=True, exist_ok=True)
    wanted = _files(source, lambda relative: not _is_cache(relative) and not _is_not_project(relative))
    present = _files(target, lambda relative: not _is_cache(relative))
    for relative, path in present.items():
        if relative not in wanted:
            path.unlink()
    for relative, path in wanted.items():
        copy = target / relative
        if copy.exists():
            ours, theirs = path.stat(), copy.stat()
            if ours.st_size == theirs.st_size and int(ours.st_mtime) == int(theirs.st_mtime):
                continue
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copy)
    # Folders a test made and nothing is left in.
    for folder, folders, names in os.walk(target, topdown=False):
        relative = PurePosixPath(Path(folder).relative_to(target).as_posix())
        if folder != str(target) and not folders and not names and not _is_cache(relative):
            try:
                os.rmdir(folder)
            except OSError:
                pass
    return target


def find_editor(explicit: str | None = None) -> Path:
    """The editor to test: `--editor`, PANDA_EDITOR, or the build of the engine checked out next
    to the repository of this project."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("PANDA_EDITOR"):
        candidates.append(Path(os.environ["PANDA_EDITOR"]))
    engine = PROJECT_DIR.parent.parent / "Panda" / "bin"
    candidates += [
        engine / "PandaEditor.app" / "Contents" / "MacOS" / "PandaEditor",
        engine / "PandaEditor.exe",
        engine / "PandaEditor",
        Path("/Applications/PandaEditor.app/Contents/MacOS/PandaEditor"),
    ]
    for candidate in candidates:
        if candidate.is_dir() and candidate.suffix == ".app":
            candidate = candidate / "Contents" / "MacOS" / "PandaEditor"
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit(
        "PandaEditor was not found. Pass --editor <path> or set PANDA_EDITOR to the executable "
        "(…/PandaEditor.app/Contents/MacOS/PandaEditor)."
    )


# ------------------------------------------------------------------ what the editor shows


class Element:
    """An element of the window, as the `ui` tool of the editor answers: what a control is, what
    it shows and holds, where it is, and the elements in it."""

    def __init__(self, data: dict):
        self.data = data
        self.role: str = data.get("role", "")
        self.id: str = data.get("id", "")
        self.label: str = data.get("label", "")
        self.value: str = data.get("value", "")
        self.frame: list[int] = data.get("frame", [0, 0, 0, 0])
        self.disabled: bool = data.get("disabled", False)
        self.selected: bool = data.get("selected", False)
        self.focused: bool = data.get("focused", False)
        self.out_of_sight: bool = data.get("outOfSight", False)
        self.children = [Element(child) for child in data.get("children", [])]

    @property
    def name(self) -> str:
        return self.id or self.label or self.role

    def all(self):
        """The element and everything in it, in the order of the tree."""
        yield self
        for child in self.children:
            yield from child.all()

    def find_all(self, role: str | None = None, label: str | None = None, id: str | None = None) -> list["Element"]:
        return [
            element
            for element in self.all()
            if element is not self
            and (role is None or element.role == role)
            and (label is None or element.label == label)
            and (id is None or element.id == id)
        ]

    def labels(self, role: str | None = None) -> list[str]:
        """The labels of the elements in this one — of one role, when it is given."""
        return [element.label for element in self.find_all(role=role) if element.label]

    def __repr__(self) -> str:
        text = self.role
        if self.id:
            text += " #" + self.id
        if self.label:
            text += ' "%s"' % self.label
        if self.value:
            text += " = " + self.value
        return "<%s>" % text


# ------------------------------------------------------------------ what the editor writes


class World:
    """A world file of the project copy, as the editor saved it."""

    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text())

    def names(self) -> list[str]:
        return [entity["tagComponent"]["tag"] for entity in self.data["entities"]]

    def entity(self, name: str) -> dict:
        found = [entity for entity in self.data["entities"] if entity["tagComponent"]["tag"] == name]
        assert len(found) == 1, "%s: %d entities are named %r (%s)" % (self.path.name, len(found), name, self.names())
        return found[0]

    def has(self, name: str) -> bool:
        return name in self.names()

    def position(self, name: str) -> tuple[float, float, float]:
        position = self.entity(name)["transformComponent"]["position"]
        return (position["x"], position["y"], position["z"])

    def parent(self, name: str) -> str | None:
        parent = self.entity(name)["relationshipComponent"]["parent"]
        for entity in self.data["entities"]:
            if entity["id"] == parent:
                return entity["tagComponent"]["tag"]
        return None

    def children(self, name: str) -> list[str]:
        ids = self.entity(name)["relationshipComponent"]["children"]
        by_id = {entity["id"]: entity["tagComponent"]["tag"] for entity in self.data["entities"]}
        return [by_id[child] for child in ids if child in by_id]

    def scripts(self, name: str) -> list[str]:
        return [script["name"] for script in self.entity(name)["scriptListComponent"]["scripts"]]

    def fields(self, name: str, script: str) -> dict:
        """The values of the published fields of a script of an entity, by the name of the field."""
        for record in self.entity(name)["scriptListComponent"]["scripts"]:
            if record["name"] == script:
                return {field["name"]: field["value"] for field in record.get("scriptFields", [])}
        raise AssertionError("%s has no script %r (%s)" % (name, script, self.scripts(name)))


# ------------------------------------------------------------------ the editor


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class Editor:
    """A PandaEditor that runs for a test: started unattended (the mouse and the keyboard of the
    machine do not reach it, its window has one size, it asks nothing) on a copy of the project,
    with user data of its own, and driven through its MCP server."""

    def __init__(self, binary: Path, project: Path, user_data: Path, log_file: Path):
        self.binary = binary
        self.project = project
        self.user_data = user_data
        self.log_file = log_file
        self.port = 0
        self.process: subprocess.Popen | None = None
        self.expects_errors = False  # the test means to make the editor log an error
        self._log_start = 0
        self._call_id = 0

    # ---------------------------------------------------------------- the process

    def start(self, timeout: float = 60.0) -> None:
        self.port = _free_port()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log = open(self.log_file, "wb")
        self.process = subprocess.Popen(
            [
                str(self.binary),
                "--project", str(self.project),
                "--user-data", str(self.user_data),
                "--mcp", str(self.port),
                "--unattended",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        deadline = time.time() + timeout
        while True:
            if self.process.poll() is not None:
                raise RuntimeError("The editor exited at once (code %s). Its log: %s" % (self.process.returncode, self.log_file))
            try:
                state = self.status()
                if state.get("state") == "edit" and state.get("project"):
                    break
            except (OSError, http.client.HTTPException, ToolError, ValueError):
                pass
            if time.time() > deadline:
                self.stop()
                raise RuntimeError("The editor did not open the project in %d s. Its log: %s" % (timeout, self.log_file))
            time.sleep(0.1)
        self._log_start = self.status()["log"]["next"]

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            try:
                self.call("quit", discard=True, _timeout=5)
            except Exception:
                pass
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    # ---------------------------------------------------------------- the MCP server

    def call(self, tool: str, _timeout: float = 60.0, _image: bool = False, **arguments):
        """Calls a tool of the editor. Answers with its text — with (text, png bytes) when
        `_image` — and raises ToolError when the tool says it failed. An argument that is None is
        left out."""
        self._call_id += 1
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": self._call_id,
                "method": "tools/call",
                "params": {"name": tool, "arguments": {key: value for key, value in arguments.items() if value is not None}},
            }
        )
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=_timeout)
        try:
            connection.request(
                "POST", "/mcp", body=body,
                headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            )
            raw = connection.getresponse().read()
        finally:
            connection.close()
        answer = json.loads(raw)
        if "error" in answer:
            raise ToolError("%s: %s" % (tool, answer["error"]))
        result = answer["result"]
        text = "\n".join(block["text"] for block in result["content"] if block["type"] == "text")
        if result.get("isError"):
            raise ToolError("%s: %s" % (tool, text))
        if _image:
            import base64

            images = [base64.b64decode(block["data"]) for block in result["content"] if block["type"] == "image"]
            return text, (images[0] if images else b"")
        return text

    # ---------------------------------------------------------------- reading the window

    def ui(self, path: str | None = None, **arguments) -> list[Element]:
        """The elements `path` names (the whole window without it), each with what is in it."""
        return [Element(data) for data in json.loads(self.call("ui", path=path, **arguments))["elements"]]

    def find(self, path: str, wait: float | None = None) -> Element:
        """The one element `path` names; waits for it to be there."""
        return self.ui(path, count=1, wait=wait)[0]

    def find_all(self, path: str) -> list[Element]:
        """The elements `path` names right now; none is an answer too."""
        try:
            return self.ui(path, wait=0)
        except ToolError:
            return []

    def exists(self, path: str) -> bool:
        return bool(self.find_all(path))

    def value(self, path: str) -> str:
        return self.find(path).value

    def expect(
        self,
        path: str,
        value: str | None = None,
        label: str | None = None,
        count: int | None = None,
        gone: bool = False,
        selected: bool | None = None,
        disabled: bool | None = None,
        wait: float | None = None,
    ) -> Element | None:
        """Waits for what `path` names to be there — and, when asked, to hold a value, show a
        label, be that many, be gone, be selected or disabled. Fails with what is there instead."""
        if gone:
            self.ui(path, gone=True, wait=wait)
            return None
        if count is not None:
            self.ui(path, count=count, wait=wait)
            return None
        deadline = time.time() + (2.0 if wait is None else wait)
        while True:
            element = self.ui(path, count=1, value=value, label=label, wait=wait)[0]
            wrong = []
            if selected is not None and element.selected != selected:
                wrong.append("is%s selected" % ("" if element.selected else " not"))
            if disabled is not None and element.disabled != disabled:
                wrong.append("is%s disabled" % ("" if element.disabled else " not"))
            if not wrong:
                return element
            if time.time() > deadline:
                raise AssertionError("`%s` %s" % (path, " and ".join(wrong)))
            time.sleep(0.03)

    # ---------------------------------------------------------------- using the window

    def tap(self, path: str, at: tuple[float, float] | None = None, **arguments) -> None:
        """A click on the element `path` names: on its middle, or on `at` — shares of its size."""
        self.call("pointer", target=path, at=list(at) if at else None, **arguments)

    def double_tap(self, path: str, **arguments) -> None:
        self.call("pointer", action="doubleClick", target=path, **arguments)

    def right_tap(self, path: str, **arguments) -> None:
        self.call("pointer", action="rightClick", target=path, **arguments)

    def hover(self, path: str, **arguments) -> None:
        self.call("pointer", action="move", target=path, **arguments)

    def drag(
        self,
        path: str,
        to: str,
        at: tuple[float, float] | None = None,
        to_at: tuple[float, float] | None = None,
        **arguments,
    ) -> None:
        """Presses on the element `path` names, moves to the one `to` names and releases there."""
        self.call(
            "pointer", action="drag", target=path, toTarget=to,
            at=list(at) if at else None, toAt=list(to_at) if to_at else None, **arguments,
        )

    def scroll(self, path: str, dy: float, dx: float = 0.0, **arguments) -> None:
        self.call("pointer", action="scroll", target=path, dx=dx, dy=dy, **arguments)

    def key(self, key: str | None = None, text: str | None = None, target: str | None = None, **modifiers) -> None:
        """Keys to the element in focus — to `target`, clicked first, when it is given."""
        self.call("key", key=key, text=text, target=target, **modifiers)

    def type_text(self, path: str, text: str, submit: bool = True) -> None:
        """Replaces what a field holds: a click, select all, the text and — unless told not to — Enter."""
        command = sys.platform == "darwin"
        self.key("a", target=path, super=command or None, ctrl=(not command) or None)
        self.key("Enter" if submit else None, text=text)

    def command(self, id: str) -> None:
        """Runs a command of the editor the way the palette does: "edit.undo", "file.saveAll", …"""
        self.call("command", id=id)

    # ---------------------------------------------------------------- what the buttons do

    def status(self) -> dict:
        return json.loads(self.call("status", _timeout=10))

    def save(self) -> str:
        return self.call("save")

    def reload(self, discard: bool = False) -> str:
        return self.call("reload", discard=discard or None)

    def play(self) -> str:
        return self.call("play")

    def stop_game(self) -> str:
        return self.call("stop")

    def show(self, **what) -> str:
        """Brings a part of the editor in front: panel="output", entity="Crate", asset="Assets/…",
        settings="project"."""
        return self.call("show", **what)

    def open_world(self, path: str) -> str:
        return self.call("open_world", path=path)

    def build(self, target: str = "scripts", action: str = "build") -> str:
        return self.call("build", target=target, action=action, _timeout=1800)

    def export(self, action: str = "cook", **arguments) -> str:
        return self.call("export", action=action, _timeout=1800, **arguments)

    def screenshot(self, file: Path, view: str = "window") -> None:
        file.parent.mkdir(parents=True, exist_ok=True)
        self.call("screenshot", view=view, file=str(file), image=False)

    def logs(self, level: str = "info", since: int | None = None, limit: int = 1000) -> list[str]:
        """The lines of the log of the editor, the oldest first."""
        return self.call("logs", level=level, since=since, limit=limit).splitlines()[1:]

    def errors(self) -> list[str]:
        """The errors the editor has logged since the test began."""
        return self.logs(level="error", since=self._log_start)

    def wait_log(self, text: str, timeout: float = 10.0) -> str:
        """Waits for a line of the log, since the test began, that has `text` in it."""
        deadline = time.time() + timeout
        while True:
            lines = self.logs(level="trace", since=self._log_start)
            for line in lines:
                if text in line:
                    return line
            if time.time() > deadline:
                raise AssertionError("The log has no line with %r. Its last lines:\n%s" % (text, "\n".join(lines[-15:])))
            time.sleep(0.1)

    # ---------------------------------------------------------------- the files of the copy

    def path(self, relative: str) -> Path:
        return self.project / relative

    def read(self, relative: str) -> str:
        return self.path(relative).read_text()

    def json(self, relative: str):
        return json.loads(self.read(relative))

    def world(self, relative: str = "Assets/world.world") -> World:
        return World(self.path(relative))


# ------------------------------------------------------------------ marks of a test


def slow(function):
    """The test takes minutes (it builds the game): it runs with --slow, or when it is named."""
    function.panda_slow = True
    return function


def scripts(function):
    """The test needs the C++ scripts of the project built: the run builds them once before it."""
    function.panda_scripts = True
    return function
