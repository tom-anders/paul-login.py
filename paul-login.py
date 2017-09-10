import requests
import re
import sys

base_url = "https://paul.uni-paderborn.de"
# fill in your login data here
username = 'TODO'
password = 'TODO'


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
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "User-Agent": "User-Agent:Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "paul.uni-paderborn.de",
        "Origin": "https://paul.uni-paderborn.de",
        "Upgrade-Insecure-Requests": "1"
    }
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
        name = re.findall(r'(?<=Herzlich willkommen,)[^!]*', r.text)[0].strip()
        print('\nYou are logged in!\nWelcome {}!'.format(name))
    else:
        print('Something broke :(')


if __name__ == '__main__':
    # https://paul.uni-paderborn.de/scripts/mgrqispi.dll?APPNAME=CampusNet&PRGNAME=EXTERNALPAGES&ARGUMENTS=-N000000000000001,-N000435,-Awelcome
    # This was just a test and this is not needed to login at all!
    # The actual login will be done by a POST in login_by_credentials()
    paul_login_page = follow_redirects(base_url)
    print("This is the URL where you see the username "
          "and password login forms: {}".format(paul_login_page))

    login_by_credentials()
