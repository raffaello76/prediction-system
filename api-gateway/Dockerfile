FROM python:3.10-slim

# Imposta la working directory
WORKDIR /app

# Copia i requisiti e installali
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto dei file
COPY . .

# Espone la porta 5001 dal container
EXPOSE 5001

# Avvia lo script Python
CMD ["python", "api_gateway.py"]
