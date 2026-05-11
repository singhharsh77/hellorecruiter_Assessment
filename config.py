import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class ModelSpec(BaseModel):
    name: str
    description: str
    compute_level: str

# Difficulty to Model mapping
MODELS = {
    "EASY": ModelSpec(
        name="gemini-2.5-flash-lite",
        description="Fast, cost-effective model for general purpose queries with less computing requirements.",
        compute_level="Low"
    ),
    "MID": ModelSpec(
        name="gemini-2.5-flash",
        description="Balanced model capable of handling moderate logic and coding tasks.",
        compute_level="Medium"
    ),
    "TOUGH": ModelSpec(
        name="gemini-2.5-pro",
        description="Advanced reasoning model suitable for tough development projects and complex architectures.",
        compute_level="High"
    )
}

CLASSIFIER_PROMPT = """
You are an intelligent routing agent. Your job is to classify the difficulty of the user's question.
Categorize the question into exactly ONE of the following three categories:

- EASY: General purpose questions, basic knowledge, simple explanations, requiring very little computation or reasoning.
- MID: Intermediate questions, basic to moderate coding problems, script writing, standard debugging.
- TOUGH: Complex development projects, system architecture design, hard algorithmic challenges, multi-step reasoning tasks.

Respond with ONLY ONE WORD: "EASY", "MID", or "TOUGH"

User Question: {question}
"""
