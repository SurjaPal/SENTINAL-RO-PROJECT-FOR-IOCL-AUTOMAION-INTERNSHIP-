@echo off
echo ========================================================
echo Starting Sentinel-RO Complete Stack
echo ========================================================

echo.
echo Building Docker Images (this may take a few minutes)...
docker compose build

echo.
echo Starting all containers...
docker compose up -d

echo.
echo ========================================================
echo Stack is now running!
echo.
echo Frontend UI:   http://localhost:8080
echo Grafana:       http://localhost:3000 (admin/sentinel)
echo.
echo To view logs, run: docker compose logs -f
echo To stop stack, run: docker compose down
echo ========================================================
pause
