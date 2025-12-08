from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict, List, Callable, Mapping
from pprint import pprint


REGION_CONFIG_FILE = Path("config/regions")

BASE_PATH = Path(".")


@dataclass
class ExpectedPbiReportInfo:
    region_code: str
    report_name: str
    
    expected_model_path: Path
    expected_report_path: Path
    model_platform: Path
    model_definition: Path
    expected_report_platform: Path
    expected_report_definition: Path
    
    model_exist: bool
    report_exist: bool


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


def get_all_expected_pbi_attributes(region: str, config_path: Path = REGION_CONFIG_FILE, loader: Callable = load_data) -> Dict[str, str | Path]:
    data = loader(config_path)
    prefix = get_nested(data, "naming", "prefix", default="missing_attribute")
    return {
        "region_code": region,
        "report_name": prefix + region,
        "expected_model_path": Path(prefix + region + get_nested(data, "paths", "expected_model_path", default="missing_attribute")),
        "expected_report_path": Path(prefix + region + get_nested(data, "paths", "expected_report_path", default="missing_attribute")), 
        "model_platform": Path(prefix + region + get_nested(data, "paths", "model_platform", default="missing_attribute")),
        "model_definition": Path(prefix + region + get_nested(data, "paths", "model_definition", default="missing_attribute")),
        "expected_report_platform": Path(prefix + region + get_nested(data, "paths", "expected_report_platform", default="missing_attribute")),
        "expected_report_definition": Path(prefix + region + get_nested(data, "paths", "expected_report_definition", default="missing_attribute")),
    }


def if_model_exist(expected_model_path : Path) -> bool:
    return expected_model_path.exists()


def if_report_exist(expected_report_path : Path) -> bool:
    return expected_report_path.exists()


def get_expected_reports(region_config_path: Path | str = REGION_CONFIG_FILE) -> List[ExpectedPbiReportInfo]:
    result: List[ExpectedPbiReportInfo] = []
    regions_config_data = load_data(region_config_path)
    regions = regions_config_data.get("regions", [])
    for region in regions:
        all_expected_pbi_attributes  = get_all_expected_pbi_attributes(region)
        model_exist = if_model_exist(all_expected_pbi_attributes["expected_model_path"])
        report_exist = if_report_exist(all_expected_pbi_attributes["expected_report_path"]) 
        info = ExpectedPbiReportInfo(
            region_code = all_expected_pbi_attributes["region_code"],
            report_name = all_expected_pbi_attributes["report_name"],
            expected_model_path = all_expected_pbi_attributes["expected_model_path"],
            expected_report_path = all_expected_pbi_attributes["expected_report_path"],
            model_platform = all_expected_pbi_attributes["model_platform"],
            model_definition = all_expected_pbi_attributes["model_definition"],
            expected_report_platform = all_expected_pbi_attributes["expected_report_platform"],
            expected_report_definition = all_expected_pbi_attributes["expected_report_definition"],
            model_exist = model_exist,
            report_exist = report_exist,
        )
        result.append(info)
    return result


if __name__ == "__main__":
    regions = get_expected_reports()
    pprint(regions)
