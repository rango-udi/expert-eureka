"""Record real customer screenshots and verify run-specific report attachments."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

RUN_ID = re.compile(r'[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}')
PNG_HEADER = b'\x89PNG\r\n\x1a\n'


class EvidenceRun:
    """Keep images outside Browser's automatically cleaned screenshot folder."""

    def __init__(self, app, model_sha256):
        """Create a distinct artifact run without changing literal test identities."""
        self.app = Path(app).resolve()
        self.run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid4().hex[:12]
        self.directory = self.app / 'reports/customer/evidence' / self.run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.manifest_path = self.directory / 'manifest.json'
        self.data = {'schema_version': 1, 'run_id': self.run_id, 'model_sha256': model_sha256,
                     'images': [], 'tests': {}, 'capture_errors': []}
        self.save()

    def save(self):
        """Publish each completed capture atomically, retaining partial failed runs."""
        pending = self.manifest_path.with_suffix('.tmp')
        pending.write_text(json.dumps(self.data, indent=2) + '\n', encoding='utf-8')
        pending.replace(self.manifest_path)

    def target(self, case_id, checkpoint):
        """Use stable business IDs and safe English labels in image filenames."""
        if not re.fullmatch(r'TC-[A-Z]{2}-[0-9]{3}', case_id) or not re.fullmatch(r'[a-z0-9-]+', checkpoint):
            raise ValueError('Use a business case ID and a simple English screenshot checkpoint.')
        folder = self.directory / 'screenshots'
        folder.mkdir(exist_ok=True)
        return folder / (case_id + '-' + checkpoint + '-' + str(len(self.data['images']) + 1).zfill(3) + '.png')

    def record(self, path, case_id, robot_id, checkpoint, role):
        """Record only an existing PNG produced inside this run's directory."""
        path = Path(path).resolve()
        if self.directory.resolve() not in path.parents or not path.is_file():
            raise ValueError('A screenshot must be an existing file in this evidence run.')
        payload = path.read_bytes()
        if not payload.startswith(PNG_HEADER):
            raise ValueError('The screenshot is not a PNG image.')
        self.data['images'].append({'case_id': case_id, 'robot_id': robot_id,
                                    'checkpoint': checkpoint, 'role': role,
                                    'path': path.relative_to(self.app).as_posix(),
                                    'sha256': hashlib.sha256(payload).hexdigest()})
        self.save()

    def capture_error(self, case_id, robot_id, checkpoint, error):
        """Record unavailable evidence without persisting raw page or credential text."""
        self.data['capture_errors'].append({'case_id': case_id, 'robot_id': robot_id,
                                            'checkpoint': checkpoint, 'error_type': type(error).__name__})
        self.save()

    def finish_test(self, robot_id, status):
        """Store execution state separately from the presence of a screenshot."""
        self.data['tests'][robot_id] = status
        self.save()


def verified_images(app, results, model_sha256):
    """Attach exact-case images only from the run identified by the selected XML."""
    app = Path(app).resolve()
    warnings = []
    metadata = (results or {}).get('evidence_run')
    if not metadata:
        return {}, ['The selected run contains no screenshot manifest metadata.'] if results else []
    if not isinstance(metadata, dict):
        return {}, ['The screenshot metadata is invalid.']
    run_id = metadata.get('run_id', '')
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        return {}, ['The screenshot run identifier is invalid.']
    expected = Path('reports/customer/evidence') / run_id / 'manifest.json'
    if metadata.get('manifest') != expected.as_posix():
        return {}, ['The screenshot manifest path does not match its run identifier.']
    path = app / expected
    if not path.is_file() or path.is_symlink() or app not in path.resolve().parents:
        return {}, ['The screenshot manifest is missing from the app folder.']
    try:
        manifest = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}, ['The screenshot manifest cannot be read.']
    if (manifest.get('schema_version') != 1 or manifest.get('run_id') != run_id or
            manifest.get('model_sha256') != metadata.get('model_sha256') or
            manifest.get('model_sha256') != model_sha256):
        return {}, ['Screenshot model/run metadata does not match the selected report and current model.']
    images = {}
    base = (app / 'reports/customer/evidence' / run_id / 'screenshots').resolve()
    if app not in base.parents:
        return {}, ['The screenshot directory resolves outside the app folder.']
    for row in manifest.get('images', []):
        case_id, robot_id = row.get('case_id', ''), row.get('robot_id', '')
        if not re.fullmatch(r'TC-[A-Z]{2}-[0-9]{3}', case_id) or robot_id not in results.get('tests', {}):
            warnings.append('Skipped an image with an unknown business or execution ID.')
            continue
        relative = Path(row.get('path', ''))
        target = app / relative
        if relative.is_absolute() or '..' in relative.parts or target.is_symlink() or base not in target.resolve().parents or not target.is_file():
            warnings.append('A screenshot is missing or outside the selected run: ' + case_id)
            continue
        payload = target.read_bytes()
        if not payload.startswith(PNG_HEADER) or hashlib.sha256(payload).hexdigest() != row.get('sha256'):
            warnings.append('A screenshot checksum or image type differs: ' + case_id)
            continue
        if manifest.get('tests', {}).get(robot_id) != results['tests'][robot_id].get('status'):
            warnings.append('Screenshot execution status differs from the selected XML: ' + case_id)
            continue
        images.setdefault(case_id, []).append(dict(row, path=relative.as_posix()))
    if manifest.get('capture_errors'):
        warnings.append('Some screenshot captures failed; inspect the evidence manifest.')
    return images, sorted(set(warnings))
