FROM python:3.11-slim

# Install Tor
RUN apt-get update && apt-get install -y tor && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY ff_gen_bot.py .

# Expose the port Render expects
EXPOSE 10000

# Start the bot
CMD ["python", "ff_gen_bot.py"]
