import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from config_reader import PowerBiTemplateConfig
from models_manager import ExpectedPbiReportInfo
from utils import load_json, save_json, ensure_platform_structure


LOGICAL_ID_NAMESPACE = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def create_model_and_report(template: PowerBiTemplateConfig, plans: List[ExpectedPbiReportInfo]) -> None:
    for plan in plans:
        _create_or_update_model(template, plan)
        _create_or_update_report(template, plan)


def _create_or_update_model(template: PowerBiTemplateConfig, plan: ExpectedPbiReportInfo) -> None:

    existing_logical_id: Optional[str] = None

    if getattr(plan, "model_exist", False) and plan.model_platform.exists():
        old_platform = load_json(plan.model_platform)
        existing_logical_id = old_platform.get("config", {}).get("logicalId")


    shutil.copytree(template.template_model, plan.expected_model_path, dirs_exist_ok=True)

    get_update_model_platform(plan, existing_logical_id)
    get_update_model_definition(template, plan)


def _create_or_update_report(template: PowerBiTemplateConfig, plan: ExpectedPbiReportInfo) -> None:

    existing_logical_id: Optional[str] = None

    if getattr(plan, "report_exist", False) and plan.expected_report_platform.exists():
        old_platform = load_json(plan.expected_report_platform)
        existing_logical_id = old_platform.get("config", {}).get("logicalId")

    shutil.copytree(template.template_report, plan.expected_report_path, dirs_exist_ok=True)

    get_update_report_platform(plan, existing_logical_id)
    _update_report_definition(plan)


def _generate_region_logical_id(plan: ExpectedPbiReportInfo, kind: str) -> str:
    name_for_id = f"{kind}:{plan.region_code}"
    return str(uuid.uuid5(LOGICAL_ID_NAMESPACE, name_for_id))


def get_update_model_platform(plan: ExpectedPbiReportInfo, existing_logical_id: Optional[str]) -> None:
    platform = ensure_platform_structure(load_json(plan.model_platform))

    platform["config"]["displayName"] = plan.report_name
    platform["metadata"]["displayName"] = plan.report_name

    if existing_logical_id:
        platform["config"]["logicalId"] = existing_logical_id
    else:
        platform["config"]["logicalId"] = _generate_region_logical_id(plan, kind="model")

    save_json(plan.model_platform, platform)


def get_update_model_definition(template: PowerBiTemplateConfig, plan: ExpectedPbiReportInfo) -> None:
    with plan.model_definition.open("r", encoding="utf-8") as f:
        txt = f.read()

    txt = txt.replace(template.template_model_parameter, plan.region_code)

    with plan.model_definition.open("w", encoding="utf-8") as f:
        f.write(txt)


def get_update_report_platform(plan: ExpectedPbiReportInfo, existing_logical_id: Optional[str]) -> None:
    platform = ensure_platform_structure(load_json(plan.expected_report_platform))

    platform["config"]["displayName"] = plan.report_name
    platform["metadata"]["displayName"] = plan.report_name

    if existing_logical_id:
        platform["config"]["logicalId"] = existing_logical_id
    else:
        platform["config"]["logicalId"] = _generate_region_logical_id(plan, kind="report")

    save_json(plan.expected_report_platform, platform)


def _update_report_definition(plan: ExpectedPbiReportInfo) -> None:

    path = Path(plan.expected_report_definition)
    definition = load_json(path)

    model_folder_name = plan.expected_model_path.name
    relative_path = Path("..") / model_folder_name

    definition["datasetReference"]["byPath"]["path"] = relative_path.as_posix()

    save_json(path, definition)
