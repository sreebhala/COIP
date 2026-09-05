FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY tests ./tests
EXPOSE 8000
# Stage 2 fix: seed demo/reference data on container startup so the demo
# works immediately after deployment without a manual extra step. The
# seed script is safe to run on every start — it only inserts rows that
# don't already exist (see app/data/seed.py), so this is not destructive
# on restart. No agent, rule, or decision logic is touched by this change.
CMD ["sh", "-c", "python -m app.data.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
