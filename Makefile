# Makefile — Database setup, document loading, and sentiment analysis
# Project root path
PROJECT_DIR := /Users/be/Documents/DT-LLM-SDM

# === PYTHON & PATH VARIABLES ===
PYTHON := python3
DB_PATH := $(PROJECT_DIR)/app.db
DOC_DIR := $(PROJECT_DIR)/data/dev/documents

# === SCRIPT PATHS ===
CREATE_TABLES_SCRIPT := $(PROJECT_DIR)/persistence/scripts/create_tables.py
ADD_DOCUMENT_SCRIPT  := $(PROJECT_DIR)/persistence/scripts/add_document.py
SENTIMENT_SCRIPT     := $(PROJECT_DIR)/tasks/sentiment_analysis.py

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
	$(PYTHON) $(SENTIMENT_SCRIPT) "I love this product! It works perfectly and exceeded my expectations." --override

analyze-sentiment-samples: analyze-negative analyze-neutral analyze-positive analyze-override
	@echo "✅ All sentiment analyses completed successfully."


# === INIT DB + SENTIMENT ANALYSIS ===
run-all: init-db analyze-sentiment-samples
	@echo "🎉 All tasks completed successfully!"