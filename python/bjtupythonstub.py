# coding=utf-8

import asyncio
import base64
import importlib.util
import io
import json
import os
import re
import runpy
import signal
import sys
import time
import warnings
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Union
from urllib import parse

import onnxruntime
import requests
import websockets
from bs4 import BeautifulSoup
from numpy import array, expand_dims, float32
from PIL import Image


class GracefulExit(SystemExit):
    code = 0


loop = asyncio.get_event_loop()


def raise_graceful_exit(*args):
    loop.stop()
    print("Gracefully shutdown")
    raise GracefulExit()


def main():
    signal.signal(signal.SIGINT, raise_graceful_exit)
    signal.signal(signal.SIGTERM, raise_graceful_exit)

    if len(sys.argv) != 2:
        print("Usage: stub.exe <python script>")
        sys.exit(1)

    script_path = sys.argv[1]

    try:
        abs_path = os.path.abspath(script_path)

        spec = importlib.util.spec_from_file_location("dynamic_module", abs_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        WebSocketServer = getattr(module, "WebSocketServer")
    except Exception as e:
        print(f"加载脚本失败: {str(e)}")
        sys.exit(1)

    server = WebSocketServer()
    start_server = websockets.serve(server.handle_connection, server.host, server.port)
    print("WebSocket Starting...")
    print(f"Current PID: {os.getpid()}")

    try:
        loop.run_until_complete(start_server)
        loop.run_forever()
    except GracefulExit:
        pass
    finally:
        loop.close()
    print("WebSocket Closed")


if __name__ == "__main__":
    main()
