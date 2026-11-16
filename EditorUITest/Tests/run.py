#!/usr/bin/env python3
"""Runs the UI tests of the Panda editor that lie next to this file.

    python3 Tests/run.py                 every test
    python3 Tests/run.py inspector       the tests whose file or name has "inspector" in it
    python3 Tests/run.py --list          what there is
    python3 Tests/run.py --slow          the tests that build the game too
    python3 Tests/run.py --open          no tests: an editor on a fresh copy, to look at while writing one

Every test gets an editor of its own on a fresh copy of the project (the project folder itself is
never written to). A file that says `SHARED_EDITOR = True` runs its tests in one editor, in the
order they are written. The exit code is 0 when everything passed. What a failed test leaves —
the picture of the window, its elements, the log — is in Tests/.results/<file>.<test>/.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import shutil
import signal
import sys
import time
import traceback
from pathlib import Path

import pandatest
from pandatest import PROJECT_DIR, RESULTS_DIR, TESTS_DIR, WORK_DIR, Editor


class Test:
    def __init__(self, module, function):
        self.module = module
        self.function = function
        self.name = "%s.%s" % (module.__name__, function.__name__)
        self.slow = getattr(function, "panda_slow", False)
        self.scripts = getattr(function, "panda_scripts", False) or getattr(module, "SCRIPTS", False)
        self.shared = getattr(module, "SHARED_EDITOR", False)


def discover() -> list[Test]:
    tests = []
    for file in sorted(TESTS_DIR.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        functions = [
            function
            for name, function in vars(module).items()
            if name.startswith("test_") and inspect.isfunction(function) and function.__module__ == module.__name__
        ]
        functions.sort(key=lambda function: function.__code__.co_firstlineno)
        tests += [Test(module, function) for function in functions]
    return tests


def select(tests: list[Test], filters: list[str], with_slow: bool) -> tuple[list[Test], list[Test]]:
    """The tests to run and the ones left out for being slow."""
    # A filter may come from an editor as the symbol under the cursor: "def test_rename(editor)".
    filters = [text.removeprefix("def ").split("(")[0].strip() for text in filters]
    filters = [text for text in filters if text]
    chosen, skipped = [], []
    for test in tests:
        if filters and not any(text in test.name for text in filters):
            continue
        named = any(text == test.function.__name__ or text == test.name for text in filters)
        if test.slow and not with_slow and not named:
            skipped.append(test)
        else:
            chosen.append(test)
    return chosen, skipped


class Session:
    """What a run of the tests shares: the editor under test and the place of the project copy."""

    def __init__(self, binary: Path):
        self.binary = binary
        self.project = WORK_DIR / "project" / PROJECT_DIR.name
        self.user_data = WORK_DIR / "userdata"
        self.editor_log = WORK_DIR / "editor.log"
        self.started: list[Editor] = []

    def new_editor(self) -> Editor:
        """An editor on the project as it is in the project folder, with nothing left of the run
        before: neither in the files nor in the settings of the editor."""
        pandatest.sync_project(PROJECT_DIR, self.project)
        shutil.rmtree(self.user_data, ignore_errors=True)
        editor = Editor(self.binary, self.project, self.user_data, self.editor_log)
        self.started.append(editor)
        editor.start()
        return editor

    def stop_editors(self) -> None:
        """No editor outlives the run, however the run ends."""
        for editor in self.started:
            if editor.alive():
                editor.stop()
        self.started.clear()

    def build_scripts(self) -> None:
        """The C++ scripts of the project, built in the copy before the tests that need them: an
        editor that starts afterwards loads the build with the world."""
        editor = self.new_editor()
        try:
            editor.build("scripts")
        finally:
            editor.stop()


def keep_evidence(test: Test, editor: Editor | None, error: str, session: Session) -> Path:
    """What a failed test leaves to look at."""
    folder = RESULTS_DIR / test.name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    (folder / "error.txt").write_text(error)
    if editor is not None and editor.alive():
        for name, take in (
            ("window.png", lambda: editor.screenshot(folder / "window.png")),
            ("ui.json", lambda: (folder / "ui.json").write_text(editor.call("ui"))),
            ("log.txt", lambda: (folder / "log.txt").write_text("\n".join(editor.logs(level="info")))),
        ):
            try:
                take()
            except Exception as problem:  # the editor may be the thing that broke
                (folder / (name + ".failed")).write_text(repr(problem))
    if session.editor_log.exists():
        shutil.copy(session.editor_log, folder / "editor-output.txt")
    return folder


def run_test(test: Test, editor: Editor) -> None:
    editor.expects_errors = False
    editor._log_start = editor.status()["log"]["next"]
    test.function(editor)
    if not editor.alive():
        raise AssertionError("The editor is gone: it exited or crashed during the test")
    errors = editor.errors()
    if errors and not editor.expects_errors:
        raise AssertionError("The editor logged errors:\n" + "\n".join(errors))


def open_editor(session: Session) -> int:
    """The editor a test would get, kept open: its MCP server is there to ask what a path names
    (`ui`), to try a gesture, to see what a test will see."""
    editor = session.new_editor()
    print("The editor runs on a copy of the project: %s" % session.project)
    print("Its MCP server: http://127.0.0.1:%d/mcp  (tools: ui, pointer, key, …)" % editor.port)
    print("The window does not hear the mouse and the keyboard. Ctrl+C closes it.")
    try:
        while editor.alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    session.stop_editors()
    return 0


def interrupt(*_):
    raise KeyboardInterrupt


def main() -> int:
    parser = argparse.ArgumentParser(description="UI tests of the Panda editor")
    parser.add_argument("filters", nargs="*", help="run the tests whose file.name has one of these in it")
    parser.add_argument("--editor", help="the PandaEditor executable to test (default: PANDA_EDITOR, then the engine checkout next to this repository)")
    parser.add_argument("--slow", action="store_true", help="also the tests that take minutes")
    parser.add_argument("--list", action="store_true", help="name the tests and leave")
    parser.add_argument("--open", action="store_true", help="run no test: start the editor on a fresh copy of the project and keep it until Ctrl+C")
    arguments = parser.parse_args()

    # A task runner stops a task with SIGTERM, and a run started in the background does not get
    # Ctrl+C: either way the run ends as an interrupted one — and takes its editor with it.
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)

    if arguments.open:
        return open_editor(Session(pandatest.find_editor(arguments.editor)))

    tests = discover()
    if arguments.list:
        for test in tests:
            print(test.name + ("  (slow)" if test.slow else ""))
        return 0
    chosen, skipped = select(tests, arguments.filters, arguments.slow)
    if not chosen and not skipped:
        print("No test matches %s" % " ".join(arguments.filters))
        return 2

    session = Session(pandatest.find_editor(arguments.editor))
    try:
        return run_tests(session, chosen, skipped)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    finally:
        session.stop_editors()


def run_tests(session: Session, chosen: list[Test], skipped: list[Test]) -> int:
    shutil.rmtree(RESULTS_DIR, ignore_errors=True)
    print("editor   %s" % session.binary)
    print("project  %s" % session.project)
    print()

    started = time.time()
    if any(test.scripts for test in chosen):
        begun = time.time()
        print("  ...   building the scripts of the project", end="", flush=True)
        try:
            session.build_scripts()
        except Exception as problem:
            print("\n\nThe scripts did not build:\n%s" % problem)
            return 1
        print("  %.1f s" % (time.time() - begun))

    passed, failed = [], []
    shared: Editor | None = None
    shared_module = None
    width = max(len(test.name) for test in chosen)
    for index, test in enumerate(chosen):
        begun = time.time()
        editor: Editor | None = None
        error = None
        try:
            if test.shared:
                if shared is None or shared_module is not test.module or not shared.alive():
                    if shared is not None:
                        shared.stop()
                    shared = session.new_editor()
                    shared_module = test.module
                editor = shared
            else:
                if shared is not None:
                    shared.stop()
                    shared = None
                editor = session.new_editor()
            run_test(test, editor)
        except Exception:
            error = traceback.format_exc()
        seconds = time.time() - begun
        if error is None:
            passed.append(test)
            print("  ok    %-*s  %5.1f s" % (width, test.name, seconds))
        else:
            failed.append(test)
            folder = keep_evidence(test, editor, error, session)
            print("  FAIL  %-*s  %5.1f s" % (width, test.name, seconds))
            for line in error.strip().splitlines()[-1].splitlines():
                print("        " + line)
            print("        see %s" % folder.relative_to(PROJECT_DIR))
        last_of_shared = test.shared and (index + 1 == len(chosen) or chosen[index + 1].module is not test.module)
        if editor is not None and (not test.shared or last_of_shared or error is not None):
            editor.stop()
            if editor is shared:
                shared = None
    for test in skipped:
        print("  skip  %-*s  slow: pass --slow or name it" % (width, test.name))

    print()
    summary = "%d passed" % len(passed)
    if failed:
        summary += ", %d failed" % len(failed)
    if skipped:
        summary += ", %d skipped" % len(skipped)
    print("%s in %.1f s" % (summary, time.time() - started))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
