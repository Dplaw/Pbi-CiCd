import json
from dataclasses import dataclass
import os 
from pathlib import Path
from typing import Any, List, Dict, Optional, Callable
import base64
import requests
from utils import die, load_json, save_json


AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
FABRIC_WORKSPACE_ID = os.environ.get("WORKSPACE_ID")

FABRIC_BASE_URL = "https://api.fabric.microsoft.com/v1"


@dataclass(frozen=True)
class Settings:
    tenant_id: str = AZURE_TENANT_ID
    client_id: str = AZURE_CLIENT_ID
    client_secret: str = AZURE_CLIENT_SECRET
    workspace_id: str = FABRIC_WORKSPACE_ID
    timeout_s: int = 60
    retry_count: int = 3
    retry_sleep_s: float = 2.0


def get_fabric_token(s: Settings) -> str: 
    token_url = f"https://login.microsoftonline.com/{s.tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": s.client_id,
        "client_secret": s.client_secret,
        "grant_type": "client_credentials",
        "scope": "https://api.fabric.microsoft.com/.default",
    }
    r = requests.post(token_url, data=data, timeout=s.timeout_s)
    if not r.ok:
        die(f"Token request failed: HTTP {r.status_code}-{r.text}")
    js = r.json()
    token = js.get("access_token")
    if not token:
        die(f"Token response missing access_token:{json.dumps(js)}")
    return token


def get_headers(token: str) -> dict:
    return {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
    } 


def get_workspace_items(s: Settings, token: str) -> List[Dict[str, Any]]:
    url = f"{FABRIC_BASE_URL}/workspaces/{s.workspace_id}/items"
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    data = r.json()
    return data.get("value", data)


def get_existing_items(token: str, display_name: str) -> Dict[str, Optional[str]]:
    items = get_workspace_items(Settings(), token)
    result: Dict[str, Optional[str]] = {
        "SemanticModel": None,
        "Report": None,
    }
    for item in items:
        if item.get("displayName") != display_name:
            continue

        item_type = item.get("type")
        if item_type in result:
            result[item_type] = item.get("id")
    return result


def _b64_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _iter_parts(root_dir: Path):

    for p in sorted(root_dir.rglob("*")):
        if p.is_dir():
            continue

        rel_path = p.relative_to(root_dir).as_posix()
        yield {
            "path": rel_path,
            "payload": _b64_file(p),
            "payloadType": "InlineBase64",
        }
 

def condition_dispatcher(workspace_id: str, semantic_model_id: str | None = None, report_id: str | None = None) -> Dict[tuple, str]: 
    return {
        ("model", "update"): f"{FABRIC_BASE_URL}/workspaces/{workspace_id}/semanticModels/{semantic_model_id}/updateDefinition",
        ("model", "create"): f"{FABRIC_BASE_URL}/workspaces/{workspace_id}/semanticModels",
        ("report", "update"): f"{FABRIC_BASE_URL}/workspaces/{workspace_id}/reports/{report_id}/updateDefinition",
        ("report", "create"): f"{FABRIC_BASE_URL}/workspaces/{workspace_id}/reports"
    }


def get_post_item(url: str, path: Path, headers: dict, display_name: str) -> int:
    parts = list(_iter_parts(path))
    definition = {"parts": parts}
    payload = {
        "displayName": display_name,
        "definition": definition,
        }
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    return r.status_code


def patch_definition_for_api(path: Path, semantic_model_id: str ) -> None:
    data = load_json(path)
    data["datasetReference"] = {
        "byConnection": {
            "connectionString": f"semanticmodelid={semantic_model_id}"
        }
    }
    save_json(path, data)


def get_deploy(plan, deployer: Callable = get_post_item, s: dataclass = Settings, headers: Callable = get_headers):
    token = get_fabric_token(s)
    for item in plan:
        id = get_existing_items(token, item.report_name)
        if id.get("SemanticModel"):
            url = f"{FABRIC_BASE_URL}/workspaces/{FABRIC_WORKSPACE_ID}/semanticModels/{id['SemanticModel']}/updateDefinition"
            deployer(url, item.expected_model_path, headers(token), item.report_name)
            print("Updated Semantic Model")
        else:
            url = f"{FABRIC_BASE_URL}/workspaces/{FABRIC_WORKSPACE_ID}/semanticModels"
            deployer(url, item.expected_model_path, headers(token), item.report_name)
            print("Created Semantic Model")
        if id.get("Report"):
            patch_definition_for_api(item.expected_report_definition, id["SemanticModel"])
            url = f"{FABRIC_BASE_URL}/workspaces/{FABRIC_WORKSPACE_ID}/reports/{id['Report']}/updateDefinition"
            deployer(url, item.expected_report_path, headers(token), item.report_name)
            print("Updated Report")
        else:
            patch_definition_for_api(item.expected_report_definition, id["SemanticModel"])
            url = f"{FABRIC_BASE_URL}/workspaces/{FABRIC_WORKSPACE_ID}/reports"
            deployer(url, item.expected_report_path, headers(token), item.report_name)
            print("Created Report")

