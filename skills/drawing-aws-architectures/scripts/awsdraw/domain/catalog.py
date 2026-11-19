"""AWS service catalog: friendly key -> verified draw.io AWS4 shape.

`shape` values come from draw.io's own Sidebar-AWS4.js. tests/fixtures/aws4-icons.txt
holds the verified resourceIcon names and a test checks every entry here against it.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

COMPUTE, STORAGE, DATABASE, NETWORK, INTEG, SECURITY, AI = (
    "#ED7100", "#7AA116", "#C925D1", "#8C4FFF", "#E7157B", "#DD344C", "#01A88D",
)
DARK = "#232F3D"


@dataclass(frozen=True)
class Service:
    key: str
    label: str
    kind: str  # "resource" (resourceIcon) | "stencil" (own shape) | "general" (actors)
    shape: str
    color: str
    tier: str
    scope: str = "regional"  # "global" services sit outside the Region box


def _s(key, label, shape, color, tier, scope="regional", kind="resource"):
    return Service(key, label, kind, shape, color, tier, scope)


_SERVICES = (
    # actors
    _s("users", "Users", "users", DARK, "actors", "external", "general"),
    _s("user", "User", "user", DARK, "actors", "external", "general"),
    _s("client", "Client", "client", DARK, "actors", "external", "general"),
    _s("mobile", "Mobile app", "mobile_client", DARK, "actors", "external", "general"),
    # edge
    _s("cloudfront", "CloudFront", "cloudfront", NETWORK, "edge", "global"),
    _s("route53", "Route 53", "route_53", NETWORK, "edge", "global"),
    _s("waf", "AWS WAF", "waf", SECURITY, "edge", "global"),
    _s("shield", "Shield", "shield", SECURITY, "edge", "global"),
    _s("cognito", "Cognito", "cognito", SECURITY, "edge"),
    _s("api_gateway", "API Gateway", "api_gateway", INTEG, "edge"),
    _s("appsync", "AppSync", "appsync", INTEG, "edge"),
    _s("alb", "Application Load Balancer", "application_load_balancer", NETWORK, "edge", kind="stencil"),
    _s("amplify", "Amplify", "amplify", COMPUTE, "edge"),
    # app
    _s("lambda", "Lambda", "lambda", COMPUTE, "app"),
    _s("ec2", "EC2", "ec2", COMPUTE, "app"),
    _s("fargate", "Fargate", "fargate", COMPUTE, "app"),
    _s("ecs", "ECS", "ecs", COMPUTE, "app"),
    _s("eks", "EKS", "eks", COMPUTE, "app"),
    _s("ecr", "ECR", "ecr", COMPUTE, "app"),
    _s("app_runner", "App Runner", "app_runner", COMPUTE, "app"),
    _s("batch", "Batch", "batch", COMPUTE, "app"),
    _s("step_functions", "Step Functions", "step_functions", INTEG, "app"),
    _s("sqs", "SQS", "sqs", INTEG, "app"),
    _s("sns", "SNS", "sns", INTEG, "app"),
    _s("eventbridge", "EventBridge", "eventbridge", INTEG, "app"),
    _s("appflow", "AppFlow", "appflow", INTEG, "app"),
    _s("kinesis", "Kinesis", "kinesis", NETWORK, "app"),
    _s("firehose", "Kinesis Firehose", "kinesis_data_firehose", NETWORK, "app"),
    _s("msk", "MSK (Kafka)", "managed_streaming_for_kafka", NETWORK, "app"),
    _s("glue", "Glue", "glue", NETWORK, "app"),
    _s("emr", "EMR", "emr", NETWORK, "app"),
    _s("sagemaker", "SageMaker", "sagemaker", AI, "app"),
    _s("bedrock", "Bedrock", "bedrock", AI, "app"),
    _s("agentcore", "Bedrock AgentCore", "bedrock_agentcore", AI, "app"),
    # data
    _s("s3", "S3", "s3", STORAGE, "data"),
    _s("efs", "EFS", "elastic_file_system", STORAGE, "data"),
    _s("ebs", "EBS", "elastic_block_store", STORAGE, "data"),
    _s("aurora", "Aurora", "aurora", DATABASE, "data"),
    _s("rds", "RDS", "rds", DATABASE, "data"),
    _s("dynamodb", "DynamoDB", "dynamodb", DATABASE, "data"),
    _s("elasticache", "ElastiCache", "elasticache", DATABASE, "data"),
    _s("redshift", "Redshift", "redshift", DATABASE, "data"),
    _s("opensearch", "OpenSearch", "elasticsearch_service", NETWORK, "data"),
    _s("dms", "DMS", "database_migration_service", DATABASE, "data"),
    _s("athena", "Athena", "athena", NETWORK, "data"),
    _s("lake_formation", "Lake Formation", "lake_formation", NETWORK, "data"),
    _s("quicksight", "QuickSight", "quick_suite", NETWORK, "data"),
    # ops / security
    _s("iam", "IAM", "identity_and_access_management", SECURITY, "ops"),
    _s("kms", "KMS", "key_management_service", SECURITY, "ops"),
    _s("secrets_manager", "Secrets Manager", "secrets_manager", SECURITY, "ops"),
    _s("guardduty", "GuardDuty", "guardduty", SECURITY, "ops"),
    _s("security_hub", "Security Hub", "security_hub", SECURITY, "ops"),
    _s("cloudwatch", "CloudWatch", "cloudwatch_2", INTEG, "ops"),
    _s("cloudtrail", "CloudTrail", "cloudtrail", INTEG, "ops"),
    _s("config", "AWS Config", "config", INTEG, "ops"),
    _s("systems_manager", "Systems Manager", "systems_manager", INTEG, "ops"),
    _s("cloudformation", "CloudFormation", "cloudformation", INTEG, "ops"),
    _s("xray", "X-Ray", "xray", INTEG, "ops"),
    _s("backup", "AWS Backup", "backup", STORAGE, "ops"),
)

SERVICES: dict[str, Service] = {s.key: s for s in _SERVICES}

ALIASES = {
    "apigw": "api_gateway", "apigateway": "api_gateway", "api": "api_gateway",
    "elb": "alb", "load_balancer": "alb", "loadbalancer": "alb",
    "route_53": "route53", "dns": "route53", "cdn": "cloudfront",
    "dynamo": "dynamodb", "ddb": "dynamodb", "postgres": "aurora", "mysql": "aurora",
    "cache": "elasticache", "redis": "elasticache", "elastic_cache": "elasticache",
    "elasticsearch": "opensearch", "kafka": "msk", "queue": "sqs", "topic": "sns",
    "events": "eventbridge", "event_bridge": "eventbridge", "stepfunctions": "step_functions",
    "sfn": "step_functions", "container": "fargate", "k8s": "eks", "kubernetes": "eks",
    "quick_sight": "quicksight", "log": "cloudwatch", "logs": "cloudwatch", "monitoring": "cloudwatch",
    "secrets": "secrets_manager", "ssm": "systems_manager", "web": "users", "browser": "client",
    "mobile_client": "mobile", "kinesis_firehose": "firehose",
}


def _norm(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def lookup(name: str) -> Service | None:
    key = _norm(name)
    return SERVICES.get(ALIASES.get(key, key))


def suggestions(name: str, limit: int = 3) -> list[str]:
    pool = list(SERVICES) + list(ALIASES)
    return difflib.get_close_matches(_norm(name), pool, n=limit, cutoff=0.5)
