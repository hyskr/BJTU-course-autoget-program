import sys
import base64
import json
import re
import time
from urllib import parse

import requests
from bs4 import BeautifulSoup, Tag

RETRY_LIMIT = 5
user_name = "" #无需填写，自动获取
sys.stdout.reconfigure(line_buffering=True)


def base64_api(img, typeid):
    base64_data = base64.b64encode(img)
    b64 = base64_data.decode()
    data = {"username": tujian_uname, "password": tujian_pwd, "typeid": typeid, "image": b64}
    result = json.loads(requests.post(
        "http://api.ttshitu.com/predict", json=data).text)
    return result


def get_cookie(username, password):
    BASE_HEADERS = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    global user_name
    try:
        # pbar = tqdm(total=8, desc="Logging in", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
        session = requests.Session()
        session.headers.update(BASE_HEADERS)

        # get captcha
        url = "https://mis.bjtu.edu.cn/auth/sso/?next=/"
        response = session.get(url, allow_redirects=False)
        url = response.headers.get('Location')
        response = session.get(url, allow_redirects=False)
        url = "https://cas.bjtu.edu.cn" + response.headers.get('Location')
        response = session.get(url, allow_redirects=False)
        # pbar.update(1)
        yield {"command": "登录", "std": "正在获取验证码..."}
        time.sleep(1)

        # Extract necessary information for login
        text = response.text
        captcha_id = re.findall(r"captcha/image/(.*)?/\"", text)[0]
        csrfmiddlewaretoken = re.findall(r"csrfmiddlewaretoken\" value=\"(.*)?\">", text)[0]
        nex_url = re.findall(r"next\" value=\"(.*?) />", text)[0].replace("&amp;", "&").strip(" \"")[:-1]
        captcha_img_url = 'https://cas.bjtu.edu.cn/captcha/image/' + captcha_id
        captcha_img = session.get(captcha_img_url).content
        captcha_result = base64_api(img=captcha_img, typeid=1005)
        if captcha_result['success']:
            b64 = "data:image/png;base64," + base64.b64encode(captcha_img).decode()
            captcha_result = captcha_result["data"]["result"]
            yield {"command": "captcha-image", "image": b64, "result": captcha_result}
        else:
            raise Exception("图鉴: " + captcha_result["message"])
        yield {"command": "登录", "std": "正在识别验证码..."}
        time.sleep(1)

        # Login
        url = f"https://cas.bjtu.edu.cn/auth/login/?next={nex_url}"
        payload = {
            "next": nex_url,
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "loginname": username,
            "password": password,
            "captcha_0": captcha_id,
            "captcha_1": captcha_result
        }
        session.headers.update({
            'authority': 'cas.bjtu.edu.cn',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://cas.bjtu.edu.cn',
            'referer': 'https://cas.bjtu.edu.cn/auth/login/?next=' + parse.quote(nex_url),
        })
        response = session.post(url, data=payload, allow_redirects=False)
        yield {"command": "登录", "std": "正在登录..."}
        time.sleep(1)

        # Follow redirects
        url = "https://cas.bjtu.edu.cn" + response.headers.get('Location')
        response = session.get(url, allow_redirects=False)
        time.sleep(1)

        session.headers.update({
            'authority': 'mis.bjtu.edu.cn',
        })
        url = response.headers.get('Location')
        response = session.get(url, allow_redirects=False)
        time.sleep(1)

        url = "https://mis.bjtu.edu.cn/module/module/10/"
        response = session.get(url)
        time.sleep(1)

        text = response.text
        url = re.findall(r"<form action=\"(.*?)\"", text)[0]
        session.headers.update({
            'authority': 'aa.bjtu.edu.cn',
            'referer': 'https://mis.bjtu.edu.cn/',
        })
        response = session.get(url, allow_redirects=False)
        time.sleep(1)

        url = "https://aa.bjtu.edu.cn/schoolcensus/schoolcensus/stucensuscard/"
        session.headers.update({
            'authority': 'aa.bjtu.edu.cn',
            'referer': 'https://aa.bjtu.edu.cn/notice/item/',
        })
        response = session.get(url)
        time.sleep(1)

        user_name = re.findall("<small>欢迎您，</small>(.*)\n", response.text)[0]
        yield {"command": "登录", "std": f"{user_name},  登陆成功!!!"}
        yield session
    except requests.exceptions.RequestException as e:
        yield {"command": "登录", "error": f"Request failed: {e}"}
        sys.exit(1)
    except Exception as e:
        yield {"command": "登录", "error": f"An error occurred: {e}, might be due to incorrect username or password.\nPlease check your username and password and try again. 5s后将自动退出! "}
        sys.exit(1)




BASE_URL = "https://aa.bjtu.edu.cn"
CAPTCHA_REFRESH_URL = f"{BASE_URL}/captcha/refresh/"
COURSE_SELECTION_URL = f"{BASE_URL}/course_selection/courseselecttask/selects/"
COURSE_ACTION_URL = f"{BASE_URL}/course_selection/courseselecttask/selects_action/?action=submit"
MESSAGE_PATTERN = r'message \+= "(.*)<br/>";'

course_name_col_num = 1 # 课程名所在列数
course_num_col_num = 2 # 课程号所在列数
course_teacher_col_num = 6 # 课程教师所在列数

