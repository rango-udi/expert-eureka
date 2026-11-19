"""Publish complete workbooks atomically, retaining an alternative when Excel locks one."""
from datetime import datetime, timezone
import errno
import os
from pathlib import Path
import tempfile
from uuid import uuid4


class ReportOutputError(OSError):
    """Describe a report save failure without hiding a completed recovery file."""


def publish_workbook(target, render):
    """Render in the destination folder and replace only after a complete save.

    A host Excel lock can surface as EACCES, EBUSY or ETXTBSY through a Docker
    bind mount. A distinct output preserves both the open workbook and the new
    report. Other errors, including a full disk, must remain failures.
    """
    target = Path(target)
    warnings = []
    if (target.parent / ('~$' + target.name)).exists():
        warnings.append('An Excel owner file exists. Export will continue; a locked workbook will be saved under a new name.')
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix='.' + target.stem + '-', suffix='.xlsx',
                                         dir=target.parent, delete=False) as stream:
            pending = Path(stream.name)
    except OSError as error:
        raise ReportOutputError('Cannot create the customer workbook. Check report-folder write access and free disk space; existing workbooks were preserved.') from error
    try:
        render(pending)
    except Exception as error:
        pending.unlink(missing_ok=True)
        if isinstance(error, OSError):
            raise ReportOutputError('Cannot finish the customer workbook. Check write access and free disk space; the previous workbook was preserved.') from error
        raise
    try:
        os.replace(pending, target)
        return target, warnings
    except OSError as error:
        locked = error.errno in (errno.EACCES, errno.EPERM, errno.EBUSY, errno.ETXTBSY) or getattr(error, 'winerror', None) in (32, 33)
        if not locked:
            raise ReportOutputError('Cannot publish the customer workbook. Check write access and free disk space. Completed workbook retained at: ' + str(pending)) from error
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8]
    alternate = target.with_name(target.stem + '-' + stamp + target.suffix)
    try:
        os.replace(pending, alternate)
    except OSError as error:
        raise ReportOutputError('The target workbook is locked or inaccessible and an alternative could not be published. Close Excel or check folder permissions/disk space, then rerun report. Completed workbook retained at: ' + str(pending)) from error
    warnings.append('The default workbook is locked or inaccessible, possibly open in Excel. It was preserved. New report saved as: ' + str(alternate) + '. Close the default workbook and rerun report to refresh its usual filename.')
    return alternate, warnings
