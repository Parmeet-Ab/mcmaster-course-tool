from bs4 import BeautifulSoup
import requests
import re
import time
import math
import xml.etree.ElementTree as ET

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#Trust the site skip SSL verification since the site is not secure and we just want to scrape data from it



header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    } #to avoid being blocked by the website

def get_courses():
    page = 1 #needed to go through all pages of courses
    courses = []

    for i in range(1):
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


def _get_active_terms():
    r = requests.get(
        'https://mytimetable.mcmaster.ca/api/v2/multiselectdata.js',
        headers=header, verify=False
    )
    # Term IDs appear as the 4th argument in MsiInstitution(...) calls
    ids = re.findall(r'MsiInstitution\([^,]+,[^,]+,[^,]+,"(\d+)"', r.text)
    return sorted(set(ids), reverse=True)  # most recent first


def get_professor_for_course(course_code):
    # Auth tokens required by the timetable API — replicates nWindow() from common.js
    t = int(math.floor(time.time() / 60)) % 1000
    e = t % 3 + t % 39 + t % 42

    terms = _get_active_terms()

    encoded = requests.utils.quote(course_code, safe='')
    for term in terms:
        url = (
            f'https://mytimetable.mcmaster.ca/api/class-data'
            f'?term={term}&course_0_0={encoded}'
            f'&va_0_0=al&t={t}&e={e}&nouser=1'
        )
        response = requests.get(url, headers=header, verify=False)
        if response.status_code != 200:
            continue

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            continue

        for block in root.iter('block'):
            if block.get('type') == 'LEC':
                teacher = block.get('teacher', '').strip()
                if teacher:
                    return teacher

    return None


def get_course_detail(course_code):
    encoded = requests.utils.quote(course_code, safe='')
    url = (
        'https://academiccalendars.romcmaster.ca/content.php'
        '?catoid=65&catoid=65&navoid=14802'
        '&filter%5Bitem_type%5D=3&filter%5Bonly_active%5D=1'
        f'&filter%5B3%5D=1&filter%5Bcpage%5D=1&filter%5Bkeyword%5D={encoded}'
    )
    response = requests.get(url, headers=header, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')

    normalized = course_code.replace(' ', '').upper()

    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'preview_course_nopop' not in href:
            continue
        # Confirm the link text matches the requested course code before fetching
        link_text = link.get_text(strip=True).replace(' ', '').upper()
        if not link_text.startswith(normalized):
            continue
        course_url = 'https://academiccalendars.romcmaster.ca/' + href
        time.sleep(1)
        return get_course_details(course_url)

    return None


def get_professor_rating(professor_name):
    MCMASTER_ID = 'U2Nob29sLTEwMTE='
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
    return {
        'name': f"{node['firstName']} {node['lastName']}",
        'avg_rating': node['avgRating'],
        'avg_difficulty': node['avgDifficulty'],
        'num_ratings': node['numRatings'],
    }


if __name__ == "__main__":
    print(get_course_details('https://academiccalendars.romcmaster.ca/preview_course_nopop.php?catoid=65&coid=323026'))