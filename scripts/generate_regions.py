import os 
import shutil
from json import loads
from uuid import uuid4
from pprint import pprint


def get_config(region_path):
    with open(region_path, 'r') as f:
        config = f.read()
    return loads(config)


def get_path(regions):
    folders = os.listdir(os.getcwd())
    return {os.path.join(folder.replace('Sales Reports', f'Sales Reports_{region}')) : region
            for folder in folders 
            for region in regions['regions']
            if folder in ['Sales Reports.SemanticModel']}


def create_directory(report_paths): 
    for new_path in report_paths.keys():
        if os.path.exists(new_path):
            shutil.rmtree(new_path)  
        os.makedirs(new_path)


def get_copy_dependencies(report_paths, semantimodel_path, report_path):
    for path in report_paths.keys():
        if 'SemanticModel' in path:
            shutil.copytree(semantimodel_path, path, dirs_exist_ok=True)
        elif 'Report' in path:
            shutil.copytree(report_path, path, dirs_exist_ok=True)


def dispatch_dict(condition, region ):
    return {
        'Sales Reports': lambda: {'Sales Reports': 'Sales Reports_' + f'{region}'},
        '1aa71ee4-8fcb-4383-b39b-b24bb2b286c5': lambda: {'1aa71ee4-8fcb-4383-b39b-b24bb2b286c5': str(uuid4())},
        'C&EE': lambda: {'C&EE': f'{region}'},
        '51349b6c-9f00-4c57-b18d-b365ea909872': lambda: {'51349b6c-9f00-4c57-b18d-b365ea909872': f'{region}'},
    }.get(condition, lambda: None)()


def get_all_attributes(regions, attributes, func):
    results = {}
    for attr_key, attr_value in attributes.items():
        for region in regions['regions']:
            idx = attr_key.find("/")
            path = os.path.join(attr_key[:idx].replace('Sales Reports', f'Sales Reports_{region}'), attr_key[idx+1:])
            new_value = [func(i, region) for i in attr_value]
            results.update({path: new_value})
    return results


def replacer(dict_obj):
    for path, values in dict_obj.items():
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        for value in values:
            for old, new in value.items():
                content = content.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def main(region_path: str, attributes: str, src_report: str, src_semantic_model: str) -> None:
    regions = get_config(region_path)
    paths = get_path(regions)
    attributes = get_config(attributes)
    dirs = create_directory(paths)
    copy = get_copy_dependencies(paths, src_semantic_model, src_report)
    dispatch = dispatch_dict
    all_attributes = get_all_attributes(regions, attributes, dispatch)
    replace = replacer(all_attributes)


if __name__ == "__main__":
    region_path = 'config/region'
    report_attributes = 'config/report_attributes'
    semantic_model = 'Sales Reports.SemanticModel'
    report = 'Sales Reports.Report'
    main(region_path, report_attributes, report, semantic_model)