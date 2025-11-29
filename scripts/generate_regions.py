from json import loads


def get_params(path: str) -> list[str]:
    with open(path, 'r') as f:
        config = f.read()
    return loads(config)

def create_directory(path: str) -> None: 
    ...

def main(region_path) -> None:
    regions = get_params(region_path)['regions']
    print(regions)

region_path = 'config/region'
main(region_path)