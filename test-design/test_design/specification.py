"""Read reviewed YAML/JSON specifications without implicit YAML type coercion."""
import hashlib
import json
from pathlib import Path
import yaml


class SpecificationLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently replacing reviewed data."""


def _mapping(loader, node, deep=False):
    """Read a YAML mapping while retaining key uniqueness."""
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError('Specification keys must be strings.')
        if key in result:
            raise ValueError('Duplicate specification key: ' + key)
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


SpecificationLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _json_mapping(pairs):
    """Apply the same duplicate-key policy to JSON input."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate specification key: ' + key)
        result[key] = value
    return result


def load_specification(path):
    """Load one mapping. Numeric UI values still require quotes and domain validation."""
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Test specifications must be no larger than 1 MiB.')
    text = path.read_text(encoding='utf-8')
    try:
        if path.suffix.lower() in ('.yaml', '.yml'):
            value = yaml.load(text, Loader=SpecificationLoader)
        elif path.suffix.lower() == '.json':
            value = json.loads(text, object_pairs_hook=_json_mapping)
        else:
            raise ValueError('Use a .yaml, .yml or .json specification.')
        if not isinstance(value, dict):
            raise ValueError('A test specification must be a mapping.')
        # Also rejects YAML timestamps, sets, recursive aliases and nonfinite numbers.
        json.dumps(value, allow_nan=False)
    except (yaml.YAMLError, TypeError, RecursionError, OverflowError) as error:
        raise ValueError('Invalid test specification: ' + str(error)) from error
    return value


def semantic_hash(model):
    """Ignore formatting and comments when identifying a reviewed model snapshot."""
    return hashlib.sha256(json.dumps(model, sort_keys=True, ensure_ascii=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()
