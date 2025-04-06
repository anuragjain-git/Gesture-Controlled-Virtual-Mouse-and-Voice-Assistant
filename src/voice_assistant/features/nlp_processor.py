# File: nlp_processor.py
# Purpose: Process natural language and extract intents/entities

import spacy
from voice_assistant.features.constants import COMMAND_SYNONYMS

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def warm_up_nlp():
    """Prime the spaCy NLP pipeline with a simple phrase."""
    _ = nlp("hello")
    print("NLP warm-up complete.")

def get_intent(voice_data):
    """
    Uses a dictionary of command synonyms to determine the intent and extracts entities using spaCy's NER.
    Fallback: if no entities are found, uses dependency parsing to get the direct object.
    """
    try:
        doc = nlp(voice_data)
    except Exception as e:
        print("NLP Error:", e)
        return "unknown", {}

    intent = "unknown"
    entities = {}

    # Token loop for intent detection using synonyms dictionary.
    for token in doc:
        lemma = token.lemma_.lower()
        for key, synonyms in COMMAND_SYNONYMS.items():
            if lemma in synonyms:
                intent = key
                break
        if intent != "unknown":
            break

    # Use spaCy's NER to extract entities.
    for ent in doc.ents:
        entities[ent.label_] = ent.text
        print("[Entity Detected]:", ent.label_, ent.text)

    # Fallback: if no entities are detected, try to extract a direct object.
    if not entities:
        for token in doc:
            if token.dep_ == "dobj":
                entities["object"] = token.text
                print("[Fallback Entity - dobj]:", token.text)
                break

    print("[Intent]:", intent, "[Entities]:", entities)
    return intent, entities