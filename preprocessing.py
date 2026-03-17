"""
preprocessing.py — Text cleaning pipeline for VeriNews
Steps: clean → remove stopwords → stem
"""
import re
import string
import os
import tempfile
import nltk

# Download NLTK resources on first run
# Add a writable directory to search path for server environments
nltk_data_dir = os.path.join(tempfile.gettempdir(), 'nltk_data')
os.makedirs(nltk_data_dir, exist_ok=True)
nltk.data.path.append(nltk_data_dir)

for resource in ['stopwords', 'punkt']:
    try:
        nltk.data.find(f'tokenizers/{resource}' if resource == 'punkt' else f'corpora/{resource}')
    except LookupError:
        nltk.download(resource, download_dir=nltk_data_dir, quiet=True)

from nltk.corpus import stopwords
from nltk.stem import LancasterStemmer

_STOP_WORDS = set(stopwords.words('english'))
_STEMMER = LancasterStemmer()

# URL / HTML / special char patterns
_URL_RE = re.compile(r'http\S+|www\.\S+')
_HTML_RE = re.compile(r'<[^>]+>')
_PUNCT = str.maketrans('', '', string.punctuation)
_DIGIT_RE = re.compile(r'\d+')
_WHITESPACE_RE = re.compile(r'\s+')


def clean_text(text: str) -> str:
    """Remove HTML, URLs, punctuation, digits and normalise whitespace."""
    text = text.lower()
    text = re.sub(r'<script\b[^>]*>.*?</script>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    text = _HTML_RE.sub(' ', text)
    text = _URL_RE.sub(' ', text)
    text = text.translate(_PUNCT)
    text = _DIGIT_RE.sub(' ', text)
    text = _WHITESPACE_RE.sub(' ', text).strip()
    return text


def remove_stopwords(text: str) -> str:
    """Remove English stopwords."""
    tokens = text.split()
    tokens = [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]
    return ' '.join(tokens)


def stem_text(text: str) -> str:
    """Apply PorterStemmer to each token."""
    tokens = text.split()
    tokens = [_STEMMER.stem(t) for t in tokens]
    return ' '.join(tokens)


def preprocess(text: str) -> str:
    """Full preprocessing pipeline: clean → stopword removal → stemming."""
    if not text or not text.strip():
        return ''
    text = clean_text(text)
    text = remove_stopwords(text)
    text = stem_text(text)
    return text
