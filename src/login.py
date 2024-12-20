import asyncio
import base64
import json
import os
import re
import signal
import sys
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Generator, List, Union
from urllib import parse

import ddddocr
import requests
import websockets
from bs4 import BeautifulSoup


def base64_api(img, typeid, tujian_uname, tujian_pwd):
    base64_data = base64.b64encode(img)
    b64 = base64_data.decode()
    data = {
        "username": tujian_uname,
        "password": tujian_pwd,
        "typeid": typeid,
        "image": b64,
    }
    result = json.loads(requests.post("http://api.ttshitu.com/predict", json=data).text)
    return result


@dataclass
class CourseConfig:
    """课程配置数据类"""

    api_username: str
    api_password: str
    senior_check: bool
    course_list: List[str]
    username: str
    password: str
    model_path: str
    charset_path: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CourseConfig":
        # 验证必需字段
        for key in [
            "apiUsername",
            "apiPassword",
            "courseList",
            "seniorCheck",
            "username",
            "password",
        ]:
            if key not in data:
                raise ValueError(f"数据中缺少{key}字段")

        return cls(
            api_username=data["apiUsername"],
            api_password=data["apiPassword"],
            course_list=[course.strip() for course in data["courseList"].split(",")],
            senior_check=data["seniorCheck"],
            username=data["username"],
            password=data["password"],
            model_path=data["modelPath"],
            charset_path=data["charsetPath"],
        )


