# Makefile — Database setup, document loading, and sentiment analysis
# Project root path
PROJECT_DIR := /Users/be/Documents/DT-LLM-SDM

# === PYTHON & PATH VARIABLES ===
PYTHON := python3
DB_PATH := $(PROJECT_DIR)/app.db
DOC_DIR := $(PROJECT_DIR)/data/dev/documents

# === SCRIPT PATHS ===
CREATE_TABLES_SCRIPT := $(PROJECT_DIR)/persistence/scripts/create_tables.py
ADD_DOCUMENT_SCRIPT  := $(PROJECT_DIR)/tasks/add_document.py
SENTIMENT_SCRIPT     := $(PROJECT_DIR)/tasks/analyse_sentiment_sentence.py

# === DATABASE TASKS ===
reset-db:
	@echo "🗑️  Removing existing database..."
	rm -f $(DB_PATH)

create-tables:
	@echo "🧩 Creating tables..."
	$(PYTHON) $(CREATE_TABLES_SCRIPT)

add-doc1:
	@echo "📄 Adding doc01..."
	$(PYTHON) $(ADD_DOCUMENT_SCRIPT) --json-path $(DOC_DIR)/doc01.json

add-doc2:
	@echo "📄 Adding doc02..."
	$(PYTHON) $(ADD_DOCUMENT_SCRIPT) --json-path $(DOC_DIR)/doc02.json

add-doc1-existing:
	@echo "📄 Adding doc01 again (testing duplicates)..."
	$(PYTHON) $(ADD_DOCUMENT_SCRIPT) --json-path $(DOC_DIR)/doc01.json --skip-duplicates

init-db: reset-db create-tables add-doc1 add-doc2 add-doc1-existing
	@echo "✅ Database initialized successfully."


# === SENTIMENT ANALYSIS TASKS ===
analyze-negative:
	@echo "😡 Running NEGATIVE sentiment analysis..."
	$(PYTHON) $(SENTIMENT_SCRIPT) "This product is absolutely terrible and broke after one day."

analyze-neutral:
	@echo "😐 Running NEUTRAL sentiment analysis..."
	$(PYTHON) $(SENTIMENT_SCRIPT) "The product arrived yesterday. It looks exactly as described."

analyze-positive:
	@echo "😊 Running POSITIVE sentiment analysis..."
	$(PYTHON) $(SENTIMENT_SCRIPT) "I love this product! It works perfectly and exceeded my expectations."

analyze-override:
	@echo "🔄 Re-running POSITIVE sentiment analysis with override..."
	$(PYTHON) $(SENTIMENT_SCRIPT) "I love this product! It works perfectly and exceeded my expectations." --persist-override

analyze-with-id1:
	@echo "Running sentiment analysis on sentence ID 1..."
	$(PYTHON) $(SENTIMENT_SCRIPT) "Gross domestic product expanded by 4.1% in the first quarter of 2025, reflecting strong consumer demand." --sentence-id 1

analyze-with-id2:
	@echo "Running sentiment analysis on sentence ID 2..."
	$(PYTHON) $(SENTIMENT_SCRIPT) "The report also notes that employment levels remained broadly unchanged compared to the previous year." --sentence-id 2

analyze-with-id3-false-id:
	@echo "Running sentiment analysis on sentence ID 3..."
	$(PYTHON) $(SENTIMENT_SCRIPT) "Global spending on artificial intelligence grew by 15% in 2025, with most investment concentrated in cloud-based services." --sentence-id 3
analyze-with-id3-true-id:
	@echo "Running sentiment analysis on sentence ID 4..."
	$(PYTHON) $(SENTIMENT_SCRIPT) "Global spending on artificial intelligence grew by 15% in 2025, with most investment concentrated in cloud-based services." --sentence-id 4



analyze-sentiment-samples: analyze-negative analyze-neutral analyze-positive analyze-override
	@echo "✅ All sentiment analyses completed successfully."


# === INIT DB + SENTIMENT ANALYSIS ===
run-all: init-db analyze-sentiment-samples
	@echo "🎉 All tasks completed successfully!"