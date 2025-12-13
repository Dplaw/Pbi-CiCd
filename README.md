Power BI Regional Report Generator (PBIP + Python + GitHub Actions)

This project provides an automated way to generate region-specific Power BI reports (PBIP format) from a single reusable template.
It solves the challenge of working with a very large data model (hundreds of millions of rows) by producing separate models for each region, filtered via Power Query parameters.

The system uses:
Python scripts to copy, modify, and configure PBIP artifacts (model + report)
GitHub Actions to automate deployment and report generation
A single template PBIP project as the source of truth
A configuration file describing all regions to be generated


Key Features
Generate multiple regional PBIP reports from a single template
Each region receives:
A Semantic Model (PBIP folder)
A Report (PBIP folder)
Region-specific parameter substitution in the model definition
Correct internal linking between report ↔ model

Stable logicalId handling
PBIP uses logicalId to uniquely identify artifacts inside Fabric / Power BI service.
The project ensures stability:
If a report/model already exists → its logicalId is preserved
If it is created for the first time → a deterministic uuid5 is generated using: <kind>:<region_code>
This prevents synchronization errors in Fabric when PBIP folders are updated.

Clean structure and fully deterministic output
Regenerating for the same region always produces the same folder names, logicalIds, and parameter values.

Configurable regions
All regions are defined in: config/regions


Each entry defines:
region_code (e.g., "C&EE", "Nordics")
prefix for folder naming
target names for the model and report
<pre>
.
├── config/
│   ├── regions                     # List of all regions to generate
│   ├── template_report_config      # Configuration for the PBIP template
│
├── pbip_template/
│   ├── SemanticModel/              # Template semantic model
│   └── Report/                     # Template report
│
├── scripts/
│   ├── config_reader.py            # Loads configs and discovers template parameters
│   ├── models_manager.py           # Resolves paths and builds generation plan
│   ├── report_creator.py           # Copies PBIP folders and applies modifications
│   ├── utils.py                    # Shared helpers (JSON, path tools, nested reading)
│   └── generate_regions.py         # Main entry point
│
└── .github/workflows/
    └── generate_regions.yml        # CI/CD automation

</pre>
How the Generation Process Works
Below is the full workflow executed by generate_regions.py.


Load template configuration
config_reader.py extracts:
Template model folder
Template report folder
The Power Query parameter to replace (configured in template_report_config)
The default parameter value found inside the template model definition

Load region definitions
models_manager.get_expected_reports():
Reads all regions from config/regions
Constructs expected paths:
prefix_region/SemanticModel
prefix_region/Report
Checks whether these folders already exist
Builds a list of ExpectedPbiReportInfo objects

For each region: generate model and report
report_creator.py performs:
Model generation:
Copy template model folder into region-specific folder
Preserve existing logicalId or generate a deterministic uuid5
Replace template parameter with the region code
Report generation:
Copy template report folder
Preserve/generate logicalId
Update datasetReference.byPath.path to correctly point to the model


Logical ID Strategy (Important!)
Power BI PBIP uses logicalId to map local files to artifacts in Fabric workspaces.
If a logicalId changes unexpectedly, Fabric treats the artifact as a different resource, which results in errors during synchronization.

To avoid this:
Scenario	What the system does
Region already exists	Reads its current logicalId and preserves it
Region is new	Generates deterministic uuid5 based on region and kind (model / report)

This guarantees:
No accidental re-creation of artifacts
No "artifact ID mismatch" errors
Predictable reproducibility across machines and workflows
