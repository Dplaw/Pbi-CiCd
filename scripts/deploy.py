import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils import die, load_json, save_json

FABRIC_BASE_URL = "https://api.fabric.microsoft.com/v1"


@dataclass(frozen=True)
class Settings:
    tenant_id: str
    client_id: str
    client_secret: str
    workspace_id: str
    timeout_s: int = 60
    deploy_timeout_s: int = 180
    op_timeout_s: int = 900
    op_default_sleep_s: int = 5
    retry_count: int = 3
    retry_backoff_s: float = 2.0

    @classmethod
    def from_env(cls) -> "Settings":
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")
        workspace_id = os.getenv("FABRIC_WORKSPACE_ID") or os.getenv("WORKSPACE_ID")

        required = {
            "AZURE_TENANT_ID": tenant_id,
            "AZURE_CLIENT_ID": client_id,
            "AZURE_CLIENT_SECRET": client_secret,
            "FABRIC_WORKSPACE_ID": workspace_id,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            die(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            workspace_id=workspace_id,
        )


def _make_session(s: Settings) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=s.retry_count,
        backoff_factor=s.retry_backoff_s,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_fabric_access_token(s: Settings, session: Optional[requests.Session] = None) -> str:
    sess = session or _make_session(s)
    token_url = f"https://login.microsoftonline.com/{s.tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": s.client_id,
        "client_secret": s.client_secret,
        "grant_type": "client_credentials",
        "scope": "https://api.fabric.microsoft.com/.default",
    }

    r = sess.post(token_url, data=data, timeout=s.timeout_s)
    if not r.ok:
        die(f"Failed to obtain access token. HTTP {r.status_code}\n\n{r.text}")

    js = r.json()
    token = js.get("access_token")
    if not token:
        die(f"Token response missing access_token: {json.dumps(js)}")
    return token


def headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get_sleep_from_retry_after(value: Optional[str], default_s: int) -> int:
    if not value:
        return default_s
    value = value.strip()
    if value.isdigit():
        return max(1, int(value))
    return default_s


def wait_for_operation(session: requests.Session, token: str, op_url: str, *, timeout_s: int, default_sleep_s: int,) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    hdrs = {"Authorization": f"Bearer {token}"}

    while True:
        if time.time() > deadline:
            raise RuntimeError(f"Operation did not finish within {timeout_s}s: {op_url}")

        r = session.get(op_url, headers=hdrs, timeout=60)
        r.raise_for_status()
        data = r.json()

        status = (data.get("status") or data.get("state") or "").lower()

        if status in ("succeeded", "success", "completed"):
            return data
        if status in ("failed", "cancelled", "canceled"):
            raise RuntimeError(f"Operation failed: {data}")

        sleep_s = _get_sleep_from_retry_after(r.headers.get("Retry-After"), default_sleep_s)
        time.sleep(sleep_s)


def wait_if_async(session: requests.Session, token: str, response: requests.Response, s: Settings) -> None:
    """
    Waits only when response indicates async operation via Location: .../v1/operations/<id>.
    """
    loc = response.headers.get("Location") or response.headers.get("location")
    if loc and "/operations/" in loc:
        wait_for_operation(
            session=session,
            token=token,
            op_url=loc,
            timeout_s=s.op_timeout_s,
            default_sleep_s=s.op_default_sleep_s,
        )


def _iter_parts(root_dir: Path) -> Iterable[Dict[str, Any]]:
    for p in sorted(root_dir.rglob("*")):
        if p.is_dir():
            continue
        rel_path = p.relative_to(root_dir).as_posix()
        yield {
            "path": rel_path,
            "payload": base64.b64encode(p.read_bytes()).decode("utf-8"),
            "payloadType": "InlineBase64",
        }


def _definition_payload(display_name: str, definition_dir: Path) -> Dict[str, Any]:
    return {"displayName": display_name, "definition": {"parts": list(_iter_parts(definition_dir))}}


def patch_definition_for_api(path: Path, semantic_model_id: str) -> None:
    data = load_json(path)
    data["datasetReference"] = {
        "byConnection": {"connectionString": f"semanticmodelid={semantic_model_id}"}
    }
    save_json(path, data)


def get_workspace_items(s: Settings, token: str, session: requests.Session) -> List[Dict[str, Any]]:
    url = f"{FABRIC_BASE_URL}/workspaces/{s.workspace_id}/items"
    r = session.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=s.timeout_s)
    r.raise_for_status()
    data = r.json()
    return data.get("value", data)


def get_existing_items(s: Settings, token: str, report_name: str, session: requests.Session) -> Dict[str, Optional[str]]:
    items = get_workspace_items(s, token, session=session)
    found: Dict[str, Optional[str]] = {"SemanticModel": None, "Report": None}

    for item in items:
        if item.get("displayName") != report_name:
            continue
        t = item.get("type")
        if t in found:
            found[t] = item.get("id")

    return found


