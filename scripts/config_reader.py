from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Callable, Mapping
from functools import lru_cache
import re
from pprint import pprint


CONFIG_FILE = Path("config/template_report_config")


@dataclass
class PowerBiTemplateConfig:
    # Paths
    base_path: Path
    template_model: Path
    template_report: Path
    model_platform: Path
    model_definition: Path
    report_platform: Path
    report_definition: Path

    # Model metadata
    template_model_metadata_type: str
    template_model_metadata_name: str
    template_model_config_id: str
    template_model_parameter: str

    # Report metadata
    template_report_metadata_type: str
    template_report_metadata_name: str
    template_report_metadata_model_reference: str


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


def get_all_pbi_attributes(config_path: Path = CONFIG_FILE, loader: Callable = load_data) -> Dict[str, str | Path]:
    data = loader(config_path)
    return {
        "base_path": Path(get_nested(data, "base_path", default="missing_attribute")),
        "template_model": Path(get_nested(data, "model_attributes", "template_model", default="missing_attribute")),
        "template_report": Path(get_nested(data, "report_attributes", "template_report", default="missing_attribute")), 
        "model_platform": Path(get_nested(data, "model_attributes", "model_platform", default="missing_attribute")),
        "model_definition": Path(get_nested(data, "model_attributes", "model_definition", default="missing_attribute")),
        "report_platform": Path(get_nested(data, "report_attributes", "report_platform", default="missing_attribute")),
        "report_definition": Path(get_nested(data, "report_attributes", "report_definition", default="missing_attribute")),
    }


def get_model_metadata(model_platform_path: Path, loader: Callable = load_data) -> Dict[str, str]:
    data = loader(model_platform_path)
    return {
        "type": get_nested(data, "metadata", "type", default=""),
        "name": get_nested(data, "metadata", "displayName", default=""),
        "config_id": get_nested(data, "config", "logicalId", default=""),
    }


def get_report_metadata(report_platform_path: Path, report_definition_path: Path, loader: Callable = load_data) -> Dict:
    platform_data = loader(report_platform_path)
    definition_data = loader(report_definition_path)
    return {
        "type": get_nested(platform_data, "metadata", "type", default=""),
        "name": get_nested(platform_data, "metadata", "displayName", default=""),
        "model_reference_path": get_nested(definition_data, "datasetReference", "byPath", "path", default=""),
    }


def get_template_model_parameter(model_definition_path: Path) -> str | None:
    text = model_definition_path
    pattern = r'Parameter1\s*=\s*"([^"]+)"'
    with open(model_definition_path, "r", encoding="utf-8") as f:
        text = f.read()
    match = re.search(pattern, text)
    return match.group(1)


def get_template_info() -> PowerBiTemplateConfig:
    all_pbi_attributes = get_all_pbi_attributes()
    model_metadata = get_model_metadata(all_pbi_attributes["model_platform"])
    report_metadata = get_report_metadata(all_pbi_attributes["report_platform"], all_pbi_attributes["report_definition"])
    model_parameter = get_template_model_parameter(all_pbi_attributes["model_definition"])
    return PowerBiTemplateConfig (
        # Paths
        base_path=all_pbi_attributes["base_path"],
        template_model=all_pbi_attributes["template_model"],
        template_report=all_pbi_attributes["template_report"],
        model_platform=all_pbi_attributes["model_platform"],
        model_definition=all_pbi_attributes["model_definition"],
        report_platform=all_pbi_attributes["report_platform"],
        report_definition=all_pbi_attributes["report_definition"],
        # Model metadata
        template_model_metadata_type=model_metadata["type"],
        template_model_metadata_name=model_metadata["name"],
        template_model_config_id=model_metadata["config_id"],
        template_model_parameter=model_parameter,
        # Report metadata
        template_report_metadata_type=report_metadata["type"],
        template_report_metadata_name=report_metadata["name"],
        template_report_metadata_model_reference=report_metadata["model_reference_path"],
    )

if __name__ == "__main__":
    template_info = get_template_info()
    pprint(template_info)
