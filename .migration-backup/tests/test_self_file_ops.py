from pathlib import Path


def test_add_edit_delete_repo_file():
    root = Path(__file__).resolve().parent.parent
    test_dir = root / "self_test_artifacts"
    test_dir.mkdir(exist_ok=True)
    f = test_dir / "temp_test.txt"
    try:
        # Add
        f.write_text("hello\n", encoding="utf-8")
        assert f.exists()
        assert f.read_text(encoding="utf-8") == "hello\n"

        # Edit
        f.write_text("edited\n", encoding="utf-8")
        assert f.read_text(encoding="utf-8") == "edited\n"

        # Delete
        f.unlink()
        assert not f.exists()
    finally:
        # cleanup directory if empty
        try:
            if test_dir.exists():
                for p in test_dir.iterdir():
                    try:
                        if p.is_file():
                            p.unlink()
                    except Exception:
                        pass
                # remove dir if empty
                try:
                    test_dir.rmdir()
                except Exception:
                    pass
        except Exception:
            pass
