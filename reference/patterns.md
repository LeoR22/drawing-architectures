# High-level AWS patterns (pick, adapt, generate)

Each pattern has a ready spec in `examples/`. Adapt labels and add or remove components rather than starting from scratch.

| Need | Pattern | Core services | Example |
|---|---|---|---|
| Web app / SPA with API and login | Serverless web | CloudFront, S3, API Gateway, Cognito, Lambda, DynamoDB | `examples/serverless-web.json` |
| Steady traffic, containers, SQL | Containerized three-tier | WAF, ALB, Fargate, Aurora, ElastiCache | `examples/containers-three-tier.json` |
| Ingest events, analytics, BI | Event-driven analytics | API Gateway, EventBridge, SQS, Lambda, S3, Glue, Athena, QuickSight | `examples/event-driven-analytics.json` |

## Quick choices

- Compute: spiky or small -> Lambda; steady containers -> Fargate (ECS); Kubernetes required -> EKS; lift and shift -> EC2.
- Database: key-value, massive scale -> DynamoDB; relational -> Aurora; search -> OpenSearch; analytics -> S3 + Athena or Redshift.
- Async work: decouple with SQS; fan-out with SNS; routing with EventBridge; multi-step with Step Functions.
- GenAI: Bedrock behind the API; add OpenSearch or Aurora for retrieval (RAG).
- Streaming/IoT: Kinesis or MSK -> Firehose -> S3.
- Edge/security: CloudFront + WAF for web; Cognito for users; KMS and Secrets Manager for keys and secrets.
- Always: CloudWatch. Compliance asks: CloudTrail, Config, GuardDuty.

## Keep it high level

6-14 components. Group repeated pieces (one "Microservices (Fargate)" box, not eight). Show data flow left to right: actors, edge, application, data, operations.
