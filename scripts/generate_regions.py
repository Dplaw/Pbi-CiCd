import os 
import shutil
from json import loads


def get_params(region_path: str) -> list[str]:
    with open(region_path, 'r') as f:
        config = f.read()
    return loads(config)['regions']


def get_path(regions: list[str]) -> list[str]:
    folders = os.listdir(os.getcwd())
    return [os.path.join(f'{folder}_{region}')
            for region in regions
            for folder in folders 
            if 'Sales Reports' in folder]


def create_directory(report_paths: list[str]) -> None: 
    for new_path in report_paths:
        if os.path.exists(new_path):
            shutil.rmtree(new_path)  
        os.makedirs(new_path) 


def get_copy_report(src: str, dests: list[str]) -> None:
    for dir in dests:
        shutil.copytree(src, dir, dirs_exist_ok=True)


def get_copy_semantic_model(src: str, dests: list[str]) -> None:
    for dir in dests:
        shutil.copytree(src, dir, dirs_exist_ok=True)


def get_expressions_path(paths: list[str], regions: list[str] ) -> list[str]:
    return [os.path.join(path, "definition", "expressions.tmdl") for path in paths if 'SemanticModel' in path]


def get_path_region_dict(expressions_path: list[str], regions: list[str]) -> dict[str, str]:
    return {path: region for region, path in zip(regions, expressions_path)}


def get_replace_region(path_region) -> None:
    for path, region in path_region.items():
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        content = content.replace("C&EE", region)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

def main(region_path: str, src_report: str, src_semantic_model: str) -> None:
    regions = get_params(region_path)
    paths = get_path(regions)
    directory = create_directory(paths)
    copy_report = get_copy_report(src_report, paths)
    copy_semantic_model = get_copy_semantic_model(src_semantic_model, paths)
    expressions_path = get_expressions_path(paths, regions)
    path_region_dict = get_path_region_dict(expressions_path, regions)
    get_replace_region(path_region_dict)


if __name__ == "__main__":
    region_path = 'config/region'
    semantic_model = 'Sales Reports.SemanticModel'
    report = 'Sales Reports.Report'
    main(region_path, report, semantic_model)
