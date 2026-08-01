FROM python:3.11-slim

# Install Tor and essential utilities (procps provides pkill, pgrep)
RUN apt-get update && apt-get install -y tor procps && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ff_gen_bot.py .

EXPOSE 10000

CMD ["python", "ff_gen_bot.py"]
