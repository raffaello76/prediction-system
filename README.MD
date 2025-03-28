# Bitcoin Prediction System

Questo progetto implementa un sistema distribuito e containerizzato per la previsione del prezzo del Bitcoin, utilizzando una pipeline basata su microservizi con Kafka, Docker e modelli di Machine Learning.

## Architettura dei Servizi

Ogni servizio ha un ruolo ben definito nella pipeline:

---

### 📁 `data-fetcher/`
- **Scopo**: Raccoglie dati grezzi da API esterne (es. CoinGecko).
- **Output**: Pubblica i dati grezzi su Kafka (topic `raw-data`).

---

### 📁 `data-preprocessor/`
- **Scopo**: Pulisce e trasforma i dati per il modello ML.
- **Input**: Dati da `data-fetcher`.
- **Output**: Pubblica i dati preprocessati su Kafka (topic `cleaned-data`).

---

### 📁 `model-trainer/`
- **Scopo**: Allena un modello ML sui dati preprocessati.
- **Output**: Salva il modello in `models/` (formato `.h5`, `.pkl`, ecc).

---

### 📁 `predictor/`
- **Scopo**: Usa il modello allenato per fare predizioni.
- **Output**: Invia predizioni a Kafka (topic `predictions`).

---

### 📁 `analysis-service/`
- **Scopo**: Analizza le predizioni e decide se generare un alert.
- **Output**: Invia messaggi su un topic di alert o triggera notifiche.

---

### 📁 `notifier-service/`
- **Scopo**: Invia notifiche (es. Telegram) quando riceve un alert.
- **Input**: Messaggi da Kafka (`alerts`).
- **Configurazione**: Supporta più `TELEGRAM_CHAT_IDS`, separati da virgola.

---

### 📁 `models/`
- **Scopo**: Volume condiviso tra `model-trainer` e `predictor` per contenere i modelli ML.

---

## Avvio e Stop del Sistema

### ▶️ Start
```bash
./start.sh
```

### ⏹️ Stop
```bash
./stop.sh
```

## Ambiente Docker
- I servizi sono definiti nel file `docker-compose.yml`
- Kafka e Zookeeper sono utilizzati per l'orchestrazione degli eventi tra servizi
- I servizi personalizzati (`data-fetcher`, `model-trainer`, ecc.) sono containerizzati via Dockerfile

## Variabili d'Ambiente Importanti
- `TELEGRAM_TOKEN`: token del bot Telegram
- `TELEGRAM_CHAT_IDS`: lista di chat ID separati da virgola (es. `-100124,-10058`)

## Requisiti
- Docker + Docker Compose
- Connessione Internet per il fetch dei dati


