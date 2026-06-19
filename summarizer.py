import os
import google.generativeai as genai
from dotenv import load_dotenv
from scraper import get_course_detail, get_professor_for_course, get_professor_rating

load_dotenv()


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.1-flash-lite")


def shorten_requisite(text, kind="prerequisite"):
    """Condense a prerequisite/antirequisite string into the shortest possible
    form — course codes and essential conditions only — so it fits in the
    narrow extension popup. Returns None if there is nothing to shorten."""
    if not text or not text.strip():
        return None

    prompt = (
        f"Condense this McMaster course {kind} into the shortest possible form. "
        "Keep only course codes and essential conditions. Drop filler such as "
        "'Registration in', 'Completion of', 'one of', 'or both of'. Use commas "
        "and slashes instead of words where possible. Aim for under 60 characters. "
        "Return ONLY the condensed text with no label or extra words.\n\n"
        f"{kind.capitalize()}: {text}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()


def get_short_summary(course):
    """Return a 2-sentence, plain-language summary of a course for the top of the
    popup. `course` is the dict from scraper.get_course_detail. Returns None if
    there is no course data."""
    if not course:
        return None

    prompt = (
        "Write EXACTLY 2 short sentences summarizing this McMaster course in plain "
        "language a first-year student would understand. Say what the course is "
        "about and roughly what to expect. Do not mention the professor. Do not use "
        "bullet points. Return only the 2 sentences.\n\n"
        f"Title: {course.get('title', 'N/A')}\n"
        f"Units: {course.get('units', 'N/A')}\n"
        f"Description: {course.get('description') or 'Not available'}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()