class CourseGrabber:
    """抢课核心类"""

    BASE_HEADERS = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    def __init__(self, config: CourseConfig):
        self.config = config
        self.session: requests.Session = None
        self.running = True
        self.username = None
        self.ocr = ddddocr.DdddOcr(
            det=False,
            ocr=False,
            import_onnx_path=self.config.model_path,
            charsets_path=self.config.charset_path,
            show_ad=False,
        )
        self.cookie = None
        self.session = requests.Session()

    def login(self) -> Dict[str, str]:
        """登录获取会话"""
        try:
            for message in self.get_cookie():
                yield message
            yield {"command": "登录", "std": "登录成功"}
        except Exception as e:
            yield {"command": "error", "error": f"登录失败: {str(e)}"}
            return

    def get_cookie(
        self,
    ) -> Generator[Union[requests.Session, Dict[str, str]], None, None]:
        """获取登录Cookie"""
        try:
            self.session.headers.update(self.BASE_HEADERS)

            yield {"command": "登录", "std": "正在获取验证码..."}
            response = self._get_initial_page(self.session)

            login_info = self._extract_login_info(response.text)

            captcha_result = self._handle_captcha(
                self.session, login_info["captcha_id"]
            )
            yield captcha_result

            yield {"command": "登录", "std": "正在登录..."}
            response = self._do_login(
                self.session, login_info, captcha_result["result"]
            )

            yield {"command": "登录", "std": "正在获取用户信息..."}
            self._handle_redirects(self.session, response)

            self.username = self._get_username(self.session)
            yield {"command": "登录", "std": f"{self.username}, 登录成功!"}
            self.cookie = self.session.cookies.get_dict()
        except requests.exceptions.RequestException as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_no = exc_traceback.tb_lineno
            func_name = exc_traceback.tb_frame.f_code.co_name
            raise Exception(f"网络请求失败: {str(e), {line_no}, {func_name}}")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_no = exc_traceback.tb_lineno
            func_name = exc_traceback.tb_frame.f_code.co_name
            raise Exception(f"{str(e), {line_no}, {func_name}}")

    def _get_initial_page(self, session: requests.Session) -> requests.Response:
        """获取初始登录页面"""
        response = session.get(
            "https://mis.bjtu.edu.cn/auth/sso/?next=/", allow_redirects=False
        )
        url = response.headers.get("Location")
        response = session.get(url, allow_redirects=False)
        url = "https://cas.bjtu.edu.cn" + response.headers.get("Location")
        return session.get(url, allow_redirects=False)

    def _extract_login_info(self, text: str) -> Dict[str, str]:
        """提取登录所需信息"""
        soup = BeautifulSoup(text, "html.parser")
        captcha_img = soup.find("img", class_="captcha")
        captcha_id = captcha_img["src"].split("/")[-2]
        csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        csrfmiddlewaretoken = csrf_input["value"]

        next_input = soup.find("input", {"name": "next"})
        next_url = next_input["value"].replace("&amp;", "&")

        return {
            "captcha_id": captcha_id,
            "csrfmiddlewaretoken": csrfmiddlewaretoken,
            "next_url": next_url,
        }

    def _handle_captcha(
        self, session: requests.Session, captcha_id: str
    ) -> Dict[str, str]:
        """处理验证码"""
        captcha_img_url = f"https://cas.bjtu.edu.cn/image/{captcha_id}"
        captcha_img = session.get(captcha_img_url).content
        expression = self.ocr.classification(captcha_img)
        try:
            expression = self.ocr.classification(captcha_img)

            expression = (
                expression.replace("x", "*")  # 将乘号x转换为*
                .replace("×", "*")  # 处理全角乘号
                .replace("=", "")  # 移除等号
                .strip()  # 移除空白
            )

            result = eval(expression, {"__builtins__": {}}, {})

            # 确保结果为整数
            if isinstance(result, float):
                result = int(result)

            return {
                "command": "captcha-image",
                "image": "data:image/png;base64,"
                + base64.b64encode(captcha_img).decode(),
                "result": result,
            }
        except Exception as e:
            raise Exception(f"验证码计算失败: {str(e)}")

    def _do_login(
        self, session: requests.Session, login_info: Dict[str, str], captcha_result: str
    ) -> requests.Response:
        """执行登录请求"""
        url = f"https://cas.bjtu.edu.cn/auth/login/?next={login_info['next_url']}"
        payload = {
            "next": login_info["next_url"],
            "csrfmiddlewaretoken": login_info["csrfmiddlewaretoken"],
            "loginname": self.config.username,
            "password": self.config.password,
            "captcha_0": login_info["captcha_id"],
            "captcha_1": captcha_result,
        }

        session.headers.update(
            {
                "authority": "cas.bjtu.edu.cn",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://cas.bjtu.edu.cn",
                "referer": f"https://cas.bjtu.edu.cn/auth/login/?next={parse.quote(login_info['next_url'])}",
            }
        )

        return session.post(url, data=payload, allow_redirects=False)

    def _handle_redirects(self, session: requests.Session, response: requests.Response):
        """处理登录后的重定向"""
        url = "https://cas.bjtu.edu.cn" + response.headers.get("Location")
        response = session.get(url, allow_redirects=False)

        session.headers.update({"authority": "mis.bjtu.edu.cn"})
        url = response.headers.get("Location")
        session.get(url, allow_redirects=False)

        response = session.get("https://mis.bjtu.edu.cn/module/module/10/")
        url = re.findall(r"<form action=\"(.*?)\"", response.text)[0]

        session.headers.update(
            {
                "authority": "aa.bjtu.edu.cn",
                "referer": "https://mis.bjtu.edu.cn/",
            }
        )
        session.get(url, allow_redirects=False)

    def _get_username(self, session: requests.Session) -> str:
        """获取用户名"""
        url = "https://aa.bjtu.edu.cn/schoolcensus/schoolcensus/stucensuscard/"
        session.headers.update(
            {
                "authority": "aa.bjtu.edu.cn",
                "referer": "https://aa.bjtu.edu.cn/notice/item/",
            }
        )
        response = session.get(url)
        return re.findall("<small>欢迎您，</small>(.*)\n", response.text)[0]

    async def grab_course(self) -> Dict[str, str]:
        try:
            try:
                async for message in self.fetch_and_handle_data():
                    if not self.running:
                        yield {"command": "stopped", "std": "抢课已停止"}
                        return
                    yield message
            except Exception as e:
                yield {"command": "error", "std": f"单次抢课失败: {str(e)}"}

        except Exception as e:
            yield {"command": "error", "std": f"抢课过程发生错误: {str(e)}"}
            return

    async def submit_course(self, course_id: str):
        """提交选课请求"""
        BASE_HEADERS = {
            "accept": "*/*",
            "origin": "https://aa.bjtu.edu.cn",
            "referer": "https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects/",
            "authority": "aa.bjtu.edu.cn",
            "x-requested-with": "XMLHttpRequest",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        }
        self.session.headers.update(BASE_HEADERS)
        try:
            response = await asyncio.to_thread(
                self.session.get, "https://aa.bjtu.edu.cn/captcha/refresh/"
            )
            key = response.json()["key"]
            captcha_img_url = f"https://aa.bjtu.edu.cn/captcha/image/{key}"
            response = await asyncio.to_thread(self.session.get, captcha_img_url)
            img = response.content
            result = base64_api(
                img, 16, self.config.api_username, self.config.api_password
            )
            b64 = "data:image/png;base64," + base64.b64encode(img).decode()
            if result["success"]:
                result = result["data"]["result"]
                yield {"command": "captcha-image", "image": b64, "result": result}
            else:
                raise Exception("图鉴: " + result["message"])
            payload = (
                f"checkboxs={course_id}&hashkey={key}&answer={parse.quote(result)}"
            )
            self.session.headers.update(
                {
                    "content-type": "application/x-www-form-urlencoded",
                }
            )
            response = await asyncio.to_thread(
                self.session.post,
                "https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?action=submit",
                data=payload,
                allow_redirects=False,
            )
            await asyncio.sleep(0.1)

            self.session.headers.update(
                {
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "cache-control": "max-age=0",
                }
            )

            response = await asyncio.to_thread(
                self.session.get,
                "https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects/",
            )
        except requests.exceptions.RequestException as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_no = exc_traceback.tb_lineno
            func_name = exc_traceback.tb_frame.f_code.co_name
            raise Exception(f"{str(e), {line_no}, {func_name}}")

        text = response.text
        messages = re.findall(r'message \+= "(.*)<br/>";', text)
        if messages:
            yield {"command": "抢课", "std": messages[0]}

    async def fetch_and_handle_data(self) -> Generator[Dict[str, Any], None, None]:
        """获取并处理课程数据"""
        try:
            # 获取所有课程数据
            courses = self.get_available_courses()
            if not courses:
                yield {"command": "选课", "error": "数据未成功获取..."}
                return

            # 生成状态信息
            yield {
                "command": "选课",
                "std": f"{self.username}, {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"待选课程：{', '.join(self.config.course_list)}",
            }

            # 处理已选课程
            finished_courses = []
            available_courses = []

            for course in courses:
                if course["id"] == "已选":
                    finished_courses.append(re.sub(r"\s+", " ", course["name"].strip()))
                else:
                    available_courses.append(course)

            if len(available_courses) == 0:
                yield {"command": "success", "std": "抢课完成"}
                return

            # 输出已选课程
            if finished_courses:
                yield {
                    "command": "选课",
                    "std": f"已选课程：{', '.join(finished_courses)}",
                }

            # 输出可选课程信息
            course_info = ""
            for course in available_courses:
                course_name = re.sub(r"\s+", " ", course["name"].strip())
                course_info += (
                    f"{course['id']}, {course_name}, "
                    f"{course['teacher']}, {course['number']}\n"
                )
            if course_info:
                yield {"command": "选课", "std": course_info}

            # 尝试选课
            for course in available_courses:
                if int(course["number"]) > 0:
                    course_name = re.sub(r"\s+", " ", course["name"].strip())
                    yield {
                        "command": "抢课",
                        "std": f"正在抢课，{course_name}, "
                        f"{course['teacher']}, {course['number']}",
                    }

                    # 提交选课
                    async for result in self.submit_course(course["id"]):
                        yield result

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_no = exc_traceback.tb_lineno
            func_name = exc_traceback.tb_frame.f_code.co_name
            raise Exception(f"{str(e), {line_no}, {func_name}}")

    def get_available_courses(self) -> List[Dict[str, str]]:
        """获取可选课程列表"""
        try:
            response = self.session.get(
                "https://aa.bjtu.edu.cn/course_selection/courseselecttask/selects/"
            )
            soup = BeautifulSoup(response.text, "html.parser")

            tables = soup.find_all("table")
            if not tables or len(tables) < 2:
                return []

            courses = []
            for row in tables[1].find_all("tr"):
                cols = row.find_all("td")
                if not cols:
                    continue

                checkbox = cols[0].find("input")
                if not checkbox:
                    checkbox = cols[0].text.strip()
                else:
                    checkbox = checkbox["value"]
                course = {
                    "id": checkbox,
                    "name": cols[1].text.strip().replace("\n", " "),
                    "number": cols[2].text.strip(),
                    "teacher": cols[6].text.strip(),
                }

                # 检查是否符合选课条件
                if self._check_course_valid(course):
                    courses.append(course)

            return courses

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_no = exc_traceback.tb_lineno
            func_name = exc_traceback.tb_frame.f_code.co_name
            raise Exception(f"{str(e), {line_no}, {func_name}}")

    def _check_course_valid(self, course: Dict[str, str]) -> bool:
        """检查课程是否符合选课条件"""
        flag = False
        for key in self.config.course_list:
            if key in course["name"]:
                flag = True

            if (
                (not self.config.senior_check)
                and ("高级" in course["name"])
                and ("高级" not in key)
            ):
                return False

        if not flag:
            return False

        return True

    def stop(self):
        """停止抢课"""
        self.running = False


