"""The start screen: where a project is made, opened again and forgotten."""

NO_PROJECT = True  # the editor of these tests starts without a project


def test_a_project_is_created_reopened_and_forgotten(editor):
    assert editor.status()["project"] is None
    editor.expect("No recent projects")

    # A new project is made of a name and a folder, and opens.
    editor.tap("New Project")
    editor.type_text("textField[0]", "Voyage", submit=False)
    editor.type_text("textField[1]", str(editor.scratch), submit=False)
    editor.tap("Create Project")
    editor.wait_project("Voyage")
    assert (editor.scratch / "Voyage" / ".Panda" / "project.json").is_file()
    editor.expect("hierarchy/Camera")  # the world of the template is open

    # Closed, it is the first of the recent projects, and a click on its row opens it again.
    editor.command("file.closeProject")
    editor.expect("Recent Projects")
    editor.tap("Voyage")
    editor.wait_project("Voyage")

    # Taken out of the list, it stays out: also after the session is written again.
    editor.command("file.closeProject")
    editor.tap("Remove from recent")
    editor.expect("Voyage", gone=True)
    editor.expect("No recent projects")
    editor.tap("New Project")
    editor.tap("Cancel")
    editor.expect("Voyage", gone=True)
    assert (editor.scratch / "Voyage").is_dir()  # forgotten, not deleted
