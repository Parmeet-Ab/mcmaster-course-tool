from bs4 import BeautifulSoup
import requests
import re
import time
import math
import xml.etree.ElementTree as ET
import json
import os
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

_session_cookie = os.getenv('MCMASTER_SESSION', '')

_COURSE_INDEX_PATH = os.path.join(os.path.dirname(__file__), 'data', 'courses.json')
_PROF_INDEX_PATH   = os.path.join(os.path.dirname(__file__), 'data', 'professors.json')


def _load_course_index():
    if not os.path.exists(_COURSE_INDEX_PATH):
        return {}
    with open(_COURSE_INDEX_PATH) as f:
        return json.load(f)

def _load_prof_index():
    if not os.path.exists(_PROF_INDEX_PATH):
        return {}
    with open(_PROF_INDEX_PATH) as f:
        return json.load(f)

_course_index = _load_course_index()
_prof_index   = _load_prof_index()


def build_course_index():
    """Scrape all catalog pages and save a normalized_code→url index to data/courses.json.
    Run this once per semester to refresh."""
    index = {}
    for page in range(1, 35):
        url = (
            'https://academiccalendars.romcmaster.ca/content.php'
            '?catoid=65&catoid=65&navoid=14802'
            '&filter%5Bitem_type%5D=3&filter%5Bonly_active%5D=1'
            f'&filter%5B3%5D=1&filter%5Bcpage%5D={page}'
        )
        response = requests.get(url, headers=header, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')

        links = [l for l in soup.find_all('a', href=True) if 'preview_course_nopop' in l['href']]
        if not links:
            break

        for link in links:
            title = link.get_text(strip=True)
            code_part = title.split(' - ')[0].strip()
            normalized = code_part.replace(' ', '').upper()
            if normalized:
                index[normalized] = 'https://academiccalendars.romcmaster.ca/' + link['href']

        print(f"Page {page} scraped — index size: {len(index)}")
        time.sleep(1)

    with open(_COURSE_INDEX_PATH, 'w') as f:
        json.dump(index, f)
    print(f"Saved {len(index)} courses to {_COURSE_INDEX_PATH}")
    return index 

_cached_terms = None
def _get_active_terms():
    global _cached_terms
    if _cached_terms:
        return _cached_terms
    r = requests.get(
        'https://mytimetable.mcmaster.ca/api/v2/multiselectdata.js',
        headers=header, verify=False
    )
    ids = re.findall(r'MsiInstitution\([^,]+,[^,]+,[^,]+,"(\d+)"', r.text)
    # Ascending order = earliest active term first (current semester has professors assigned)
    _cached_terms = sorted(set(ids))
    return _cached_terms


def _te():
    t = int(math.floor(time.time() / 60)) % 1000
    return t, t % 3 + t % 39 + t % 42

def build_professor_index():
    """Pre-scrape professor assignments using batched API calls.
    Run once per semester when timetable data is published (3x/year).
    Stores per-term data so a course taught by different profs each term is tracked. Batches 10 courses per request — O(N/10) calls instead of O(N)."""
    global _prof_index

    course_index = _load_course_index()
    # normalized (e.g. MATH1A03) -> api_code (e.g. MATH-1A03)
    all_courses = {
        norm: re.sub(r'^([A-Za-z]+)', r'\1-', norm)
        for norm in course_index
    }

    req_headers = {**header}
    if _session_cookie:
        req_headers['Cookie'] = _session_cookie
    auth_suffix = '' if _session_cookie else '&nouser=1'

    terms = _get_active_terms()
    # Structure: { normalized: { term_id: { term_name, professor } } }
    prof_index = {}
    items = list(all_courses.items())
    BATCH = 10

    for term in terms:
        found_this_term = 0

        for start in range(0, len(items), BATCH):
            batch = items[start:start + BATCH]

            # Step 1: va=al to get selection va tokens for the whole batch
            t, e = _te()
            params1 = ''.join(
                f'&course_{i}_0={requests.utils.quote(api, safe="")}&va_{i}_0=al&rq_{i}_0='
                for i, (_, api) in enumerate(batch)
            )
            r1 = requests.get(
                f'https://mytimetable.mcmaster.ca/api/class-data?term={term}{params1}&t={t}&e={e}{auth_suffix}',
                headers=req_headers, verify=False, timeout=10,
            )
            if r1.status_code != 200:
                time.sleep(0.3)
                continue
            try:
                root1 = ET.fromstring(r1.text)
            except ET.ParseError:
                time.sleep(0.3)
                continue

            # course key → first va token; also grab the human-readable term name
            va_map = {}
            term_name = term
            for el in root1.iter():
                if el.tag == 'term' and el.get('v'):
                    term_name = el.get('v')
                if el.tag == 'course':
                    key = el.get('key', '')
                    for sel in el.iter('selection'):
                        va = sel.get('va', '')
                        if va:
                            va_map[key] = va
                            break

            step2 = [
                (norm, api, va_map[api])
                for norm, api in batch
                if api in va_map
            ]
            if not step2:
                time.sleep(0.3)
                continue

            # Step 2: specific va tokens → teacher names
            t, e = _te()
            params2 = ''.join(
                f'&course_{i}_0={requests.utils.quote(api, safe="")}&va_{i}_0={va}&rq_{i}_0='
                for i, (_, api, va) in enumerate(step2)
            )
            r2 = requests.get(
                f'https://mytimetable.mcmaster.ca/api/class-data?term={term}{params2}&t={t}&e={e}{auth_suffix}',
                headers=req_headers, verify=False, timeout=10,
            )
            if r2.status_code != 200:
                time.sleep(0.3)
                continue
            try:
                root2 = ET.fromstring(r2.text)
            except ET.ParseError:
                time.sleep(0.3)
                continue

            api_to_norm = {api: norm for norm, api, _ in step2}
            for course_el in root2.iter('course'):
                norm = api_to_norm.get(course_el.get('key', ''))
                if not norm:
                    continue
                for block in course_el.iter('block'):
                    if block.get('type') != 'LEC':
                        continue
                    raw = block.get('teacher', '').strip()
                    if not raw:
                        continue
                    names = [n.strip() for n in raw.split(';')]
                    prof = next((n for n in names if n.lower() != 'staff' and n), None)
                    if prof:
                        if norm not in prof_index:
                            prof_index[norm] = {}
                        prof_index[norm][term] = {
                            'term_name': term_name,
                            'professor': prof,
                        }
                        found_this_term += 1
                        break

            if (start // BATCH) % 50 == 49:
                with open(_PROF_INDEX_PATH, 'w') as f:
                    json.dump(prof_index, f, indent=2)

            time.sleep(0.3)

        print(f"Term {term} ({term_name}): +{found_this_term} assignments, {len(prof_index)} courses with data")

    with open(_PROF_INDEX_PATH, 'w') as f:
        json.dump(prof_index, f, indent=2)

    _prof_index = prof_index
    print(f"Saved {len(prof_index)} courses with professor data to {_PROF_INDEX_PATH}")
    return prof_index


def get_professor_for_course(course_code):
    """Return per-term professor data from the pre-built index.
    Returns { term_id: { term_name, professor } } or None."""
    normalized = course_code.replace(' ', '').upper()
    return _prof_index.get(normalized)

def get_course_details(url):
    response = requests.get(url, headers=header, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')

    td = soup.find('td', class_='block_content')
    if not td:
        return None
    p = td.find('p')
    if not p:
        return None

    h1 = p.find('h1', id='course_preview_title')
    title = h1.get_text(strip=True) if h1 else None

    units = None
    if h1:
        for sibling in h1.next_siblings:
            if hasattr(sibling, 'name') and sibling.name == 'br':
                break
            if isinstance(sibling, str):
                match = re.search(r'(\d+(?:\.\d+)?)\s+unit', sibling)
                if match:
                    units = float(match.group(1))
                    break

    description_parts = []
    hr = p.find('hr')
    if hr:
        for sibling in hr.next_siblings:
            if hasattr(sibling, 'name') and sibling.name == 'strong':
                break
            if isinstance(sibling, str):
                text = sibling.strip()
                if text:
                    description_parts.append(text)
    description = ' '.join(description_parts).strip()

    prerequisites = None
    antirequisites = None
    for strong in p.find_all('strong'):
        label = strong.get_text(strip=True)
        parts = []
        for sibling in strong.next_siblings:
            if hasattr(sibling, 'name') and sibling.name == 'br':
                break
            if isinstance(sibling, str):
                text = sibling.strip()
                if text:
                    parts.append(text)
            elif hasattr(sibling, 'name'):
                parts.append(sibling.get_text(strip=True))
        value = ' '.join(parts).strip() or None
        if 'Prerequisite(s)' in label:
            prerequisites = value
        elif 'Antirequisite(s)' in label:
            antirequisites = value

    course_code = None
    if title:
        match = re.match(r'^([A-Z\s]+\s+\w+)', title)
        if match:
            course_code = match.group(1).strip()

    return {
        'title': title,
        'course_code': course_code,
        'units': units,
        'description': description,
        'prerequisites': prerequisites,
        'antirequisites': antirequisites,
    }

def get_course_detail(course_code):
    normalized = course_code.replace(' ', '').upper()
    if normalized in _course_index:
        return get_course_details(_course_index[normalized])
    else:
        return None


def get_professor_rating(professor_name):
    MCMASTER_ID = 'U2Nob29sLTE0NDA='
    query = """
    query TeacherSearch($count: Int!, $query: TeacherSearchQuery!) {
      search: newSearch {
        teachers(query: $query, first: $count) {
          edges {
            node {
              firstName
              lastName
              avgRating
              avgDifficulty
              numRatings
              school { id }
            }
          }
        }
      }
    }
    """
    payload = {
        'query': query,
        'variables': {
            'count': 5,
            'query': {'text': professor_name, 'schoolID': MCMASTER_ID},
        },
    }
    rmp_headers = {
        **header,
        'Authorization': 'Basic dGVzdDp0ZXN0',
        'Content-Type': 'application/json',
    }
    try:
        response = requests.post(
            'https://www.ratemyprofessors.com/graphql',
            json=payload,
            headers=rmp_headers,
            verify=False,
            timeout=10,
        )
        edges = (
            response.json()
            .get('data', {})
            .get('search', {})
            .get('teachers', {})
            .get('edges', [])
        )
    except Exception:
        return None

    if not edges:
        return None

    node = edges[0]['node']
    if node.get('school', {}).get('id') != MCMASTER_ID:
        return None

    search_tokens = set(re.sub(r'[,.]', '', professor_name.lower()).split())
    if node['lastName'].lower() not in search_tokens:
        return None

    return {
        'name': f"{node['firstName']} {node['lastName']}",
        'avg_rating': node['avgRating'],
        'avg_difficulty': node['avgDifficulty'],
        'num_ratings': node['numRatings'],
    }

if __name__ == "__main__":
    if not os.path.exists(_COURSE_INDEX_PATH):
        build_course_index()
    elif not os.path.exists(_PROF_INDEX_PATH):
        build_professor_index()

