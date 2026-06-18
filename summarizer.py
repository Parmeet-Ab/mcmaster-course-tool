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


def get_course_summary(course_code):
    course = get_course_detail(course_code)
    professor_name = get_professor_for_course(course_code)
    professor_rating = get_professor_rating(professor_name) if professor_name else None

    sections = [f"Course: {course_code}"]

    if course:
        sections.append(f"Title: {course.get('title', 'N/A')}")
        sections.append(f"Units: {course.get('units', 'N/A')}")
        sections.append(f"Description: {course.get('description') or 'Not available'}")
        if course.get('prerequisites'):
            sections.append(f"Prerequisites: {course['prerequisites']}")
        if course.get('antirequisites'):
            sections.append(f"Antirequisites: {course['antirequisites']}")

    if professor_name:
        sections.append(f"\nProfessor: {professor_name}")

    if professor_rating:
        sections.append(f"RMP Overall Rating: {professor_rating['avg_rating']}/5.0")
        sections.append(f"RMP Difficulty: {professor_rating['avg_difficulty']}/5.0")
        sections.append(f"Number of Ratings: {professor_rating['num_ratings']}")
    elif professor_name:
        sections.append("RMP Rating: Not found")

    course_info = "\n".join(sections)

    prompt = (
        "You are a helpful McMaster University course advisor. "
        "Based on the following course and professor data, write a concise, "
        "student-friendly summary covering:\n"
        "1. What the course is about (in plain language)\n"
        "2. How hard it is (based on units, prerequisites, and professor difficulty)\n"
        "3. What the professor is like (based on their RMP rating)\n\n"
        "Write 3-4 short paragraphs in plain language a first-year student would understand. "
        "If any data is missing, work with what is available.\n\n"
        f"Course Information:\n{course_info}"
    )

    response = model.generate_content(prompt)
    return response.text


if __name__ == "__main__":
    #only runs if the courses are acctually posted on the website, otherwise use test case
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "COMPSCI 1JC3"
    print(get_course_summary('CHEM 1A03'))