def submit(session, checkbox, cookie=None):
    BASE_HEADERS = {
        'accept': '*/*',
        'origin': BASE_URL,
        'referer': COURSE_SELECTION_URL,
        'authority': 'aa.bjtu.edu.cn',
        'x-requested-with': 'XMLHttpRequest',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    if cookie:
        session = requests.Session()
        session.headers.update({'Cookie': cookie})
    session.headers.update(BASE_HEADERS)
    try:
        response = session.get(CAPTCHA_REFRESH_URL)
        key = response.json()['key']
        captcha_img_url = f"{BASE_URL}/captcha/image/{key}"
        response = session.get(captcha_img_url)
        img = response.content
        result = base64_api(img=img, typeid=16)
        b64 = "data:image/png;base64," + base64.b64encode(img).decode()
        if (result['success']):
            result = result["data"]["result"]
            yield {"command": "captcha-image", "image": b64, "result": result}
        else:
            raise Exception("图鉴: " + result["message"])
        payload = f"checkboxs={checkbox}&hashkey={key}&answer={parse.quote(result)}"
        session.headers.update({
            'content-type': 'application/x-www-form-urlencoded',
        })
        response = session.post(COURSE_ACTION_URL, data=payload, allow_redirects=False)
        time.sleep(0.1)

        session.headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'cache-control': 'max-age=0',
        })

        response = session.get(COURSE_SELECTION_URL)
    except requests.exceptions.RequestException as e:
        yield {"command": "抢课", "error": f"Request failed: {e}"}
        return None

    text = response.text
    messages = re.findall(MESSAGE_PATTERN, text)
    yield {"command": "抢课", "std": messages[0]}


def get_all(session, cookie=None):
    # url = f"https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?kch=&kxh=&gname2020=&action=load&order=&iframe=school&submit=&has_advance_query=&page=1&perpage=500"
    url = "https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects/"
    if cookie:
        headers = {
            'authority': 'aa.bjtu.edu.cn',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'max-age=0',
            'cookie': cookie,
            'referer': 'https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?kch=108009B+%E7%94%9F%E6%B4%BB%E4%B8%AD%E7%9A%84%E7%94%9F%E7%89%A9%E5%AD%A6+01+%E7%89%A9%E5%B7%A5%E5%AD%A6%E9%99%A2%09&kxh=&gname2020=&action=load&order=&iframe=school&submit=&has_advance_query=',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
    else:
        response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        return -1
    table = tables[1]

    data = []
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if not cols:
            continue

        if cols[0].input:
            cols[0] = cols[0].input['value']
        cols = [ele.text.strip().replace("\n", "").replace(" ", "").replace("\r", "") if isinstance(ele, Tag) else ele.strip().replace("\n", "").replace(" ", "").replace("\r", "") for ele in cols]
        # print(cols)
        for i in course_list:
            if i.replace(" ", "") == "":
                continue
            if "高级" not in i and senior_check and "高级" in cols[course_name_col_num]:
                continue
            if i.replace(" ", "") in cols[course_name_col_num]:
                data.append(cols)
    return data

def fetch_and_handle_data(session, cookie=None):
    global course_list
    data = get_all(session, cookie)
    if data == -1:
        yield {"command": "选课", "error": "数据未成功获取..."}

    else:
        yield {"command": "选课", "std": "%s, %s\n待选课程：%s"%(user_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), ", ".join(course_list))}

    time.sleep(1)

    std_str = ""
    if data == []:
        course_list = []
        yield {"command": "选课", "error": "找不到待选课程..."}
        return
    finished_course = ""
    for i in data:
        if i[0] == "已选":
            finished_course += i[course_name_col_num] + ", "
            for j in course_list:
                if j.replace(" ", "") == "":
                    continue
                if j.replace(" ", "") in i[course_name_col_num]:
                    course_list.remove(j)
        else:
            std_str += f"{i[0]}, {i[course_name_col_num]}, {i[course_teacher_col_num]}, {i[course_num_col_num]}\n"
    yield {"command": "选课", "std": "已选课程：%s"%finished_course}
    yield {"command": "选课", "std": std_str}

    for i in data:
        if int(i[course_num_col_num]) > 0 and i[0].isdigit():
            yield {"command": "抢课", "std": f"正在抢课，{i[course_name_col_num]}, {i[course_teacher_col_num]}, {i[course_num_col_num]}"}
            yield from submit(session, i[0], cookie)



if __name__ == "__main__":
    global tujian_uname, tujian_pwd, course_list, senior_check, user_id, user_password\

    input_data = json.loads(sys.argv[1])
    print(json.dumps(input_data))
    sys.stdout.flush()
    tujian_uname = input_data['apiUsername']
    tujian_pwd = input_data['apiPassword']
    course_list = input_data['courseList'].split(",")
    senior_check = input_data['seniorCheck']
    user_id = input_data['username']
    user_password = input_data['password']

    for message in get_cookie(user_id, user_password):
        if isinstance(message, requests.sessions.Session):
            session = message
        else:
            print(json.dumps(message))
            sys.stdout.flush()
    while True:
        if course_list == []:
            print(json.dumps({"command": "抢课", "std": "抢课完成"}))
            sys.exit()
        for message in fetch_and_handle_data(session):
            print(json.dumps(message))
            sys.stdout.flush()
        # sys.exit()
