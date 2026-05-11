import os
from google import genai
from google.genai import types
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from config import MODELS, CLASSIFIER_PROMPT
import re
try:
    from cache_db import search_cache, save_to_cache
except ImportError:
    # Fallback if DB isn't set up yet
    search_cache = lambda q: None
    save_to_cache = lambda q, a, m: None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# ---------------------------------------------------------
# TIER 2: Local ML Classifier Setup (Zero API Calls)
# ---------------------------------------------------------
# A tiny dummy dataset to train our instant local router
X_train = [
    "what is a variable", "how to write a for loop", "what is html", "hello", "hi there", "what is the capital of india",
    "write a python script to reverse an array", "how to sort a list", "find the maximum element", "debug this error",
    "design a microservice architecture", "how to deploy kubernetes", "build a highly available backend", "system design"
]
y_train = ["EASY", "MID", "EASY", "EASY", "EASY", "EASY", "MID", "MID", "MID", "MID", "TOUGH", "TOUGH", "TOUGH", "TOUGH"]

local_clf = make_pipeline(TfidfVectorizer(), MultinomialNB())
local_clf.fit(X_train, y_train)

class RateLimitExceeded(Exception):
    pass

# Initialize the Gemini client
# We will initialize the client dynamically inside the function to ensure the API key is loaded
client = None

# Rate limit retry configuration
# Retries on 429
# Wait 2^x * 1 second between each retry starting with 2 seconds, then up to 10 seconds, then 10 seconds afterwards
@retry(
    retry=retry_if_exception_type((RateLimitExceeded, Exception)), # Broad exception catch
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5)
)
def call_gemini(model_name: str, prompt: str) -> str:
    """Wrapper to call Gemini API with rate limit handling."""
    global client
    if not client:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            raise ValueError("GEMINI_API_KEY is missing or invalid.")
        client = genai.Client(api_key=api_key)
        
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        # Tenacity will retry on any exception matching our criteria
        if "429" in str(e) or "quota" in str(e).lower():
            raise RateLimitExceeded(str(e))
        raise

def classify_question(question: str) -> str:
    """Classifies the question using Heuristics first, then LLM if needed."""
    
    # ---------------------------------------------------------
    # TIER 1: Heuristic Pre-Routing (Zero API Calls)
    # ---------------------------------------------------------
    word_count = len(question.split())
    
    # Rule 1: Very short questions are EASY
    if word_count < 4:
        return "EASY"
        
    # Rule 2: Contains complex dev keywords -> TOUGH
    tough_pattern = r'\b(architecture|microservice|database design|system design|kubernetes|docker|deployment|scale)\b'
    if re.search(tough_pattern, question, re.IGNORECASE):
        return "TOUGH"
        
    # Rule 3: Contains basic coding keywords -> MID
    mid_pattern = r'\b(def|class|function|script|python|javascript|loop|array)\b'
    if re.search(mid_pattern, question, re.IGNORECASE):
        return "MID"
        
    # ---------------------------------------------------------
    # TIER 2: Local ML Classification (Replaces LLM Call)
    # ---------------------------------------------------------
    # Instead of an API call, we use our lightning-fast offline model
    predicted = local_clf.predict([question])[0]
    return predicted

def call_gemini_stream(model_name: str, prompt: str, difficulty: str):
    """Wrapper to call Gemini API with streaming and tool usage."""
    global client
    if not client:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            raise ValueError("GEMINI_API_KEY is missing or invalid.")
        client = genai.Client(api_key=api_key)
        
    config = None
    # Agentic Workflow: Give Google Search tool to TOUGH models
    if difficulty == "TOUGH":
        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0.7
        )
        
    try:
        response_stream = client.models.generate_content_stream(
            model=model_name,
            contents=prompt,
            config=config
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            raise RateLimitExceeded(str(e))
        raise

def process_query_stream(question: str):
    """End-to-end processing of a user query, returning a generator and metadata."""
    
    # 1. Classify
    difficulty = classify_question(question)
    
    # 2. Select Model
    selected_spec = MODELS[difficulty]
    model_name = selected_spec.name
    
    metadata = {
        "difficulty": difficulty,
        "model_name": model_name,
        "model_description": selected_spec.description + (" (Agent: Internet Access Enabled)" if difficulty == "TOUGH" else ""),
        "compute_level": selected_spec.compute_level,
        "cached": False
    }
    
    # 3. Return the stream generator and metadata
    stream_generator = call_gemini_stream(model_name, question, difficulty)
    
    return stream_generator, metadata
