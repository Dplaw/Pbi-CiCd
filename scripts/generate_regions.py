from pathlib import Path

from config_reader import get_template_info  
from models_manager import get_expected_reports
from report_creator import create_model_and_report


CONFIG_TEMPLATE = Path("config") / ("template_report_config")
CONFIG_REGIONS = Path("config") / ("regions")


def main():
    template = get_template_info(CONFIG_TEMPLATE)
    plans = get_expected_reports(CONFIG_REGIONS)
    create_model_and_report(template, plans)

if __name__ == "__main__":
    main()
