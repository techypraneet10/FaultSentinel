"""CLI script to validate deployment configurations prior to deployment."""

import argparse
import json
import sys
from sentinellog.deployment.config_validator import load_env_config, validate_deployment_config


def main():
    parser = argparse.ArgumentParser(description="SentinelLog Deployment Configuration Validator")
    parser.add_argument("--env", required=True, choices=["development", "staging", "production"], help="Target environment")
    parser.add_argument("--configs-dir", default="configs", help="Directory containing environment configs")
    parser.add_argument("--check-env-vars", action="store_true", help="Assert referenced environment variables are set")
    args = parser.parse_args()

    try:
        cfg = load_env_config(args.env, configs_root=args.configs_dir)
        report = validate_deployment_config(cfg, check_env_vars=args.check_env_vars)
        print(json.dumps(report.to_dict(), indent=2))
        sys.exit(0 if report.valid else 1)
    except Exception as e:
        print(f"Error during configuration validation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
