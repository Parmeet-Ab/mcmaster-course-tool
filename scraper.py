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

_mcmaster_cookie = os.getenv('MCMASTER_SESSION', '')

_COURSE_INDEX_PATH = os.path.join(os.path.dirname(__file__), 'data', 'courses.json')

def _load_course_index():
    if not os.path.exists(_COURSE_INDEX_PATH):
        return {}
    with open(_COURSE_INDEX_PATH) as f:
        return json.load(f)

_course_index = _load_course_index()


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


def get_courses():
    page = 1 #needed to go through all pages of courses
    courses = []

    for i in range(1, 35):
        url = 'https://academiccalendars.romcmaster.ca/content.php?catoid=65&catoid=65&navoid=14802&filter%5Bitem_type%5D=3&filter%5Bonly_active%5D=1&filter%5B3%5D=1&filter%5Bcpage%5D=' + str(page) + '#acalog_template_course_filter'  
        
        response = requests.get(url, headers=header, verify = False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
  
        
        for link in soup.find_all('a', href = True):
            href = link['href']
            #Prevents non course links from being added to the list
            if 'preview_course_nopop' in href:
                courses.append({
                    'title': link.text.strip(),
                    'url': 'https://academiccalendars.romcmaster.ca/' + href #speicific URL giving quick summary of course
                }) 

        print(f"Page {page} scraped, total courses found: {len(courses)}") #to track progress

        page += 1
        
    return courses


def get_course_details(url):
    response = requests.get(url, headers=header, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')

    td = soup.find('td', class_='block_content')
    if not td:
        return None

    p = td.find('p')
    if not p:
        return None

    # Title
    h1 = p.find('h1', id='course_preview_title')
    title = h1.get_text(strip=True) if h1 else None

    # Units — text node immediately after h1, before first <br>
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

    # Description — all text between <hr> and the first <strong>
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

    # Prerequisites and antirequisites — text/links after each labeled <strong>
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

    # Extract course code — the part before the first " - " in the title
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
    _cached_terms = sorted(set(ids), reverse=True)
    return _cached_terms


def get_professor_for_course(course_code):
    # Auth tokens required by the timetable API — replicates nWindow() from common.js
    t = int(math.floor(time.time() / 60)) % 1000
    e = t % 3 + t % 39 + t % 42

    terms = _get_active_terms()

    encoded = requests.utils.quote(course_code, safe='')
    req_headers = {**header}
    if _mcmaster_cookie:
        req_headers['Cookie'] = _mcmaster_cookie

    for term in terms:
        url = (
            f'https://mytimetable.mcmaster.ca/api/class-data'
            f'?term={term}&course_0_0={encoded}'
            f'&va_0_0=al&t={t}&e={e}'
            + ('' if _mcmaster_cookie else '&nouser=1')
        )
        response = requests.get(url, headers=req_headers, verify=False)
        if response.status_code != 200:
            continue

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            continue

        for block in root.iter('block'):
            if block.get('type') == 'LEC':
                raw = block.get('teacher', '').strip()
                if not raw:
                    continue
                # Field can be "Last, First; Staff" — pick the first real name
                names = [n.strip() for n in raw.split(';')]
                professor = next((n for n in names if n.lower() != 'staff' and n), None)
                if professor:
                    return professor

    return None


def get_course_detail(course_code):
    normalized = course_code.replace(' ', '').upper()

    # Fast path: direct URL lookup from cached index
    if normalized in _course_index:
        return get_course_details(_course_index[normalized])

    # Slow path: search the calendar page by page (used when index hasn't been built yet)
    encoded = requests.utils.quote(course_code, safe='')
    for page in range(1, 20):
        url = (
            'https://academiccalendars.romcmaster.ca/content.php'
            '?catoid=65&catoid=65&navoid=14802'
            '&filter%5Bitem_type%5D=3&filter%5Bonly_active%5D=1'
            f'&filter%5B3%5D=1&filter%5Bcpage%5D={page}&filter%5Bkeyword%5D={encoded}'
        )
        response = requests.get(url, headers=header, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')

        course_links = [l for l in soup.find_all('a', href=True) if 'preview_course_nopop' in l['href']]
        if not course_links:
            break

        for link in course_links:
            link_text = link.get_text(strip=True).replace(' ', '').upper()
            if not link_text.startswith(normalized):
                continue
            course_url = 'https://academiccalendars.romcmaster.ca/' + link['href']
            time.sleep(1)
            return get_course_details(course_url)

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
              school {
                id
              }
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

    # Normalize search name: strip punctuation like trailing commas (e.g. "Last, First" format)
    search_tokens = set(re.sub(r'[,.]', '', professor_name.lower()).split())
    rmp_last = node['lastName'].lower()
    # Require the last name to match exactly as a token — first-name-only overlap is not enough
    if rmp_last not in search_tokens:
        return None

    return {
        'name': f"{node['firstName']} {node['lastName']}",
        'avg_rating': node['avgRating'],
        'avg_difficulty': node['avgDifficulty'],
        'num_ratings': node['numRatings'],
    }


if __name__ == "__main__":
    build_course_index()