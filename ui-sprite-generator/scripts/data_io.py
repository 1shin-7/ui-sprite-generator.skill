"""Small JSON/YAML loader used by ui-sprite-generator helper scripts."""

import json
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by environment-dependent tests
    yaml = None


class DataIOError(Exception):
    pass


YAML_EXTENSIONS = {".yaml", ".yml"}
JSON_EXTENSIONS = {".json"}


def load_data(path):
    data_path = Path(path)
    suffix = data_path.suffix.lower()
    try:
        text = data_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DataIOError(f"data file not found: {data_path}") from exc

    if suffix in JSON_EXTENSIONS:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise DataIOError(f"invalid JSON in {data_path}: {exc}") from exc
    if suffix in YAML_EXTENSIONS:
        if yaml is None:
            raise DataIOError(f"PyYAML is required to read YAML files: {data_path}")
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise DataIOError(f"invalid YAML in {data_path}: {exc}") from exc

    raise DataIOError(f"unsupported data file extension: {data_path.suffix}")


def dump_data(data, path):
    data_path = Path(path)
    suffix = data_path.suffix.lower()
    data_path.parent.mkdir(parents=True, exist_ok=True)
    if suffix in JSON_EXTENSIONS:
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    if suffix in YAML_EXTENSIONS:
        if yaml is None:
            raise DataIOError(f"PyYAML is required to write YAML files: {data_path}")
        data_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return
    raise DataIOError(f"unsupported data file extension: {data_path.suffix}")