def resolve_item_id(s: Settings, token: str, display_name: str, item_type: str, session: requests.Session, *, attempts: int = 20, sleep_s: float = 2.0,) -> Optional[str]:
    for _ in range(attempts):
        items = get_workspace_items(s, token, session=session)
        for item in items:
            if item.get("displayName") == display_name and item.get("type") == item_type:
                return item.get("id")
        time.sleep(sleep_s)
    return None


def _extract_id_from_response(r: requests.Response) -> Optional[str]:
    try:
        js = r.json()
    except Exception:
        js = None

    if isinstance(js, dict):
        for key in ("id", "itemId", "semanticModelId", "reportId"):
            val = js.get(key)
            if isinstance(val, str) and val:
                return val

    loc = r.headers.get("Location") or r.headers.get("location")
    if loc:
        parts = [p for p in loc.split("/") if p]
        if parts:
            candidate = parts[-1].split("?")[0]
            if candidate:
                return candidate

    return None


def deploy_definition(url: str, definition_path: Path, headers_dict: Dict[str, str], display_name: str, *, session: Optional[requests.Session] = None, timeout_s: int = 180,) -> requests.Response:
    sess = session or requests.Session()
    payload = _definition_payload(display_name, definition_path)
    return sess.post(url, headers=headers_dict, json=payload, timeout=timeout_s)


def get_deploy(plan, deployer: Callable = deploy_definition) -> None:
    s = Settings.from_env()
    session = _make_session(s)
    token = get_fabric_access_token(s, session=session)

    for item in plan:
        report_name = item.report_name

        existing = get_existing_items(s, token, report_name, session=session)
        existing_model_id = existing.get("SemanticModel")
        existing_report_id = existing.get("Report")

        # --- Semantic Model ---
        if existing_model_id:
            url = f"{FABRIC_BASE_URL}/workspaces/{s.workspace_id}/semanticModels/{existing_model_id}/updateDefinition"
            r = deployer(
                url, item.expected_model_path, headers(token), report_name,
                session=session, timeout_s=s.deploy_timeout_s
            )
            if not r.ok:
                die(f"Failed to update Semantic Model '{report_name}'. HTTP {r.status_code}\n\n{r.text}")

            wait_if_async(session, token, r, s)
            print("Updated Semantic Model")

            semantic_model_id = existing_model_id
        else:
            url = f"{FABRIC_BASE_URL}/workspaces/{s.workspace_id}/semanticModels"
            r = deployer(
                url, item.expected_model_path, headers(token), report_name,
                session=session, timeout_s=s.deploy_timeout_s
            )
            if not r.ok:
                die(f"Failed to create Semantic Model '{report_name}'. HTTP {r.status_code}\n\n{r.text}")

            wait_if_async(session, token, r, s)
            print("Created Semantic Model")

            semantic_model_id = (
                resolve_item_id(s, token, report_name, "SemanticModel", session=session, attempts=25, sleep_s=2.0)
                or _extract_id_from_response(r)
            )

        if not semantic_model_id:
            die(f"Could not resolve SemanticModel ID for '{report_name}' after deployment.")

        patch_definition_for_api(item.expected_report_definition, semantic_model_id)
        print(f"Binding report '{report_name}' to semantic model id: {semantic_model_id}")

        if existing_report_id:
            url = f"{FABRIC_BASE_URL}/workspaces/{s.workspace_id}/reports/{existing_report_id}/updateDefinition"
            r2 = deployer(
                url, item.expected_report_path, headers(token), report_name,
                session=session, timeout_s=s.deploy_timeout_s
            )
            if not r2.ok:
                die(
                    "Failed to update Report '{0}'. HTTP {1}\n\n"
                    "SemanticModelId used: {2}\n\nResponse:\n{3}".format(
                        report_name, r2.status_code, semantic_model_id, r2.text
                    )
                )

            wait_if_async(session, token, r2, s)  # <--- key addition
            print("Updated Report")
        else:
            url = f"{FABRIC_BASE_URL}/workspaces/{s.workspace_id}/reports"
            r2 = deployer(
                url, item.expected_report_path, headers(token), report_name,
                session=session, timeout_s=s.deploy_timeout_s
            )
            if not r2.ok:
                die(
                    "Failed to create Report '{0}'. HTTP {1}\n\n"
                    "SemanticModelId used: {2}\n\nResponse:\n{3}".format(
                        report_name, r2.status_code, semantic_model_id, r2.text
                    )
                )

            wait_if_async(session, token, r2, s)  # <--- key addition
            print("Created Report")


def deploy(plan, deployer: Callable = deploy_definition) -> None:
    return get_deploy(plan, deployer=deployer)
