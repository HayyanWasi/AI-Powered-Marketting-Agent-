import glob
import os


def patch_validation():
    services_dir = (
        r"d:\Hayyan\Projects\AI-powered-marketing-agent\backend\src\modules\ai_generation\services"
    )
    files = glob.glob(os.path.join(services_dir, "*.py"))

    for filepath in files:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # We want to replace lines like:
        # if image.get(field) is None:
        # with:
        # if image.get(field) is None:

        import re

        # Find exactly `if not <var>.get(field):`
        # and replace with `if <var>.get(field) is None:`
        # Note: some use `if strategy.get(field) is None:`, etc.
        pattern = r"if not ([a-zA-Z0-9_]+)\.get\((['\"]?field['\"]?)\):"
        replacement = r"if \1.get(\2) is None:"

        new_content, count = re.subn(pattern, replacement, content)

        if count > 0:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Patched {os.path.basename(filepath)} ({count} replacements)")


if __name__ == "__main__":
    patch_validation()
