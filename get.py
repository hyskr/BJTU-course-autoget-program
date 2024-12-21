import base64
import json
import re
import time
from urllib import parse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

user_id = "" # 学号
user_password = "" # mis密码

course_list = ["网球07", ""] #课程全名 或 课程代码，若不添加数字则默认抢课程所有
senior_check = True # 是否不抢高级课程, 默认为True, 如要指定高级课程, 请在course_list中添加高级课程

# wx_pusher https://wxpusher.zjiecode.com/

# notification_uid_list = ["UID_****************************", "UID_****************************"] # 通知用户的UID
notification_uid_list = [] # 通知用户的UID, 如不需要， 请留空 
# notification_APPTOKEN = "AT_********************************"
notification_APPTOKEN = "" # 通知用户的APPTOKEN, 如不需要， 请留空

# 图鉴 API http://www.ttshitu.com/ 我的推荐码:761d71be5b21457aa72acf037510155c
tujian_uname = ""
tujian_pwd = ""


# 失败重复次数
RETRY_LIMIT = 5


user_name = "" #无需填写，自动获取

if not user_id or not user_password or not tujian_uname or not tujian_pwd or not course_list:
    print("请填写完整信息!")
    exit()

def base64_api(img, typeid):
    base64_data = base64.b64encode(img)
    b64 = base64_data.decode()
    data = {"username": tujian_uname, "password": tujian_pwd, "typeid": typeid, "image": b64}
    result = json.loads(requests.post(
        "http://api.ttshitu.com/predict", json=data).text)
    return result

def send(content, uid):
    if not uid or not notification_APPTOKEN:
        return
    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = json.dumps({
        "appToken": notification_APPTOKEN,
        "content": user_name + content,
        "contentType": 1,
        "uids": uid
    })
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        requests.request("POST", url, headers=headers, data=payload)
    except requests.exceptions.RequestException as e:
        print(f'Send Requeset failed: {e}')


