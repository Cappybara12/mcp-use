# Dashboard

Vite + React dashboard for the Graftcode content-pipeline demo. It does not call
a REST API: the dev-server middleware in `vite.config.ts` imports the generated
Graft package and calls the Python receiver directly.

Run it through `bash ../scripts/start.sh` (see the root README).
