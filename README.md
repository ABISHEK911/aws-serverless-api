# Serverless REST API — Lambda + DynamoDB + IAM Least Privilege

A serverless CRUD API built entirely with Terraform, using API Gateway, Lambda,
and DynamoDB. Built as a portfolio project for AWS Cloud Solutions Architect
roles, with the same least-privilege IAM discipline applied in a different
architecture style than a traditional server-based app.

This is a **backend API only** — there's no web frontend. It's meant to be
consumed by clients (curl, Postman, a mobile app, another service, etc.), the
same way a real backend API would be.

## Architecture

```
        Client (curl / Postman / any HTTP client)
                        │
                        ▼
            ┌───────────────────────┐
            │   API Gateway (HTTP)  │
            │   GET    /notes       │
            │   GET    /notes/{id}  │
            │   POST   /notes       │
            │   DELETE /notes/{id}  │
            └───────────┬───────────┘
                        │ AWS_PROXY integration
                        ▼
            ┌───────────────────────┐
            │   Lambda (Python)     │
            │   notes-handler       │
            └───────────┬───────────┘
                        │ IAM role scoped to
                        │ this table only
                        ▼
            ┌───────────────────────┐
            │   DynamoDB            │
            │   notes table         │
            └───────────────────────┘
```

## Why this design (interview talking points)

- **IAM least privilege, applied to serverless.** The Lambda execution role (`iam.tf`) can only perform `GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, `Scan`, and `Query` — and only on this project's specific DynamoDB table ARN, not `dynamodb:*` on every table in the account. Same principle as a traditional EC2 least-privilege role, applied to a different compute model.
- **Explicit invoke permission.** Lambda refuses to be invoked by anything — even a correctly wired API Gateway route — unless explicitly granted via `aws_lambda_permission`, scoped to only `apigateway.amazonaws.com` as the principal.
- **On-demand billing everywhere.** DynamoDB uses `PAY_PER_REQUEST` billing and Lambda/API Gateway are inherently pay-per-invocation — there's no idle hourly cost like a NAT Gateway or RDS instance. This project can be left running far longer than a traditional 3-tier app without meaningful cost.
- **No infrastructure to patch.** No OS, no server, no security groups to manage for the compute layer — the trade-off compared to an EC2-based design, and a genuine talking point on when serverless is (and isn't) the right call.

## Prerequisites

- Terraform >= 1.5.0
- AWS CLI configured (`aws configure`)
- Python 3.12 compatible code (Lambda runtime version used here)

## Deployment

1. **Initialize Terraform** (downloads both the AWS and Archive providers — the Archive provider zips the Lambda code automatically):
   ```bash
   terraform init
   ```

2. **Review the plan:**
   ```bash
   terraform plan
   ```

3. **Apply:**
   ```bash
   terraform apply
   ```
   Type `yes` when prompted. This is fast compared to a VPC-based project — usually under a minute.

4. **Get your API's base URL:**
   ```bash
   aws apigatewayv2 get-apis --query "Items[?Name=='serverless-api-api'].ApiEndpoint" --output text
   ```

## Testing the API

PowerShell (`Invoke-RestMethod`) or `curl.exe` both work. Examples below use PowerShell.

**Create a note:**
```powershell
Invoke-RestMethod -Uri "<YOUR_API_URL>/notes" -Method POST -ContentType "application/json" -Body '{"title":"My note","content":"Hello world"}'
```

**List all notes:**
```powershell
Invoke-RestMethod -Uri "<YOUR_API_URL>/notes" -Method GET
```

**Get one note by ID:**
```powershell
Invoke-RestMethod -Uri "<YOUR_API_URL>/notes/<NOTE_ID>" -Method GET
```

**Delete a note:**
```powershell
Invoke-RestMethod -Uri "<YOUR_API_URL>/notes/<NOTE_ID>" -Method DELETE
```

## Tearing it down

This project stays almost entirely within AWS free tier, but it's still good practice to clean up test resources:

```bash
terraform destroy
```
Type `yes` when prompted.

## Real debugging notes (kept here on purpose)

Two genuine bugs came up during deployment — both are common serverless gotchas worth knowing:

- **Wrong ARN type on the Lambda permission.** `aws_apigatewayv2_api.<name>.arn` returns the API's management ARN, not the invocation-time execution ARN. Using it in `aws_lambda_permission`'s `source_arn` produces a permission that looks valid in the AWS Console but silently fails to match what API Gateway presents at request time — requests return a generic `"Internal Server Error"` and never even reach Lambda (confirmed by an empty CloudWatch log group). Fix: use `aws_apigatewayv2_api.<name>.execution_arn` instead.
- **Payload format version mismatch.** With `payload_format_version = "2.0"` (HTTP API), the HTTP method lives at `event["requestContext"]["http"]["method"]`, not the top-level `event["httpMethod"]` used by the older REST API / payload format 1.0. Code written against the wrong format reaches Lambda successfully but silently falls through to an "unsupported route" branch instead of matching the intended handler.

Both were diagnosed by testing Lambda directly with `aws lambda invoke` (bypassing API Gateway entirely) to isolate whether the bug was in Lambda/DynamoDB or in the API Gateway wiring — a useful debugging pattern for any Lambda-behind-API-Gateway setup.

## Project structure

| File | Purpose |
|---|---|
| `provider.tf` | Terraform, AWS provider, and Archive provider configuration |
| `variables.tf` | Input variables |
| `dynamodb.tf` | DynamoDB table (on-demand billing) |
| `iam.tf` | Least-privilege Lambda execution role and policies |
| `lambda.tf` | Lambda function resource + code packaging |
| `lambda_function.py` | Python CRUD handler (get/list/create/delete) |
| `api_gateway.tf` | HTTP API, routes, integration, invoke permission |

## Possible extensions

- Add an `UpdateItem` route (`PUT /notes/{id}`) to complete full CRUD with update
- Add Cognito authentication so the API isn't publicly writable by anyone
- Add request validation on the API Gateway routes
- Add a simple static frontend (S3 + CloudFront) that calls this API
- Add DynamoDB Streams + a second Lambda to demonstrate event-driven processing