class WebSocketServer:
    """WebSocket服务器类"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.grabbers: Dict[str, CourseGrabber] = {}
        self.grab_course_tasks: Dict[str, asyncio.Task] = {}

    async def stop(self):
        """停止服务器"""
        if self.server:
            self.is_running = False
            self.server.close()
            await self.server.wait_closed()
            print("\n服务器已安全关闭")

    async def handle_connection(self, websocket):
        """处理WebSocket连接"""
        client_id = str(id(websocket))

        try:
            async for message in websocket:
                input_data = json.loads(message)
                if input_data.get("command") == "stop":
                    if client_id in self.grabbers:
                        self.grabbers[client_id].stop()
                    await websocket.send(
                        json.dumps({"command": "finished", "std": "任务已停止"})
                    )
                else:
                    if client_id in self.grab_course_tasks:
                        self.grab_course_tasks[client_id].cancel()
                    self.grab_course_tasks[client_id] = asyncio.create_task(
                        self.process_message(websocket, client_id, input_data)
                    )

        except Exception as e:
            print(f"WebSocket错误: {str(e)}")
        finally:
            if client_id in self.grabbers:
                self.grabbers[client_id].stop()
                del self.grabbers[client_id]
            if client_id in self.grab_course_tasks:
                self.grab_course_tasks[client_id].cancel()
                del self.grab_course_tasks[client_id]

    async def process_message(self, websocket, client_id, input_data):
        config = CourseConfig.from_dict(input_data)
        grabber = CourseGrabber(config)
        self.grabbers[client_id] = grabber
        grabber.running = True

        login_result = grabber.login()
        for result in login_result:
            await websocket.send(json.dumps(result))
        while grabber.running and not websocket.closed:
            async for result in grabber.grab_course():
                await websocket.send(json.dumps(result))
                if result["command"] in ["success", "error", "stopped"]:
                    await websocket.send(
                        json.dumps({"command": "finished", "std": "任务结束"})
                    )
                    return
            await asyncio.sleep(2)

        await websocket.send(json.dumps({"command": "success", "std": "任务结束"}))


class GracefulExit(SystemExit):
    code = 0


def raise_graceful_exit(*args):
    loop.stop()
    print("Gracefully shutdown")
    raise GracefulExit()


if __name__ == "__main__":
    print("WebSocket服务器启动中...")
    loop = asyncio.get_event_loop()
    signal.signal(signal.SIGINT, raise_graceful_exit)
    signal.signal(signal.SIGTERM, raise_graceful_exit)
    server = WebSocketServer()
    start_server = websockets.serve(server.handle_connection, server.host, server.port)
    print(f"当前PID: {os.getpid()}")
    try:
        loop.run_until_complete(start_server)
        loop.run_forever()
    except GracefulExit:
        pass
    finally:
        loop.close()
