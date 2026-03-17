# VeriNews — System Interaction Specification

## 1. System Overview

VeriNews is an AI-powered misinformation detection platform that analyzes news content submitted by users through multiple input channels.

Supported inputs include:
- Typed text
- Screenshot images
- Social media URLs

The platform processes submitted content using Natural Language Processing (NLP) techniques and machine learning models to determine whether the content is **REAL** or **FAKE**.

Predictions are generated using an **ensemble of Logistic Regression and Naive Bayes models**. All system interactions and processing results are logged for auditing, monitoring, and future model improvement.

---

## 2. System Components

### User Interface

The user interface allows users to interact with the VeriNews platform through a web application.

Users can:
- Submit news text
- Upload screenshots containing news content
- Submit social media URLs
- View prediction results and confidence scores

---

### Flask Backend

The Flask application acts as the central controller of the system.

Responsibilities include:
- Handling user requests
- Routing input to the appropriate processing modules
- Coordinating preprocessing and machine learning pipelines
- Returning prediction results
- Storing logs and metadata

---

### Input Acquisition Module

This module collects and manages user submissions.

Components include:

**UserInput**
Handles direct text input submitted by users.

**MediaUpload**
Manages uploaded screenshots and stores file metadata.

**UrlFetcher**
Receives social media URLs and initiates content retrieval.

---

### Content Extraction

This stage extracts usable text from non-text inputs.

Components:

**OCR Module (EasyOCR)**  
Extracts text from uploaded screenshots.

**URL Fetcher**  
Retrieves textual content and metadata from submitted URLs.

Extracted metadata includes:
- original_url
- author
- post_date
- fetched_text
- fetch_status

---

### Preprocessing Pipeline

Before analysis, text is cleaned and normalized to improve machine learning accuracy.

Preprocessing steps:

1. Text Cleaning
2. Stopword Removal
3. Stemming

The output of this stage is **cleaned text** ready for feature extraction.

---

### Feature Extraction

The cleaned text is transformed into numerical representations using **TF-IDF Vectorization**.

Example configuration:

max_features = 10000  
ngram_range = (1,2)

The resulting output is a **TF-IDF feature vector** representing the importance of words within the text.

---

### Machine Learning Prediction Engine

Two machine learning models independently analyze the feature vector.

Models used:

**Logistic Regression Model**  
Detects linear relationships between textual features and classification labels.

**Naive Bayes Model**  
Performs probabilistic classification optimized for text data.

Each model outputs a prediction label.

Possible labels:

REAL  
FAKE

---

### Ensemble Model

Predictions from the Logistic Regression and Naive Bayes models are combined using **majority voting**.

Example:

Logistic Regression → REAL  
Naive Bayes → FAKE  

Final Decision → REAL

The final decision is stored as the **ensemble result**.

---

### Result Handling and Logging

After prediction, the system records:

- user input data
- preprocessing results
- feature vectors
- model predictions
- ensemble decision
- metadata and timestamps

This information is stored in the **SolutionLog** database table for auditing and debugging.

---

## 3. System Architecture

Overall system interaction flow:

User  
↓  
Flask API  
↓  
Input Module (Text / Image / URL)  
↓  
Content Extraction (OCR / URL Fetcher)  
↓  
Preprocessing  
↓  
TF-IDF Vectorizer  
↓  
Machine Learning Models  
(Logistic Regression + Naive Bayes)  
↓  
Ensemble Voting Model  
↓  
Result Storage and Logging  
↓  
Prediction Returned to User

---

## 4. Input Processing Pipelines

### Text Input Pipeline

1. User submits typed news content.
2. Flask receives the request.
3. Text is sent to the preprocessing module.
4. Cleaned text is vectorized using TF-IDF.
5. Feature vector is passed to both models.
6. Predictions are generated.
7. Ensemble voting produces final label.
8. Result is logged and returned to the user.

---

### Screenshot Input Pipeline

1. User uploads screenshot.
2. MediaUpload module stores image file.
3. OCR Module (EasyOCR) extracts text.
4. OCR returns:
   - extracted_text
   - confidence_score
5. Extracted text is preprocessed.
6. Text is vectorized.
7. Models generate predictions.
8. Ensemble determines final label.
9. Result is stored and returned.

If OCR confidence is low, the system still processes the text but logs the confidence value.

---

### URL Input Pipeline

1. User submits social media URL.
2. URL Fetcher retrieves webpage content.
3. Extracted text and metadata are stored.
4. Text enters preprocessing pipeline.
5. Feature vector generated.
6. Models generate predictions.
7. Ensemble voting produces final result.
8. Results and metadata are logged.

Supported sources include:
- Social media posts
- News websites
- Public webpages

---

## 5. Database Entities

### users

Stores registered user information.

Fields:
user_id  
username  
email  
created_at  
last_login

---

### user_input

Tracks user submissions.

Fields:
input_id  
user_id  
input_type  
media_id  
news_id  
url_id  
submitted_at

---

### media_upload

Stores uploaded screenshots.

Fields:
media_id  
file_name  
file_type  
uploaded_at  
file_size

---

### ocr_result

Stores OCR extraction results.

Fields:
ocr_id  
media_id  
extracted_text  
confidence_score  
processed_at

---

### url_fetch

Stores fetched URL data.

Fields:
url_id  
original_url  
author  
post_date  
fetched_text  
fetch_status

---

### preprocessing

Stores cleaned text outputs.

Fields:
preprocessing_id  
source_type  
cleaned_text  
processed_at

---

### feature_vector

Stores TF-IDF vectors.

Fields:
vector_id  
preprocessing_id  
tfidf_vector  
created_at

---

### model_prediction

Stores predictions from each model.

Fields:
prediction_id  
model_id  
vector_id  
predicted_label  
probability  
predicted_at

---

### ensemble_result

Stores final ensemble decision.

Fields:
ensemble_id  
vector_id  
final_label  
confidence  
decided_at

---

### solution_log

Stores complete system logs.

Fields:
log_id  
input_id  
media_id  
url_id  
fetch_status  
timestamp  
metadata

---

## 6. Error Handling

### OCR Failure

If OCR cannot extract usable text:

- OCR error is logged
- User receives notification
- Processing stops

---

### URL Fetch Failure

If the URL cannot be accessed:

- fetch_status is marked as failed
- error details are logged
- user is notified

---

## 7. Logging and Monitoring

The system logs:

- prediction inputs
- OCR results
- URL fetch attempts
- preprocessing outputs
- model predictions
- ensemble results

Logs help with debugging, performance monitoring, and dataset expansion.

---

## 8. Deployment Strategy

Current environment:
Local development system.

Planned production environment:

Flask  
Gunicorn  
Nginx  
PostgreSQL  
Docker

The system will be deployed on a public server using a registered domain name.

---

## 9. Future Improvements

Potential future enhancements include:

- Transformer-based models such as BERT
- Multilingual misinformation detection
- Social media API integration
- Browser extension for instant verification
- Active learning for continuous model improvement