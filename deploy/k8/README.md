# Kubernetes deployment manifests

This folder contains example Kubernetes manifests for running the ledger service and its dependencies.

## Apply manifests

Build the application image before deploying:

```bash
docker build -t ledger-api:latest -f deploy/docker/django/Dockerfile.prod .
```

Then apply the manifests:

```bash
kubectl apply -k deploy/k8/
```

## Components

- `postgres.yaml` — PostgreSQL deployment, service, and PVC
- `redis.yaml` — Redis deployment, service, and PVC
- `api.yaml` — Django API deployment and ClusterIP service
- `celery.yaml` — Celery worker deployment

## Notes

- The example uses `ledger-api:latest` for both the API and Celery worker. Replace this image reference with your registry image if needed.
- `DB_PASSWORD` and other runtime secrets are configured in plain text for example purposes; use Kubernetes Secrets for production deployments.
