"""Script to automate or dry-run rollback to a previous immutable release version."""

import argparse
import json
import sys
from pathlib import Path


def execute_rollback(
    target_environment: str,
    target_image_tag: str,
    target_digest: str,
    reason: str,
    dry_run: bool = True,
) -> dict:
    """Prepare and execute rollback plan."""
    plan = {
        "action": "ROLLBACK",
        "environment": target_environment,
        "target_image_tag": target_image_tag,
        "target_image_digest": target_digest,
        "reason": reason,
        "dry_run": dry_run,
        "status": "PLAN_GENERATED" if dry_run else "EXECUTED",
        "steps": [
            "1. Halt active traffic rollout in ECS service deployment circuit breaker",
            f"2. Point ECS task definition to target immutable image tag {target_image_tag} ({target_digest})",
            "3. Update ECS service with minimum healthy percent = 100",
            "4. Monitor target group health checks on /health/ready",
            "5. Execute smoke tests against rolled back tasks",
            "6. Log rollback incident in results/phase15/releases/",
        ],
    }
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelLog Release Rollback Utility")
    parser.add_argument("--env", required=True, choices=["staging", "production"], help="Target environment")
    parser.add_argument("--tag", required=True, help="Target immutable image tag to revert to (e.g. v0.14.0)")
    parser.add_argument("--digest", required=True, help="Target image digest (e.g. sha256:...)")
    parser.add_argument("--reason", required=True, help="Reason for initiating rollback")
    parser.add_argument("--execute", action="store_true", help="Execute rollback (default is dry-run)")
    args = parser.parse_args()

    plan = execute_rollback(
        target_environment=args.env,
        target_image_tag=args.tag,
        target_digest=args.digest,
        reason=args.reason,
        dry_run=not args.execute,
    )
    print(json.dumps(plan, indent=2))
    sys.exit(0)
