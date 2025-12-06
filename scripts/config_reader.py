from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Callable, Mapping
from functools import lru_cache
from pprint import pprint


CONFIG_FILE = Path("config/template_report_config")


@dataclass
class PowerBiTemplateConfig:
    # Paths
    base_path: Path
    template_model: Path
    template_report: Path
    model_platform: Path
    report_platform: Path
    report_definition: Path

    # Model metadata
    template_model_metadata_type: str
    template_model_metadata_name: str
    template_model_config_id: str

    # Report metadata
    template_report_metadata_type: str
    template_report_metadata_name: str
    template_report_metadata_model_reference_path: str


def _load_json(path: Path | str) -> Dict:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def load_data(path: Path | str) -> Dict:
    return _load_json(path)


def get_nested(mapping: Mapping, *keys, default=None):
    current = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


def get_base_path(config_data: Dict) -> Path:
    return Path(config_data["base_path"])


def get_template_report(base: Path, config_data: Dict) -> Path:
    return base / config_data["template_report"]


def get_template_model(base: Path, config_data: Dict) -> Path:
    return base / config_data["template_model"]


def get_model_platform(template_model: Path, config_data: Dict) -> Path:
    return template_model / config_data["model_attributes"]["model_platform"]


def get_report_platform(template_report: Path, config_data: Dict) -> Path:
    return template_report / config_data["report_attributes"]["report_platform"]


def get_report_definition(template_report: Path, config_data: Dict) -> Path:
    return template_report / config_data["report_attributes"]["report_definition"]


def get_model_metadata(model_platform_path: Path, loader: Callable = load_data) -> Dict:
    data = loader(model_platform_path)
    return {
        "type": get_nested(data, "metadata", "type", default=""),
        "name": get_nested(data, "metadata", "displayName", default=""),
        "config_id": get_nested(data, "config", "logicalId", default=""),
    }


def get_report_metadata(report_platform_path: Path,
                        report_definition_path: Path,
                        loader: Callable = load_data) -> Dict:
    platform_data = loader(report_platform_path)
    definition_data = loader(report_definition_path)

    return {
        "type": get_nested(platform_data, "metadata", "type", default=""),
        "name": get_nested(platform_data, "metadata", "displayName", default=""),
        "model_reference_path": get_nested(
            definition_data, "datasetReference", "byPath", "path", default=""
        ),
    }


def get_template_info(config_path: Path | str = CONFIG_FILE) -> PowerBiTemplateConfig:
    config_data = load_data(config_path)

    base_path = get_base_path(config_data)
    template_model = get_template_model(base_path, config_data)
    template_report = get_template_report(base_path, config_data)
    model_platform = get_model_platform(template_model, config_data)
    report_platform = get_report_platform(template_report, config_data)
    report_definition = get_report_definition(template_report, config_data)

    model_meta = get_model_metadata(model_platform)
    report_meta = get_report_metadata(report_platform, report_definition)

    return PowerBiTemplateConfig(
        base_path=base_path,
        template_report=template_report,
        template_model=template_model,
        model_platform=model_platform,
        report_platform=report_platform,
        report_definition=report_definition,
        template_model_metadata_type=model_meta["type"],
        template_model_metadata_name=model_meta["name"],
        template_model_config_id=model_meta["config_id"],
        template_report_metadata_type=report_meta["type"],
        template_report_metadata_name=report_meta["name"],
        template_report_metadata_model_reference_path=report_meta["model_reference_path"],
    )


if __name__ == "__main__":
    template_info = get_template_info()
    pprint(template_info)
