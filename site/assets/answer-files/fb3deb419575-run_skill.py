#!/usr/bin/env python3
"""
Runner for aws-solution-architect skill scripts.

The skill's SKILL.md documents CLI invocations like:
    python scripts/architecture_designer.py --input requirements.json
but the actual script files only define classes (no __main__/argparse),
so those commands silently exit with no output.

This runner imports the existing classes as-is (no modification to the
skill files, no new dependencies) and exercises their public methods,
using assets/sample_input.json as the requirements source.
"""
import json
import sys
import os

SKILL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "aws-solution-architect-skill", "aws-solution-architect",
)
sys.path.insert(0, SKILL_DIR)

from scripts.architecture_designer import ArchitectureDesigner  # noqa: E402
from scripts.serverless_stack import ServerlessStackGenerator  # noqa: E402
from scripts.cost_optimizer import CostOptimizer  # noqa: E402


def main():
    # --- Step 1 & 2: requirements + architecture design ---
    with open(os.path.join(SKILL_DIR, "assets", "sample_input.json")) as f:
        requirements = json.load(f)

    designer = ArchitectureDesigner(requirements)
    design = designer.recommend_architecture_pattern()
    checklist = designer.generate_service_checklist()

    design_out = {
        "input_requirements": requirements,
        "recommended_pattern": design["pattern_name"],
        "description": design["description"],
        "use_case": design["use_case"],
        "services": {k: v["service"] for k, v in design["services"].items()},
        "estimated_monthly_cost_usd": design["estimated_cost"]["monthly_usd"],
        "cost_breakdown": design["estimated_cost"]["breakdown"],
        "pros": design["pros"],
        "cons": design["cons"],
        "scaling_characteristics": design["scaling_characteristics"],
    }
    with open("output_design.json", "w") as f:
        json.dump(design_out, f, indent=2, ensure_ascii=False)
    with open("output_checklist.json", "w") as f:
        json.dump(checklist, f, indent=2, ensure_ascii=False)

    # --- Step 3: IaC templates ---
    # sample input targets three-tier (50k users), but serverless_stack.py
    # only generates the serverless stack. Run it for a small MVP app name
    # to demonstrate its real output (the script's actual capability).
    gen = ServerlessStackGenerator(
        app_name="mvp-app",
        requirements={"region": requirements.get("region", "us-east-1")},
    )
    with open("output_template.yaml", "w") as f:
        f.write(gen.generate_cloudformation_template())
    with open("output_cdk_stack.ts", "w") as f:
        f.write(gen.generate_cdk_stack())
    with open("output_terraform.tf", "w") as f:
        f.write(gen.generate_terraform_configuration())

    # --- Step 4: cost optimization ---
    # No real AWS resource inventory is available (no AWS account/credentials
    # in this environment). Use a clearly-labeled illustrative inventory so
    # the CostOptimizer logic can be exercised; this is NOT real account data.
    illustrative_inventory = {
        "ec2_instances": [
            {"id": "i-example1", "cpu_utilization": 5, "pricing": "on-demand"},
            {"id": "i-example2", "cpu_utilization": 60, "pricing": "on-demand"},
        ],
        "s3_buckets": [
            {"name": "example-logs", "size_gb": 600,
             "storage_class": "STANDARD", "has_lifecycle_policy": False},
        ],
        "rds_instances": [
            {"name": "example-aurora", "engine": "aurora-postgresql",
             "utilization": 20, "monthly_cost": 300, "connections_per_day": 500},
        ],
        "dynamodb_tables": [
            {"name": "example-table", "billing_mode": "PROVISIONED",
             "read_capacity_units": 100, "write_capacity_units": 100,
             "utilization_percentage": 10},
        ],
        "nat_gateways": [{"id": "nat-a"}, {"id": "nat-b"}],
        "multi_az_required": False,
        "vpc_endpoints": [],
        "s3_data_transfer_gb": 200,
        "cloudwatch_log_groups": [
            {"name": "/aws/lambda/example", "retention_days": -1, "size_gb": 20},
        ],
        "elastic_ips": [{"id": "eip1", "attached": False}],
        "has_budget_alerts": False,
        "has_cost_explorer": False,
    }
    optimizer = CostOptimizer(illustrative_inventory, monthly_spend=2000)
    cost_result = optimizer.analyze_and_optimize()
    cost_checklist = optimizer.generate_optimization_checklist()
    with open("output_cost.json", "w") as f:
        json.dump(
            {"illustrative_inventory": illustrative_inventory,
             "analysis": cost_result,
             "optimization_checklist": cost_checklist},
            f, indent=2, ensure_ascii=False,
        )

    print("=== 架构推荐 ===")
    print(json.dumps(design_out, indent=2, ensure_ascii=False))
    print("\n=== 成本优化（基于示意清单，非真实账户数据）===")
    print(json.dumps(cost_result, indent=2, ensure_ascii=False))
    print("\n生成文件: output_design.json, output_checklist.json, "
          "output_template.yaml, output_cdk_stack.ts, output_terraform.tf, "
          "output_cost.json")


if __name__ == "__main__":
    main()
