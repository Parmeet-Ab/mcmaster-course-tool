import os
from dotenv import load_dotenv
import anthropic
from scraper import get_course_detail, get_professor_for_course, get_professor_rating

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


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

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a helpful McMaster University course advisor. "
                    "Based on the following course and professor data, write a concise, "
                    "student-friendly summary covering:\n"
                    "1. What the course is about (in plain language)\n"
                    "2. How hard it is (based on units, prerequisites, and professor difficulty)\n"
                    "3. What the professor is like (based on their RMP rating)\n\n"
                    "Write 3-4 short paragraphs in plain language a first-year student would understand. "
                    "If any data is missing, work with what is available.\n\n"
                    f"Course Information:\n{course_info}"
                ),
            }
        ],
    )

    return message.content[0].text


if __name__ == "__main__":
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "COMPSCI 1JC3"
    print(get_course_summary(code))
