import os
import sys

if os.name == "nt":
    import pythoncom
    import win32com.client


__all__ = ["phn_shellpath"]


def _norm(path):
    return (
        str(path)
        .strip()
        .strip('"')
        .replace("/", "\\")
        .rstrip("\\")
        .lower()
    )


def phn_shellpath(path):
    """
    Convert a Windows phone/MTP Shell path into a human-readable Explorer path.

    Example:
        ::{20D04FE0-...}\\...\\{6AB94...}

    becomes:
        This PC\\OnePlus 12\\Internal shared storage\\Download\\file.bin
    """

    if os.name != "nt":
        raise OSError("phn_shellpath() only works on Windows.")

    if not isinstance(path, str):
        raise TypeError("path must be a string.")

    path = path.strip().strip('"')

    if not path:
        raise ValueError("path cannot be empty.")

    # Already human-readable.
    if _norm(path) == "this pc" or _norm(path).startswith("this pc\\"):
        return path.replace("/", "\\").rstrip("\\")

    target = _norm(path)

    pythoncom.CoInitialize()

    try:
        shell = win32com.client.Dispatch("Shell.Application")
        current = shell.NameSpace(17)  # This PC

        if current is None:
            raise RuntimeError("Could not open the Windows 'This PC' Shell namespace.")

        names = [str(current.Title)]
        visited = set()

        for _ in range(128):

            matches = []

            try:
                items = current.Items()
            except Exception as e:
                raise RuntimeError(
                    "Could not enumerate the current Windows Shell folder."
                ) from e

            for item in items:
                try:
                    item_path = _norm(item.Path)

                    if not item_path:
                        continue

                    if target == item_path or target.startswith(item_path + "\\"):
                        matches.append((len(item_path), item))

                except Exception:
                    continue

            if not matches:
                raise ValueError(
                    "Could not resolve the MTP Shell path. "
                    "Make sure the phone is connected, unlocked, "
                    "and USB mode is set to File Transfer."
                )

            # Choose the deepest matching child.
            _, item = max(matches, key=lambda x: x[0])

            item_path = _norm(item.Path)

            if item_path in visited:
                raise RuntimeError(
                    "Windows Shell traversal entered a loop."
                )

            visited.add(item_path)
            names.append(str(item.Name))

            if item_path == target:
                return "\\".join(names)

            try:
                current = item.GetFolder
            except Exception as e:
                raise ValueError(
                    f"Reached '{item.Name}', but it is not a browsable Shell folder."
                ) from e

            if current is None:
                raise ValueError(
                    f"Reached '{item.Name}', but Windows could not open it."
                )

        raise RuntimeError("Shell path exceeded maximum traversal depth.")

    finally:
        pythoncom.CoUninitialize()


def main():
    if len(sys.argv) != 2:
        print("Usage: phn_shellpath <path>", file=sys.stderr)
        sys.exit(2)

    try:
        print(phn_shellpath(sys.argv[1]))

    except Exception as e:
        print(f"phn_shellpath: {e}", file=sys.stderr)
        sys.exit(1)