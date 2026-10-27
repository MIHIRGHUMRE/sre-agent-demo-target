# Safe Demo SRE Target

This repository is a deliberately buggy, local-only demonstration service for a Self-Healing SRE agent workflow. It is not production code and it does not contain real credentials, secrets, or user data.

## Purpose

This app is intentionally small, simple, and compatible with the target repository contract used by the SRE agent. It exposes the endpoints required by the integration:

- `/` - basic service information
- `/health` - health status
- `/api/data` - normal success path by default, and a controlled demo failure when the `X-Trigger-Bug: true` header is sent

## Python version

This demo is intended for Python 3.11.

## Local setup

```bash
python -m venv .venv
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the service

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

- `http://localhost:8000/`
- `http://localhost:8000/health`
- `http://localhost:8000/api/data`

## Trigger the controlled demo failure

Send the special header:

```bash
curl -i http://localhost:8000/api/data -H "X-Trigger-Bug: true"
```

This intentionally raises a `KeyError` from a local dictionary lookup and returns a generic `500` response. The application logs that event to the repository root file `app_logs.txt` and to the console, but it does not expose secrets or stack traces to clients.

## Validation checks

### Healthy endpoint

```bash
curl -i http://localhost:8000/health
```

Expected response: HTTP 200 with a JSON object containing `"status": "healthy"`.

### Normal data request

```bash
curl -i http://localhost:8000/api/data
```

Expected response: HTTP 200 with a JSON body containing `"status": "success"`.

### Intentional 500 response

```bash
curl -i http://localhost:8000/api/data -H "X-Trigger-Bug: true"
```

Expected response: HTTP 500 with a generic error detail.

### PowerShell equivalents

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
Invoke-RestMethod -Uri http://localhost:8000/api/data
Invoke-RestMethod -Uri http://localhost:8000/api/data -Headers @{ "X-Trigger-Bug" = "true" }
```

## Notes

- The app writes request logs and error information to `app_logs.txt` in the repository root.
- The repository does not include a `.env` file, secrets, or credentials.
- This is a safe, local-only demo target and not a production monitoring or autonomous remediation system.
