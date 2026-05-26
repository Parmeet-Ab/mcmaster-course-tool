from bs4 import BeautifulSoup
import requests 

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#Trust the site skip SSL verification since the site is not secure and we just want to scrape data from it



header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    } #to avoid being blocked by the website

def get_courses():
    page = 1 #needed to go through all pages of courses
    courses = []

    for i in range(33):
        url = 'https://academiccalendars.romcmaster.ca/content.php?catoid=65&catoid=65&navoid=14802&filter%5Bitem_type%5D=3&filter%5Bonly_active%5D=1&filter%5B3%5D=1&filter%5Bcpage%5D=' + str(page) + '#acalog_template_course_filter'  
        
        response = requests.get(url, headers=header, verify = False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
  
        
        for link in soup.find_all('a', href = True):
            href = link['href']
            #Prevents non course links from being added to the list
            if 'preview_course_nopop' in href:
                courses.append({
                    'title': link.text.strip(),
                    'url': url + "/" + href
                }) 

        print(f"Page {page} scraped, total courses found: {len(courses)}")

        page += 1
        
    
    return courses

if __name__ == "__main__":
    courses = get_courses()
    for course in courses[:-1]:
        print(course['title'], course['url'])