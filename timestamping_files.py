# Last updated: 2025-05-05 19:29:09
import os
from datetime import datetime


def add_timestamp_to_py_files(directory="."):
    timestamp = f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)

                # Read original content
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.readlines()

                # Skip if already has a timestamp
                if content and content[0].startswith("# Last updated:"):
                    content = content[1:]

                # Prepend new timestamp
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(timestamp + "".join(content))


add_timestamp_to_py_files(".")

print("✅ Timestamps added to all .py files.")