def get_cookie(username, password):
    BASE_HEADERS = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    try:
        pbar = tqdm(total=8, desc="Logging in", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
        session = requests.Session()
        session.headers.update(BASE_HEADERS)

        # get captcha
        url = "https://mis.bjtu.edu.cn/auth/sso/?next=/"
        response = session.get(url, allow_redirects=False)
        url = response.headers.get('Location')
        response = session.get(url, allow_redirects=False)
        url = "https://cas.bjtu.edu.cn" + response.headers.get('Location')
        response = session.get(url, allow_redirects=False)
        pbar.update(1)
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
             captcha_result = captcha_result["data"]["result"]
        else:
            raise Exception("图鉴: " + captcha_result["message"])
        pbar.update(1)
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
        pbar.update(1)
        time.sleep(1)

        # Follow redirects
        url = "https://cas.bjtu.edu.cn" + response.headers.get('Location')
        response = session.get(url, allow_redirects=False)
        pbar.update(1)
        time.sleep(1)
        
        session.headers.update({
            'authority': 'mis.bjtu.edu.cn',
        })
        url = response.headers.get('Location')
        response = session.get(url, allow_redirects=False)
        pbar.update(1)
        time.sleep(1)
        
        url = "https://mis.bjtu.edu.cn/module/module/10/"
        response = session.get(url)
        pbar.update(1)
        time.sleep(1)
        
        text = response.text
        url = re.findall(r"<form action=\"(.*?)\"", text)[0]
        session.headers.update({
            'authority': 'aa.bjtu.edu.cn',
            'referer': 'https://mis.bjtu.edu.cn/',
        })
        response = session.get(url, allow_redirects=False)
        pbar.update(1)
        time.sleep(1)
        

        url = "https://aa.bjtu.edu.cn/schoolcensus/schoolcensus/stucensuscard/"
        session.headers.update({
            'authority': 'aa.bjtu.edu.cn',
            'referer': 'https://aa.bjtu.edu.cn/notice/item/',
        })
        response = session.get(url)
        pbar.update(1)
        time.sleep(1)
        
        userid = re.findall("<small>欢迎您，</small>(.*)\n", response.text)[0]
        pbar.close()
        print(userid, " 登陆成功!!!")
        cookie = ""
        for _cookie in session.cookies.get_dict():
            cookie += _cookie + "=" + session.cookies.get_dict()[_cookie] + "; "
        return cookie
    except requests.exceptions.RequestException as e:
        pbar.close()
        print(f"There was an issue with the network: {e}")
        return None
    except Exception as e:
        pbar.close()
        print(f"An error occurred: {e}, might be due to incorrect username or password.")
        print("Please check your username and password and try again. 5s后将自动退出! ")
        time.sleep(5)
        exit()
        return None




BASE_URL = "https://aa.bjtu.edu.cn"
CAPTCHA_REFRESH_URL = f"{BASE_URL}/captcha/refresh/"
COURSE_SELECTION_URL = f"{BASE_URL}/course_selection/courseselecttask/selects/"
COURSE_ACTION_URL = f"{BASE_URL}/course_selection/courseselecttask/selects_action/?action=submit"
MESSAGE_PATTERN = r'message \+= "(.*)<br/>";'



def submit(cookie, checkbox):
    BASE_HEADERS = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    with requests.Session() as session:
        session.headers.update(BASE_HEADERS)
        session.headers.update({'cookie': cookie})
        try:
            response = session.get(CAPTCHA_REFRESH_URL)
            key = response.json()['key']
            captcha_img_url = f"{BASE_URL}/captcha/image/{key}"
            response = session.get(captcha_img_url)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

        img = response.content
        result = base64_api(img=img, typeid=16)
        payload = f"checkboxs={checkbox}&hashkey={key}&answer={parse.quote(result)}"
        
        session.headers.update({
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': BASE_URL,
            'referer': COURSE_SELECTION_URL,
            'x-requested-with': 'XMLHttpRequest'
        })
        
        try:
            response = session.post(COURSE_ACTION_URL, data=payload)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

        time.sleep(0.1)
        messages = response.cookies.get_dict().get('messages', '')
        
        session.headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'cache-control': 'max-age=0',
            'cookie': session.headers['cookie'] + "messages=" + messages,
        })
        
        try:
            response = session.get(COURSE_SELECTION_URL)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

        text = response.text
        messages = re.findall(MESSAGE_PATTERN, text)

    return messages

def get_all(cookie):
    url = f"https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?kch=&kxh=&gname2020=&action=load&order=&iframe=school&submit=&has_advance_query=&page=1&perpage=500"

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
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        return -1

    data = []
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if not cols:
            continue
        
        if cols[0].input:
            cols[0] = cols[0].input['value']
        cols = [ele.text.strip().replace("\n", "").replace(" ", "") for ele in cols]
        
        for i in course_list:
            if i.replace(" ", "") == "":
                continue
            if "高级" not in i and senior_check and "高级" in cols[2]:
                continue
            if i.replace(" ", "") in cols[2]:
                data.append(cols)

    return data





def fetch_and_handle_data(cookie, retry_count=0):
    data = get_all(cookie)

    if data == -1:  # 数据获取失败
        print("数据未成功获取...")
        retry_count += 1

        if retry_count >= RETRY_LIMIT:
            print("---get_cookie...")
            send("cookie重新获取", ["UID_EM6DPDJpqmywihJDbzRTmeCPQrMr"])
            cookie = get_cookie(user_id, user_password)
            retry_count = 0  # 重置计数器

        # 延时后重试
        time.sleep(1)
        fetch_and_handle_data(cookie, retry_count)

    else:  # 数据获取成功，进行处理
        print(user_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        for i in data:
            print(f"{i[2]}, {i[6]}, {i[3]}")
            if int(i[3]) > 0 and i[0].isdigit():
                print("正在抢课........................")
                send(f"正在抢课，{i[2]}, {i[6]}, {i[3]}", notification_uid_list)
                t = submit(cookie, i[0])
                print("抢课成功", t)
                send(f"抢课成功，{t}", notification_uid_list)

        print("--------------------------------------------------------------------")

# 主程序
count = 0
cookie = get_cookie(user_id, user_password)

while True:
    fetch_and_handle_data(cookie)
