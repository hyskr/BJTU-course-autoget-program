import base64
import json
import re
import time
from urllib import parse
from bs4 import BeautifulSoup
import requests

username = ""
password = ""

course = ["网球07", "网球14"]
uid = ["", ""]
userid = ""
uname = ""
pwd = ""
appToken = ""

def base64_api(img, typeid):
    base64_data = base64.b64encode(img)
    b64 = base64_data.decode()
    data = {"username": uname, "password": pwd, "typeid": typeid, "image": b64}
    result = json.loads(requests.post(
        "http://api.ttshitu.com/predict", json=data).text)
    if result['success']:
        return result["data"]["result"]
    else:
        return result["message"]
    return ""


def get_cookie(username, password):
    headers = {
        'authority': 'mis.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    url = "https://mis.bjtu.edu.cn/auth/sso/?next=/"
    response = requests.request(
        "GET", url, headers=headers, allow_redirects=False)
    url = response.headers.get('Location')
    time.sleep(1)
    print(".", end="")
    response = requests.request(
        "GET", url, headers=headers, allow_redirects=False)
    url = "https://cas.bjtu.edu.cn" + response.headers.get('Location')
    time.sleep(1)
    response = requests.request(
        "GET", url, headers=headers, allow_redirects=False)
    csrftoken = response.headers.get('Set-Cookie').split(';')[0].split('=')[1]
    text = response.text
    _id = re.findall(r"captcha/image/(.*)?/\"", text)[0]
    src = 'https://cas.bjtu.edu.cn/captcha/image/' + _id
    img = requests.get(src).content

    csrfmiddlewaretoken = re.findall(
        r"csrfmiddlewaretoken\" value=\"(.*)?\">", text)[0]
    nex_url = re.findall(r"next\" value=\"(.*?) />",
                         text)[0].replace("&amp;", "&").strip(" \"")[:-1]
    # print(_id, nex_url, csrfmiddlewaretoken, sep = "\n")
    # exit()
    result = base64_api(img=img, typeid=11)

    # login

    url = f"https://cas.bjtu.edu.cn/auth/login/?next={nex_url}"

    payload = {
        "next": nex_url,
        "csrfmiddlewaretoken": csrfmiddlewaretoken,
        "loginname": username,
        "password": password,
        "captcha_0": _id,
        "captcha_1": result
    }
    headers = {
        'authority': 'cas.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': f'csrftoken={csrftoken}; ',
        'origin': 'https://cas.bjtu.edu.cn',
        'referer': 'https://cas.bjtu.edu.cn/auth/login/?next=' + parse.quote(nex_url),
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    time.sleep(1)
    r = requests.request("POST", url, headers=headers,
                         data=payload, allow_redirects=False)
    c = r.headers.get('Set-Cookie')
    cookie = re.findall(r'csrftoken=.*?;',
                        c)[0] + " " + re.findall(r'sessionid=.*?;', c)[0]
    url = "https://cas.bjtu.edu.cn" + r.headers.get('Location')
    headers = {
        'authority': 'cas.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'cookie': cookie[:-1],
        'referer': url,
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    time.sleep(1)
    print(".", end="")
    r = requests.request("GET", url, headers=headers, allow_redirects=False)

    headers = {
        'authority': 'mis.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        # 'cookie': 'csrftoken=6xpjNpmRrrtBp2XY4l2gpBwQeKLGnmF2OdJHrqodNvk57Rgns16MgSq7MzYIpEKR',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    url = r.headers.get('Location')
    time.sleep(1)
    print(".", end="")
    r = requests.request("GET", url, headers=headers,
                         data=payload, allow_redirects=False)
    c = r.headers.get('Set-Cookie')
    print(".", end="")
    cookie = re.findall(r'csrftoken=.*?;',
                        c)[0] + " " + re.findall(r'sessionid=.*?;', c)[0]

    headers = {
        'authority': 'mis.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cookie': cookie,
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    url = "https://mis.bjtu.edu.cn/module/module/10/"
    time.sleep(1)
    print(".", end="")
    response = requests.request("GET", url, headers=headers)

    text = response.text
    url = re.findall(r"<form action=\"(.*?)\"", text)[0]

    payload = {}
    headers = {
        'authority': 'aa.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'referer': 'https://mis.bjtu.edu.cn/',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    time.sleep(1)
    print(".", end="")
    r = requests.request("GET", url, headers=headers,
                         data=payload, allow_redirects=False)

    c = r.headers.get('set-cookie')
    cookie = re.findall(r'csrftoken=.*?;',
                        c)[0] + " " + re.findall(r'sessionid=.*?;', c)[0]
    print(" finished!!!")
    print(cookie)

    url = "https://aa.bjtu.edu.cn/schoolcensus/schoolcensus/stucensuscard/"

    payload = {}
    headers = {
        'authority': 'aa.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'cookie': cookie,
        'referer': 'https://aa.bjtu.edu.cn/notice/item/',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }

    r = requests.request("GET", url, headers=headers, data=payload)
    global userid
    t = r.text
    userid = re.findall("<small>欢迎您，</small>(.*)\n", t)[0]
    print(userid, " 登陆成功!!!")
    return cookie


def send(content, uid):
    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = json.dumps({
        "appToken": appToken,
        "content": userid + content,
        "contentType": 1,
        "uids": uid
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)



def get_all(cookie):
    url = f"https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?kch=&kxh=&gname2020=&action=load&order=&iframe=school&submit=&has_advance_query=&page=1&perpage=500"

    payload = {}
    headers = {
        'authority': 'aa.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'cookie': cookie,
        'referer': 'https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?kch=108009B+%E7%94%9F%E6%B4%BB%E4%B8%AD%E7%9A%84%E7%94%9F%E7%89%A9%E5%AD%A6+01+%E7%89%A9%E5%B7%A5%E5%AD%A6%E9%99%A2%09&kxh=&gname2020=&action=load&order=&iframe=school&submit=&has_advance_query=',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }

    r = requests.request("GET", url, headers=headers, data=payload)
    data = []
    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table')
    if not table:
        return -1
    rows = table.find_all('tr')
    for row in rows:
        # print(rows)
        cols = row.find_all('td')
        if cols and cols[0].input:
            value = cols[0].input['value']
        cols = [ele.text.strip().replace("\n", "").replace(" ", "")
                for ele in cols]
        if cols:
            if cols[0] == "":
                cols[0] = value
            for i in course:
                if i.replace(" ", "") in cols[2]:
                    data.append(cols)
    return data

def submit(cookie, checkbox):
    url = "https://aa.bjtu.edu.cn/captcha/refresh/"
    payload = {}
    headers = {
        'authority': 'aa.bjtu.edu.cn',
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cookie': cookie,
        'referer': 'https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects/',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    key = response.json()['key']
    src = 'https://aa.bjtu.edu.cn/captcha/image/' + key
    headers = {
        'authority': 'aa.bjtu.edu.cn',
        'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cookie': cookie,
        'referer': 'https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects/',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    print(src)
    response = requests.request("GET", src, headers=headers)
    img = response.content
    result = base64_api(uname='heziah', pwd='tT39eCpPmK2n', img=img, typeid=16)
    print(result)
    payload = f"checkboxs={checkbox}&hashkey={key}&answer={parse.quote(result)}"
    print(payload)
    url = "https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?action=submit"
    headers = {
        'authority': 'aa.bjtu.edu.cn',
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'cookie': cookie,
        'origin': 'https://aa.bjtu.edu.cn',
        'referer': 'https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?kch&kxh&gname2020=3&action=load&order&iframe=school&submit&has_advance_query&page=1&perpage=200',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    time.sleep(0.1)
    messages = response.cookies.get_dict()['messages']

    url = "https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects/"

    payload = {}
    headers = {
        'authority': 'aa.bjtu.edu.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'cookie': cookie + "messages=" + messages,
        'referer': 'https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects/',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    text = response.text

    t = re.findall(r'message \+= "(.*)<br/>";', text)

    return t

cookie = get_cookie(username, password)


while True:
    url = "https://aa.bjtu.edu.cn/course_selection/courseselecttask/remains/?college=&kch=&jsh=8297&skxq=&skjc=&has_advance_query="
    data = get_all(cookie)
    if data == -1:
        print("---get_cookie...")
        send("cookie重新获取", ["UID_EM6DPDJpqmywihJDbzRTmeCPQrMr"])
        cookie = get_cookie(username, password)
        continue
    print(userid, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    for i in data:
        print(f"{i[2]}, {i[6]}, {i[3]}")
        if int(i[3]) > 0 and i[0].isdigit():
            print("正在抢课........................")
            send(f"正在抢课，{i[2]}, {i[6]}, {i[3]}", uid)
            t = submit(cookie, i[0])
            print("抢课成功", t)
            send(f"抢课成功，{t}", uid)

    print("--------------------------------------------------------------------")
