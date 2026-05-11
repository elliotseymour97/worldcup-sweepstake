FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 1 --threads 4
