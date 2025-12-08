import json
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Any

from pprint import pprint

from config_reader import PowerBiTemplateConfig
from models_manager import ExpectedPbiReportInfo


LOGICAL_ID_NAMESPACE = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def create_model_and_report(template: PowerBiTemplateConfig, plans: List[ExpectedPbiReportInfo]) -> None:
    for plan in plans:
        _create_or_update_model(template, plan)
        _create_or_update_report(template, plan)


def _create_or_update_model(template: PowerBiTemplateConfig, plan: ExpectedPbiReportInfo) -> None:
    existing_logical_id = None

    if getattr(plan, "model_exist", False) and plan.model_platform.exists():
        old_platform = _load_json(plan.model_platform)
        existing_logical_id = old_platform.get("config", {}).get("logicalId")

    shutil.copytree(template.template_model, plan.expected_model_path, dirs_exist_ok=True)

    get_update_model_platform(plan, existing_logical_id)
    get_update_model_definition(template, plan)


def _create_or_update_report(template: PowerBiTemplateConfig, plan: ExpectedPbiReportInfo) -> None:

    existing_logical_id = None
    if plan.report_exist:
        old_platform = _load_json(plan.expected_report_platform)
        existing_logical_id = old_platform.get("config", {}).get("logicalId")

    shutil.copytree(template.template_report, plan.expected_report_path, dirs_exist_ok=True)
    get_update_report_platform(plan, existing_logical_id)

    if hasattr(plan, "expected_report_definition"):
        _update_report_definition(plan)
 

def _load_json(path: Path | str) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _generate_region_logical_id(plan: ExpectedPbiReportInfo, kind: str) -> str:
    name_for_id = f"{kind}:{plan.region_code}"
    return str(uuid.uuid5(LOGICAL_ID_NAMESPACE, name_for_id))


def get_update_model_platform(plan: ExpectedPbiReportInfo, existing_logical_id: str) -> None:
    platform = _load_json(plan.model_platform)
    platform["config"]["displayName"] = plan.report_name
    platform["metadata"]["displayName"] = plan.report_name
    if existing_logical_id:
        platform["config"]["logicalId"] = existing_logical_id
    else:
        platform["config"]["logicalId"] = _generate_region_logical_id(plan, kind="model")
    _save_json(plan.model_platform, platform)


def get_update_model_definition(template: PowerBiTemplateConfig, plan: ExpectedPbiReportInfo) -> None:
    with plan.model_definition.open("r", encoding="utf-8") as f:
        txt = f.read()
    txt = txt.replace(template.template_model_parameter, plan.region_code)
    with plan.model_definition.open("w", encoding="utf-8") as f:
        f.write(txt)


def get_update_report_platform(plan: ExpectedPbiReportInfo, existing_logical_id: str) ->None:
    platform = _load_json(plan.expected_report_platform)
    platform["config"]["displayName"] = plan.report_name
    platform["metadata"]["displayName"] = plan.report_name
    if existing_logical_id:
        platform["config"]["logicalId"] = existing_logical_id
    else:
        platform["config"]["logicalId"] = _generate_region_logical_id(plan, kind="report")
    _save_json(plan.expected_report_platform, platform)


def _update_report_definition(plan: ExpectedPbiReportInfo) -> None:
    path = Path(plan.expected_report_definition)
    definition = _load_json(path)
    definition["datasetReference"]["byPath"]["path"] = f"../{plan.expected_model_path}"
    _save_json(path, definition)