FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN echo "nameserver 8.8.8.8\nnameserver 1.1.1.1" > /etc/resolv.conf && \
    pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENTRYPOINT ["/bin/sh", "-c"]
CMD ["python3 -u main.py"]
