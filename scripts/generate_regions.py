from pathlib import Path

from config_reader import get_template_info  
from models_manager import get_expected_reports
from report_creator import create_model_and_report


def main():
    template = get_template_info()
    plans = get_expected_reports()
    create_model_and_report(template, plans)

if __name__ == "__main__":
    main()
