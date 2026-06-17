import os
import google.generativeai as genai
from dotenv import load_dotenv
from scraper import get_course_detail, get_professor_for_course, get_professor_rating

load_dotenv()


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.1-flash-lite")


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
