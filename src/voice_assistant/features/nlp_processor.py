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

            if token.dep_ == "prep":
                phrase = token.text
                for child in token.subtree:
                    if child != token:
                        phrase += " " + child.text
                entities["prep"] = phrase
                print("[Prepositional Phrase]:", phrase)

        # Handle conjunctions (like "and good ratings")
        if "prep" not in entities:
            for token in doc:
                if token.dep_ == "cc":
                    conj_phrase = token.text
                    for sibling in token.head.subtree:
                        if sibling != token and sibling != token.head:
                            conj_phrase += " " + sibling.text
                    entities["prep"] = conj_phrase
                    print("[Conjunction Phrase]:", conj_phrase)

    # --- WhatsApp Special Detection ---
    if "whatsapp" in voice_data.lower() and intent == "unknown":
        intent = "msg_whatsapp"

    # --- Extract Recipient Name and Message ---
    recipient = None
    message = None

    prepositions = ["to", "on", "via", "with"]
    
    # Look for the message after "send"
    if "send" in voice_data.lower():
        try:
            send_index = [i for i, token in enumerate(doc) if token.lemma_ == "send"][0]
            # Extract message (up to 'to' or 'on')
            message_tokens = []
            for token in doc[send_index + 1:]:
                if token.text in ["to", "on", "via", "with", "using"]:
                    break
                message_tokens.append(token.text)
            message = " ".join(message_tokens).strip("'\" ")
        except Exception as e:
            pass

    # Extract recipient name (after 'to', 'on', 'via', etc.)
    for token in doc:
        if token.text.lower() in prepositions:
            recipient_tokens = []
            for t in doc[token.i + 1:]:
                if t.text.lower() in prepositions + ["whatsapp"]:
                    break
                recipient_tokens.append(t.text)
            recipient = " ".join(recipient_tokens).strip("'\" ")
            break

    # --- Final Entities ---
    if message:
        entities["message"] = message
    if recipient:
        entities["recipient"] = recipient

    print("[Intent]:", intent, "[Entities]:", entities)
    return intent, entities