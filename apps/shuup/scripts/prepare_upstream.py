"""Verify the upstream wheel and repair only its malformed dependency metadata."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile


def normalize_wheel(payload, expected_sha256):
    """Verify original bytes, split toml/pytz requirements, and rebuild wheel RECORD hashes."""
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("Shuup wheel checksum differs from the source lock. Build stopped.")
    with zipfile.ZipFile(io.BytesIO(payload)) as source:
        files = {name: source.read(name) for name in source.namelist()}
    metadata = "shuup-3.1.0.dist-info/METADATA"
    malformed = b"Requires-Dist: toml (<1pytz>=2015.4,>=0.10.0)"
    if files[metadata].count(malformed) != 1:
        raise ValueError("Unexpected Shuup dependency metadata. Review the source lock before building.")
    files[metadata] = files[metadata].replace(malformed, b"Requires-Dist: toml (<1,>=0.10.0)\nRequires-Dist: pytz (>=2015.4)")
    record_name = "shuup-3.1.0.dist-info/RECORD"
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, content in sorted(files.items()):
        if name == record_name:
            continue
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode("ascii")
        writer.writerow([name, "sha256=" + digest, len(content)])
    writer.writerow([record_name, "", ""])
    files[record_name] = record.getvalue().encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for name, content in files.items():
            target.writestr(name, content)
    return output.getvalue()


def main():
    """Download the locked distribution during image build and write a verified normalized wheel."""
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "config/source-lock.json").read_text())
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(lock["distribution_url"], timeout=120) as response:
        payload = response.read()
    normalized = normalize_wheel(payload, lock["sha256"])
    (destination / lock["distribution"]).write_bytes(normalized)
    print("Verified Shuup distribution; normalized dependency metadata and retained application assets.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        raise SystemExit("ERROR: Upstream package preparation failed: " + str(error))
