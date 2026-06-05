from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, request
from flask_cors import CORS
from scraper import get_course_detail, get_professor_for_course, get_professor_rating

app = Flask(__name__)
CORS(app)

@app.route("/course", methods=['GET'])
def get_course():
    course_code = request.args.get('code')
    if not course_code:
        return jsonify({"error": "Course code is required"}), 400

    course_code = course_code.upper().strip()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_course = executor.submit(get_course_detail, course_code)
        future_professor = executor.submit(get_professor_for_course, course_code)
        course = future_course.result()
        professor_name = future_professor.result()

    if not course:
        return jsonify({"error": f"Course '{course_code}' not found"}), 404

    professor_rating = get_professor_rating(professor_name) if professor_name else None

    return jsonify({
        "course": course,
        "professor": {
            "name": professor_name,
            "rating": professor_rating,
        },
    })


if __name__ == "__main__":
    app.run(debug=True)
