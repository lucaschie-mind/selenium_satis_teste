FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1     DEBIAN_FRONTEND=noninteractive     CHROME_BIN=/usr/bin/chromium     CHROMEDRIVER_PATH=/usr/bin/chromedriver     PORT=8501

RUN apt-get update && apt-get install -y --no-install-recommends     chromium     chromium-driver     fonts-liberation     ca-certificates     unzip     wget     curl     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0"]
