# review-analyzer

![Stars](https://img.shields.io/badge/stars-0-brightgreen) ![Forks](https://img.shields.io/badge/forks-0-blue) ![Language](https://img.shields.io/badge/language-Python-orange)

AI-Driven Customer Review Analyzer using Streamlit and Hugging Face NLP models (BERTweet for Sentiment, BART-MNLI for Classification, BART-CNN for Summarization). Upload a CSV of reviews to get key metrics, sentiment breakdown, top themes, and automated summaries.

## Overview

**Project Overview and Features**
=====================================

The Review Analyzer is an AI-driven customer review analysis tool that uses state-of-the-art NLP models to analyze sentiment, categorize feedback, and extract actionable insights from customer reviews.

**Key Features**
---------------

* **AI-Powered Analysis**:
	+ Sentiment Analysis: Classify reviews as Positive, Negative, or Neutral using BERTweet
	+ Category Classification: Automatically categorize reviews into topics (Product Quality, Shipping, Customer Service, etc.)
	+ Review Summarization: Generate concise summaries from multiple reviews using BART-CNN
	+ Keyword Extraction: Identify key terms from positive and negative reviews
* **Interactive Dashboard**:
	+ Real-time Analytics: Visualize sentiment distribution, category breakdowns, and trends
	+ Advanced Filtering: Filter reviews by sentiment, category, rating, and keywords
	+ Custom Visualizations: Interactive Plotly charts with multiple themes
	+ Confidence Scores: View model confidence for each prediction
* **Deep Dive Analysis**:
	+ Keyword Analysis: Discover most common words in positive/negative reviews
	+ Sentiment by Category: See how sentiment varies across different topics
	+ Rating Correlation: Analyze relationship between ratings and sentiment
	+ Review Explorer: Search and browse individual reviews with full metadata
* **Export Capabilities**:
	+ Download filtered results as CSV
	+ Export complete analyzed dataset
	+ Timestamped file naming for version control

## Tech Stack

**Tech Stack**
===============

The following are the main technologies, languages, frameworks, and tools used in the `review-analyzer` repository:

### Backend

* **Python 3.8+**: Primary programming language
* **Streamlit**: Framework for building web applications
* **Hugging Face Transformers**: Library for NLP models (BERTweet, BART-MNLI, BART-CNN)

### Frontend

* **Streamlit**: Framework for building web applications

### Database

* **CSV**: Input data format for review text and optional rating columns

### Tooling

* **SpaCy**: Library for natural language processing
* **Pip**: Package manager for Python dependencies
* **Git**: Version control system

## Installation

**Installation**
===============

### Prerequisites
----------------

* Python 3.8 or higher
* 4GB+ RAM recommended
* GPU optional (will use CPU if not available)

### Installation Steps
----------------------

1. **Clone the repository**
   ```bash
git clone https://github.com/yourusername/review-analyzer.git
cd review-analyzer
```
2. **Create a virtual environment** (recommended)
   ```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```
3. **Install dependencies**
   ```bash
pip install -r requirements.txt
```
4. **Download spaCy language model**
   ```bash
python -m spacy download en_core_web_sm
```

### Running the Application
---------------------------

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`.

## Usage

**Usage**
================

### Uploading and Analyzing Reviews

To upload and analyze reviews, follow these steps:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm

# Run the application
streamlit run app.py
```

### Example Use Case

Upload a CSV file with review text and optional rating columns:

```csv
review_text,rating
"Great product! Exceeded my expectations.",5
"Shipping was delayed by 3 days.",2
"Good value for money. Would recommend.",4
"Poor quality. Broke after one week.",1
"Decent product but overpriced.",3
```

Configure settings, load models, and analyze reviews:

1. Click "Browse files" and select your review data.
2. Set sample size (0 = analyze all reviews) and choose visualization theme.
3. Click "Load & Initialize Models" and wait for models to download and initialize.
4. Click "Analyze Reviews" and view key metrics, sentiment distribution, category analysis, and confidence distribution.

### Dashboard Tab

View high-level analytics, including:

* Key Metrics: Total reviews, sentiment breakdown, confidence scores
* Sentiment Distribution: Visual breakdown of positive/negative/neutral
* Category Analysis: Most common review topics
* Confidence Distribution: Model prediction reliability

## Contributing

**Contributing to Review Analyzer**
=====================================

### Filing Issues

* Report bugs, feature requests, or questions to the [GitHub Issues page](https://github.com/vedikakute06/review-analyzer/issues).
* Please provide a clear description of the issue and any relevant details.

### Creating Pull Requests

* Fork the repository and create a new branch for your changes.
* Make sure to follow the [coding style guidelines](#coding-style-guidelines) below.
* Submit a pull request to the main branch with a clear description of the changes.

### Coding Style Guidelines

* We follow the [PEP 8 style guide](https://www.python.org/dev/peps/pep-0008/) for Python code.
* Use consistent naming conventions and formatting throughout the codebase.

### Further Guidelines

* For more information on contributing to Review Analyzer, please refer to the [README.md](README.md) file.
* If you have any questions or need help, feel free to ask on the [GitHub Issues page](https://github.com/vedikakute06/review-analyzer/issues).

## License

This project is licensed under the terms specified in the repository.
