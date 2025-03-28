#!/bin/bash
# Attendi che Kafka sia raggiungibile
echo "Attendo che Kafka sia pronto su kafka:9092..."
while ! nc -z kafka 9092; do
  sleep 1
done
echo "Kafka è pronto!"

# Avvia il servizio originale passato come parametro
exec python3 "$@"

