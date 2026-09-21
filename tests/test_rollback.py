import json
import shlex
import shutil
import subprocess

import pytest

from agent_undo.rollback import RollbackGenerator


class FakeJournal:
    def __init__(self, operations):
        self.operations = operations

    def get_ops_since(self, session_id, target_op_id):
        return self.operations


def generate_script(path, content_before, op_id=7):
    op = {
        "id": op_id,
        "op_type": "file-write",
        "path": path,
        "content_before": content_before,
    }
    return RollbackGenerator(FakeJournal([op])).generate("test-session", target_op_id=0)


@pytest.mark.parametrize(
    "path",
    [
        "/tmp/file with spaces.txt",
        "/tmp/file's.txt",
        '/tmp/file"with-quotes.txt',
        "/tmp/file$var`tick`\\name.txt",
        "/tmp/file\nwith-newline.txt",
    ],
)
def test_file_write_paths_are_shell_quoted_and_comments_are_single_line(path):
    script = generate_script(path, "previous owner's contents")

    assert f"if [ -f {shlex.quote(path)} ]; then" in script
    assert f"cat > {shlex.quote(path)} << 'AGENT_UNDO_EOF_7'" in script
    assert f"# [file-write] {json.dumps(path)}" in script
    assert "previous owner's contents" in script


def test_heredoc_delimiter_avoids_lines_in_file_contents():
    content_before = "AGENT_UNDO_EOF_7\nAGENT_UNDO_EOF_7_1\nprevious contents"

    script = generate_script("/tmp/document.txt", content_before)

    assert "cat > /tmp/document.txt << 'AGENT_UNDO_EOF_7_2'" in script
    assert content_before in script
    assert script.count("AGENT_UNDO_EOF_7_2") == 2


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is required for syntax validation")
def test_generated_scripts_pass_bash_syntax_validation():
    bash = shutil.which("bash")
    paths = [
        "/tmp/file with spaces.txt",
        "/tmp/file's.txt",
        '/tmp/file"with-quotes.txt',
        "/tmp/file$var`tick`\\name.txt",
    ]

    for path in paths:
        script = generate_script(path, "previous owner's contents\nAGENT_UNDO_EOF_7")
        result = subprocess.run(
            [bash, "-n"], input=script.encode(), capture_output=True, check=False
        )
        assert result.returncode == 0, result.stderr.decode()
