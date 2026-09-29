# Windows MTP Utilities

A small collection of Windows utilities for working with Android/MTP devices through the Windows Shell and Windows Portable Devices (WPD) APIs.

The repository currently contains two tools:

- **ShellPath** — converts Windows Shell/MTP GUID paths into readable Explorer-style paths.
- **FastMTP** — copies files directly from MTP/WPD devices to the local filesystem.

Together, they make it easier to work with Android devices from PowerShell, Command Prompt, or Python without relying entirely on Windows Explorer.

---

## Tools

### ShellPath

ShellPath converts Windows Shell namespace paths such as:

```text
::{20D04FE0-3AEA-1069-A2D8-08002B30309D}\...
```

into human-readable Explorer-style paths such as:

```text
This PC\OnePlus 12\Internal shared storage\Download\Models
```

Windows frequently represents MTP locations internally using Shell namespace paths rather than normal filesystem paths. ShellPath walks the Windows Shell hierarchy and reconstructs the readable path.

### FastMTP

FastMTP transfers files directly from an MTP/WPD device to the local filesystem.

Example source path:

```text
This PC\OnePlus 12\Internal shared storage\Download\model.gguf
```

Example destination:

```text
D:\Models\
```

FastMTP provides:

- direct WPD stream access,
- transfer progress,
- transfer speed,
- ETA,
- `.part` temporary files,
- final size verification,
- transfer-stage timing information.

---

## Requirements

### General

- Windows
- Python 3.10+ recommended
- Android or another compatible MTP/WPD device
- Device connected in **File Transfer / MTP** mode

### ShellPath

Requires:

```text
pywin32
```

### FastMTP

Requires a compatible `mtp-wpd` Python backend.

FastMTP uses the Windows Portable Devices API and therefore works only on Windows.

---

## Repository Structure

```text
Windows-MTP-Utilities/
├── FastMTP/
│   ├── fast_mtp.py
│   └── pyproject.toml
│
├── ShellPath/
│   ├── shellpath/
│   │   └── __init__.py
│   └── pyproject.toml
│
├── README.md
└── LICENSE
```

---

# ShellPath

## Installation

From the repository root:

```powershell
cd ShellPath
pip install .
```

For development:

```powershell
pip install -e .
```

---

## Command-Line Usage

After installation:

```powershell
phn_shellpath "<shell-path>"
```

Example:

```powershell
phn_shellpath "::{20D04FE0-3AEA-1069-A2D8-08002B30309D}\..."
```

Example output:

```text
This PC\OnePlus 12\Internal shared storage\Download\Models
```

The device should be:

- connected,
- unlocked,
- configured for USB File Transfer / MTP.

---

## Python Usage

```python
from shellpath import phn_shellpath

path = phn_shellpath(
    r"::{20D04FE0-3AEA-1069-A2D8-08002B30309D}\..."
)

print(path)
```

Example output:

```text
This PC\OnePlus 12\Internal shared storage\Download\Models
```

---

# FastMTP

## Installation

From the repository root:

```powershell
cd FastMTP
pip install .
```

For development:

```powershell
pip install -e .
```

Make sure the required `mtp-wpd` backend is installed and importable by Python.

---

## Command-Line Usage

After installation:

```powershell
fastmtp "<phone-path>" "<destination>"
```

Example:

```powershell
fastmtp "This PC\OnePlus 12\Internal shared storage\Download\model.gguf" "D:\Models\"
```

FastMTP also accepts a path without the leading `This PC`:

```powershell
fastmtp "OnePlus 12\Internal shared storage\Download\model.gguf" "D:\Models\"
```

If no arguments are supplied:

```powershell
fastmtp
```

the program asks interactively for the source and destination paths.

---

## Example Output

```text
======================================================================
FAST DIRECT WPD COPY
======================================================================
File        : model.gguf
Size        : 4.25 GiB
Destination : D:\Models\model.gguf
WPD buffer  : 64 KiB
Read request: 256 KiB

Copying...

 47.31% | 2.01 GiB / 4.25 GiB | 32.18 MB/s | ETA 71.2s
```

After completion, FastMTP also reports average transfer speed and the approximate time spent in the WPD read, buffer conversion, and local file-write stages.

---

## Transfer Safety

FastMTP writes incoming data to a temporary file first:

```text
filename.ext.part
```

Only after the transferred byte count matches the expected file size is the temporary file moved to the requested destination filename.

For example:

```text
model.gguf.part
        ↓
size verified
        ↓
model.gguf
```

If a transfer fails, the partial file is preserved instead of being presented as a successfully completed file.

---

## Using ShellPath and FastMTP Together

The two utilities can be used as part of the same workflow.

If Windows or another program provides an MTP location as a Shell GUID path:

```text
::{20D04FE0-3AEA-1069-A2D8-08002B30309D}\...
```

first resolve it using:

```powershell
phn_shellpath "<shell-path>"
```

This produces a readable path such as:

```text
This PC\OnePlus 12\Internal shared storage\Download\model.gguf
```

That path can then be supplied to FastMTP:

```powershell
fastmtp "This PC\OnePlus 12\Internal shared storage\Download\model.gguf" "D:\Models\"
```

So the overall workflow is:

```text
Windows Shell path
        │
        ▼
   ShellPath
        │
        ▼
Readable MTP path
        │
        ▼
    FastMTP
        │
        ▼
Local file
```

---

## Limitations

- Windows only
- MTP devices are not ordinary filesystem drives
- FastMTP currently focuses on copying files **from** an MTP/WPD device
- Transfer speed depends on the phone, USB connection, Windows WPD implementation, and device-side MTP implementation
- ShellPath requires the target MTP object to be visible to the Windows Shell
- FastMTP requires a compatible `mtp-wpd` backend

---

## License

See the `LICENSE` file for license information.
