.PHONY: infra run migrate seed milvus ingest bootstrap smoke test lint

infra:
	docker start edu_agent_postgres edu_agent_etcd edu_agent_minio edu_agent_milvus

run:
	cd backend && powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1

migrate:
	cd backend && .venv/Scripts/alembic.exe upgrade head

seed:
	cd backend && .venv/Scripts/python.exe scripts/seed_admin.py

milvus:
	cd backend && .venv/Scripts/python.exe scripts/init_milvus.py

ingest:
	cd backend && .venv/Scripts/python.exe scripts/ingest_shopify.py

bootstrap:
	cd backend && .venv/Scripts/python.exe scripts/ingest_bootstrap.py

smoke:
	cd backend && .venv/Scripts/python.exe scripts/smoke_local.py

test:
	cd backend && .venv/Scripts/pytest.exe -p no:cacheprovider

lint:
	cd backend && .venv/Scripts/ruff.exe check app scripts tests --no-cache
