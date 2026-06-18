from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, request, make_response
from scraper import get_course_detail, get_professor_for_course, get_professor_rating

app = Flask(__name__)
app.url_map.provide_automatic_options = False

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Private-Network': 'true',
}

@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        res = make_response('', 200)
        for k, v in CORS_HEADERS.items():
            res.headers[k] = v
        return res

@app.after_request
def cors_headers(response):
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    return response

@app.route("/course", methods=['GET'])
def get_course():
    course_code = request.args.get('code')
    if not course_code:
        return jsonify({"error": "Course code is required"}), 400

    course_code = course_code.upper().strip()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_course = executor.submit(get_course_detail, course_code)
        future_prof = executor.submit(get_professor_for_course, course_code)
        course = future_course.result()
        term_data = future_prof.result()  # { term_id: { term_name, professor } } or None

    if not course:
        return jsonify({"error": f"Course '{course_code}' not found"}), 404

    # Fetch RMP rating once per unique professor name
    professors = []
    if term_data:
        unique_names = {v['professor'] for v in term_data.values() if v.get('professor')}
        ratings = {name: get_professor_rating(name) for name in unique_names}

        professor_list = []
        for tid, tdata in term_data.items():
            professor_list.append({
                'term_id': tid,
                'term_name': tdata['term_name'],
                'name': tdata['professor'],
                'rating': ratings.get(tdata['professor']),
            })

        professors = sorted(professor_list, key=lambda x: x['term_id'])

    return jsonify({
        "course": course,
        "professors": professors,
    })


if __name__ == "__main__":
    app.run(debug=True, port=8080)
