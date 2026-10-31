# One image per service: docker build --build-arg SERVICE=sensing -f deploy/Dockerfile .
FROM python:3.12-slim
ARG SERVICE
WORKDIR /app
COPY ${SERVICE}/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
ENV PYTHONPATH=/app PYTHONUTF8=1
