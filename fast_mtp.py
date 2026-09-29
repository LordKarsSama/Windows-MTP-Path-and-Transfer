import os
import sys
import time
import ctypes


# ============================================================
# FIND LOCAL mtp-wpd SOURCE
# ============================================================

MTP_WPD_PATH = r"E:\Tools\mtp-wpd"

if os.path.isdir(MTP_WPD_PATH):
    sys.path.insert(0, MTP_WPD_PATH)

try:
    import mtp.win_access as mtp
except ModuleNotFoundError:
    print("ERROR: Could not find mtp-wpd.")
    print(f"Expected it here: {MTP_WPD_PATH}")
    sys.exit(1)


# ============================================================
# SETTINGS
# ============================================================

READ_SIZE = 256 * 1024
PROGRESS_INTERVAL = 0.5


# ============================================================
# HELPERS
# ============================================================

def human_size(n):
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(n)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024


def as_int(value):
    if hasattr(value, "value"):
        return int(value.value)
    return int(value)


def clean_phone_path(path):
    """
    Accepts things like:

    This PC\\OnePlus 12\\Internal shared storage\\Download\\file.bin

    or:

    OnePlus 12\\Internal shared storage\\Download\\file.bin
    """

    path = path.strip().strip('"').replace("/", "\\")

    parts = [
        p for p in path.split("\\")
        if p.strip()
    ]

    if parts and parts[0].lower() == "this pc":
        parts = parts[1:]

    if len(parts) < 3:
        raise ValueError(
            "Phone path should look like:\n"
            r"This PC\OnePlus 12\Internal shared storage\Download\file.ext"
        )

    device_name = parts[0]
    storage_name = parts[1]
    object_parts = parts[2:]

    return device_name, storage_name, object_parts


def find_device(name):
    devices = mtp.get_portable_devices()

    if not devices:
        raise RuntimeError(
            "No MTP device found. Unlock the phone and enable File Transfer."
        )

    # Exact match
    for device in devices:
        if getattr(device, "name", "").lower() == name.lower():
            return device

    # Partial match
    for device in devices:
        device_name = getattr(device, "name", "")
        description = getattr(device, "description", "")

        combined = f"{device_name} {description}".lower()

        if name.lower() in combined:
            return device

    if len(devices) == 1:
        print(
            f"Warning: device name did not exactly match '{name}'. "
            f"Using the only connected MTP device."
        )
        return devices[0]

    raise RuntimeError(f"Could not find device: {name}")


def find_storage(device, name):
    storages = device.get_content()

    for storage in storages:
        if storage.name.lower() == name.lower():
            return storage

    if len(storages) == 1:
        print(
            f"Warning: storage '{name}' not found exactly. "
            f"Using '{storages[0].name}'."
        )
        return storages[0]

    raise RuntimeError(f"Could not find storage: {name}")


def find_object(storage, parts):
    current = storage

    for part in parts:
        child = current.get_child(part)

        if child is None:
            raise FileNotFoundError(
                f"Could not find '{part}' in phone path."
            )

        current = child

    return current


# ============================================================
# FAST DIRECT WPD COPY
# ============================================================

