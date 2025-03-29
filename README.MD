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


┌─────────────────────────────┐
│ BinanceDataFetcherService   │
│ - Recupera i dati BTCUSDT   │
│   da Binance (candlestick)  │
│ - Invia i dati al topic:    │
│   "bitcoin_data"            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   DataPreprocessor Service  │
│ - Consuma i dati dal topic  │
│   "bitcoin_data"            │
│ - Esegue preprocessing:     │
│   • Calcolo indicatori      │
│     tecnici (MA, volatilità, │
│       returns, ecc.)        │
│   • Creazione di sequenze   │
│     per LSTM                │
│ - Pubblica i dati processati│
│   su "preprocessed_bitcoin_data"  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  ModelTrainerService        │
│ - Consuma le sequenze da    │
│   "preprocessed_bitcoin_data"    │
│ - Addestra il modello LSTM   │
│ - Salva il modello e invia  │
│   i risultati dell'addestramento   │
│   su "model_training_results"      │
└──────────────┬──────────────┘
               │
               ▼
       (Passo facoltativo)
   [Modulo di Predictive Model]
   - Utilizza il modello addestrato per
     generare previsioni sui prezzi
   - Invia le previsioni al topic:
     "bitcoin_predictions"
               │
               ▼
┌─────────────────────────────┐
│   AnalysisService           │
│ - Consuma previsioni dal    │
│   topic "bitcoin_predictions"    │
│ - Recupera l'ultimo prezzo  │
│   dal topic "bitcoin_data"   │
│ - Calcola segnali di trading│
│   e raccomandazioni tramite  │
│   la strategia (BitcoinTradingStrategy) │
│   (in questo esempio stampa i    │
│    risultati, ma in un sistema    │
│    operativo verrebbe inviarli a  │
│    un topic dedicato, es.         │
│    "bitcoin_trading_signals")      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   API Gateway Service       │
│ - Consuma segnali (da "bitcoin_trading_signals") │
│ - Tiene uno storico di segnali e prezzi          │
│ - Espone endpoint REST per:                      │
│    • Stato del sistema                           │
│    • Ultimi segnali                              │
│    • Cronologia dei segnali e dei prezzi         │
│    • Dati per la dashboard                       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   TelegramNotifier Service  │
│ - Consuma segnali da:                           │
│      • "bitcoin_predictions" oppure           │
│      • "bitcoin_trading_signals"                │
│   (a seconda della versione implementata)      │
│ - Formattta il messaggio e invia notifiche via  │
│   Telegram ai canali configurati               │
└─────────────────────────────┘
