import json
import re


def extract_json(text):

    """
    Extract JSON object from messy LLM response.
    """

    if not text:
        raise ValueError("Empty response")


    # -----------------------------------------
    # Remove markdown code fences
    # -----------------------------------------

    cleaned = text.strip()

    cleaned = cleaned.replace("```json", "")
    cleaned = cleaned.replace("```", "")


    # -----------------------------------------
    # Find JSON object
    # -----------------------------------------

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:

        raise ValueError("No JSON found in response")


    json_text = cleaned[start:end + 1]


    # -----------------------------------------
    # Parse JSON
    # -----------------------------------------

    try:

        parsed = json.loads(json_text)

        return parsed

    except json.JSONDecodeError as e:

        print("\n===== INVALID JSON =====\n")
        print(json_text)
        print("\n========================\n")

        raise ValueError(f"JSON decode error: {str(e)}")
