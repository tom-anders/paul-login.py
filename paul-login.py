import requests
import os
import re
import sys
import yaml
import getpass
from bs4 import BeautifulSoup

base_url = "https://paul.uni-paderborn.de"
usr_file = "usr.yaml"


def extract_meta_redirect(html):
    """
    Check if the returned array has any elements to proceed with the parsing!
    """
    return re.findall(
        r'(?<=metahttp-equiv="refresh"content="0;URL=)[^"]*', html)


def prepare_html(r):
    # I have no idea why there are \0 characters in some responses
    # In those responses there are also 2 strange starting bytes
    # which we filter out by translate()
    # noinspection PyTypeChecker
    table = dict.fromkeys(map(ord, '\0'), None)
    text = r.content.decode('utf-8', 'ignore')
    text = "".join(text.split())
    return text.translate(table)


def follow_redirects(start_url):
    """
    We follow the redirects until we reach a page where we are not
    redirected anymore.
    """
    r = requests.get(start_url)
    suffix = ''
    while True:
        html = prepare_html(r)
        redirect = extract_meta_redirect(html)
        if len(redirect) == 0:
            break
        suffix = redirect[0]
        r = requests.get(base_url + suffix)
    return base_url + suffix


def login_by_credentials():
    print('Starting log in...')
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "User-Agent": "User-Agent:Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "paul.uni-paderborn.de",
        "Origin": "https://paul.uni-paderborn.de",
        "Upgrade-Insecure-Requests": "1"
    }
    if os.path.exists(usr_file):
        with open(usr_file, encoding='utf-8') as f:
            y = yaml.load(f.read())
            username = y["username"]
            password = y["password"]
    else:
        username = input("Username: ")
        password = getpass.getpass()
        print('\n Note: Create a file "{file}" and fill it with your information for faster login:\n\n'
              'username: your_username\n'
              'password: your_password\n'.format(file=usr_file))

    data = {
        "usrname": username,
        "pass": password,
        "APPNAME": "CampusNet",
        "PRGNAME": "LOGINCHECK",
        "ARGUMENTS": "clino,usrname,pass,menuno,menu_type,browser,platform",
        "clino": "000000000000001",
        "menuno": "000435",
        "menu_type": "classic",
        "browser": "",
        "platform": ""
    }
    r = requests.post("https://paul.uni-paderborn.de/scripts/mgrqispi.dll",
                      headers=headers, data=data)
    if 'REFRESH' in r.headers:
        url = re.findall(r"(?<=URL=).*", r.headers['REFRESH'])[0]
    else:
        print("\nLogin failed! Are your credentials correct?")
        print("Note that this can rarely fail even though you set the "
              "correct credentials!")
        sys.exit(1)
    final_url = follow_redirects(base_url + url)
    r = requests.get(final_url)
    if 'Herzlich willkommen' in r.text:
        print('Login successful!')
    else:
        print('Something broke :(')
    
    return r


def find_courses(r):
    print("Fetching courses...")
    # Find "Studium" link
    soup = BeautifulSoup(r.text, 'html.parser')
    studium = soup.find('a', attrs={'class', 'depth_1 link000454 navLink branchLink folder'})
    # Find "Semesterverwaltung"
    r = requests.get(base_url + studium['href'])
    soup = BeautifulSoup(r.text, 'html.parser')
    semesterverwaltung = soup.find('a', attrs={'class', 'depth_2 link000455 navLink branchLink '})
    # Find "Veranstaltungsuebersicht"
    r = requests.get(base_url + semesterverwaltung['href'])
    soup = BeautifulSoup(r.text, 'html.parser')
    uebersicht = soup.find('a', attrs={'class', 'depth_3 link000459 navLink '})
   
    # return a list of all your courses in the current term
    r = requests.get(base_url + uebersicht['href'])
    r.encoding = 'utf-8' 
    soup = BeautifulSoup(r.text, 'html.parser')
    courses = soup.findAll('a', {'name': 'eventLink'})
    return courses


def download_material(course):
    # Remove " - Übung" and "(Übung)" from course name
    name = course.text
    if ' - ' in name: 
        name = course.text.split(' - ')[0]
    elif '(Übung)' in name:
        name = course.text.split(' (Übung)')[0]
    if not os.path.exists(name):
        os.makedirs(name)

    print("Downloading new files for {}...".format(name))

    # Find files
    r = requests.get(base_url + course['href'])
    r.encoding = 'utf-8' 
    soup = BeautifulSoup(r.text, 'html.parser')
    material = soup.findAll('a', {'href': re.compile('filetransfer')})

    # Download files
    count = 0
    for m in material:
        filename = name + "/" + m.text
        if not os.path.exists(filename):  # Only download new files
            print("    " + m.text) 
            count += 1
            r = requests.get(base_url + m['href'])
            with open(filename, 'wb') as file:
                file.write(r.content)
    if count == 0:
        print("    No new files!")


if __name__ == '__main__':
    r = login_by_credentials()
    courses = find_courses(r)
    
    for c in courses:
        download_material(c)

