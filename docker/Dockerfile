# Build/pull explicitly before running with a network-disabled sandbox.
FROM python:3.11.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 65534 runnergroup 2>/dev/null || true
USER 65534:65534
WORKDIR /workspace
CMD ["python", "--version"]
