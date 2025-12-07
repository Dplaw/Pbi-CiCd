from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path
import json
from typing import List, Dict, Any
from pprint import pprint


REGION_CONFIG_FILE = Path("config/regions")

BASE_PATH = Path(".")


@dataclass
class ExpectedPbiReportInfo:
    region_code: str
    expected_model_path: Path
    expected_report_path: Path
    model_platform: Path
    expected_report_platform: Path
    expected_report_definition: Path

    report_name: str

    model_exist: bool
    report_exist: bool

def _load_json(path: Path | str) -> Dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def load_data(path: Path | str) -> Dict[str, Any]:
    return _load_json(path)


def get_expected_model_path(region_data: Dict[str, Any], region: str, base_path: Path = BASE_PATH) -> Path:
    model_prefix = region_data["naming"]["prefix"]
    return Path(base_path, f"{model_prefix}{region}.SemanticModel")


def get_expected_report_path(region_data: Dict[str, Any], region: str, base_path: Path = BASE_PATH) -> Path:
    report_prefix = region_data["naming"]["prefix"]
    return Path(base_path, f"{report_prefix}{region}.Report")


def get_model_platform(model_path: Path) -> Path:
    return Path(model_path, ".platform")


def get_expected_report_platform(report_path: Path) -> Path:
    return Path(report_path, ".platform")


def get_expected_report_definition(report_path: Path) -> Path:
    return Path(report_path, "definition.pbir")


def get_report_name(region_data: Dict[str, Any], region: str, base_path: Path = BASE_PATH):
    report_prefix = region_data["naming"]["prefix"]
    return report_prefix + region


def if_model_exist(expected_model_path : Path) -> bool:
    return expected_model_path.exists()


def if_report_exist(expected_report_path : Path) -> bool:
    return expected_report_path.exists()

    
def get_expected_reports(region_config_path: Path | str = REGION_CONFIG_FILE) -> List[ExpectedPbiReportInfo]:
    result: List[ExpectedPbiReportInfo] = []
    regions_config_data = load_data(region_config_path)

    regions = regions_config_data.get("regions", [])
    for region in regions:
        expected_model_path = get_expected_model_path(regions_config_data, region)
        expected_report_path = get_expected_report_path(regions_config_data, region)

        model_platform = get_model_platform(expected_model_path)
        expected_report_platform = get_expected_report_platform(expected_report_path)
        expected_report_definition = get_expected_report_definition(expected_report_path)
        report_name = get_report_name(regions_config_data, region)
        model_exist = if_model_exist(expected_model_path)
        report_exist = if_report_exist(expected_report_path)
        info = ExpectedPbiReportInfo(
            region_code=region,
            expected_model_path=expected_model_path,
            expected_report_path=expected_report_path,
            model_platform=model_platform,
            expected_report_platform=expected_report_platform,
            expected_report_definition=expected_report_definition,
            report_name=report_name,
            model_exist=model_exist,
            report_exist=report_exist
        )
        result.append(info)
    return result


if __name__ == "__main__":
    regions = get_expected_reports()
    pprint(regions)