def copy_from_phone(phone_file, destination):
    expected_size = int(phone_file.size)

    # If destination is a directory, preserve source filename.
    if (
        destination.endswith("\\")
        or destination.endswith("/")
        or os.path.isdir(destination)
    ):
        destination = os.path.join(
            destination,
            phone_file.name
        )

    destination = os.path.abspath(destination)

    os.makedirs(
        os.path.dirname(destination),
        exist_ok=True
    )

    temp_file = destination + ".part"

    if os.path.exists(temp_file):
        os.remove(temp_file)

    print()
    print("=" * 70)
    print("FAST DIRECT WPD COPY")
    print("=" * 70)

    print(f"File        : {phone_file.name}")
    print(f"Size        : {human_size(expected_size)}")
    print(f"Destination : {destination}")

    # --------------------------------------------------------
    # OPEN WPD STREAM DIRECTLY
    # --------------------------------------------------------

    resources = phone_file._content.Transfer()

    stgm_read = ctypes.c_uint(0)
    optimal_size = ctypes.pointer(ctypes.c_ulong(0))

    optimal_size, q_stream = resources.GetStream(
        phone_file._object_id,
        mtp.WPD_RESOURCE_DEFAULT,
        stgm_read,
        optimal_size
    )

    driver_size = int(
        optimal_size.contents.value
    )

    stream = q_stream.value

    print(
        f"WPD buffer   : {driver_size // 1024} KiB"
    )
    print(
        f"Read request : {READ_SIZE // 1024} KiB"
    )

    print()
    print("Copying...")
    print()

    total = 0

    read_ns = 0
    convert_ns = 0
    write_ns = 0

    start = time.perf_counter()
    last_print = start

    try:

        # buffering=0 = raw file write
        with open(temp_file, "wb", buffering=0) as out:

            while True:

                # ----------------------------
                # WPD READ
                # ----------------------------

                t0 = time.perf_counter_ns()

                buf, length = stream.RemoteRead(
                    READ_SIZE
                )

                t1 = time.perf_counter_ns()

                n = as_int(length)

                if n == 0:
                    break

                # ----------------------------
                # FAST NATIVE BUFFER COPY
                # ----------------------------

                chunk = ctypes.string_at(
                    buf,
                    n
                )

                t2 = time.perf_counter_ns()

                # ----------------------------
                # DIRECT FILE WRITE
                # ----------------------------

                out.write(chunk)

                t3 = time.perf_counter_ns()

                total += n

                read_ns += t1 - t0
                convert_ns += t2 - t1
                write_ns += t3 - t2

                now = time.perf_counter()

                if now - last_print >= PROGRESS_INTERVAL:

                    elapsed = now - start

                    speed = (
                        total / elapsed / 1_000_000
                    )

                    percent = (
                        total / expected_size * 100
                        if expected_size
                        else 0
                    )

                    remaining = (
                        expected_size - total
                    )

                    rate = (
                        total / elapsed
                        if elapsed
                        else 0
                    )

                    eta = (
                        remaining / rate
                        if rate > 0
                        else 0
                    )

                    print(
                        f"\r"
                        f"{percent:6.2f}% | "
                        f"{human_size(total)} / "
                        f"{human_size(expected_size)} | "
                        f"{speed:6.2f} MB/s | "
                        f"ETA {eta:6.1f}s",
                        end="",
                        flush=True
                    )

                    last_print = now

    except Exception:
        print()
        print()
        print("Transfer failed.")
        print(f"Partial file kept at:")
        print(temp_file)
        raise

    elapsed = time.perf_counter() - start

    print()
    print()

    if total != expected_size:
        raise IOError(
            f"SIZE MISMATCH!\n"
            f"Expected: {expected_size}\n"
            f"Received: {total}\n"
            f"Partial file: {temp_file}"
        )

    if os.path.exists(destination):
        os.remove(destination)

    os.replace(
        temp_file,
        destination
    )

    speed = total / elapsed / 1_000_000

    stage_total = (
        read_ns +
        convert_ns +
        write_ns
    )

    print("=" * 70)
    print("TRANSFER COMPLETE")
    print("=" * 70)

    print(f"Transferred : {human_size(total)}")
    print(f"Elapsed     : {elapsed:.2f} s")
    print(f"Average     : {speed:.2f} MB/s")

    if stage_total:

        print()
        print("Stage timings:")

        print(
            f"RemoteRead  : "
            f"{read_ns / 1e9:.3f}s "
            f"({read_ns / stage_total * 100:.1f}%)"
        )

        print(
            f"Conversion  : "
            f"{convert_ns / 1e9:.3f}s "
            f"({convert_ns / stage_total * 100:.1f}%)"
        )

        print(
            f"File write  : "
            f"{write_ns / 1e9:.3f}s "
            f"({write_ns / stage_total * 100:.1f}%)"
        )

    print()
    print(f"Saved to:")
    print(destination)


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) >= 3:

        phone_path = sys.argv[1]
        destination = sys.argv[2]

    else:

        print()
        print("FAST MTP / WPD COPY")
        print()

        phone_path = input(
            "Phone file path:\n> "
        ).strip()

        print()

        destination = input(
            "Destination:\n> "
        ).strip()

    phone_path = phone_path.strip('"')
    destination = destination.strip('"')

    device_name, storage_name, object_parts = (
        clean_phone_path(phone_path)
    )

    device = None

    try:

        print()
        print(f"Connecting to {device_name}...")

        device = find_device(
            device_name
        )

        storage = find_storage(
            device,
            storage_name
        )

        print(
            f"Storage: {storage.name}"
        )

        print(
            "Locating: "
            + "\\".join(object_parts)
        )

        phone_file = find_object(
            storage,
            object_parts
        )

        copy_from_phone(
            phone_file,
            destination
        )

    finally:

        if device is not None:
            try:
                device.close()
            except Exception:
                pass


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)

    except Exception as e:
        print()
        print("ERROR:")
        print(e)
        sys.exit(1)