#!/bin/bash

echo "🛑 Arresto e pulizia del sistema..."
docker compose down -v

echo "✅ Tutti i container, volumi e reti rimossi."

