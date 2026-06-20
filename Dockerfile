FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libzbar0 libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Pré-installer torch CPU-only avant easyocr pour éviter le pull des libs CUDA (~2GB)
RUN pip install --no-cache-dir \
    torch==2.2.2+cpu torchvision==0.17.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Installer le reste (easyocr verra torch déjà installé, skip CUDA)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
