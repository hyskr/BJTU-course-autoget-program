const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const spawn = require("child_process").spawn;
const execFile = require("child_process").execFile;
const storage = require('electron-json-storage');
var kill = require('tree-kill');

let mainWindow;
let exePath = path.join(__dirname, "./src/login.exe"); // 使用 path.join 构建正确的路径
let modelPath = path.join(__dirname, "./src/omis.onnx");
let charsetPath = path.join(__dirname, "./src/charsets.json");

let ws = null; // 全局 WebSocket 对象
let pythonProcess = null; // 全局 Python 进程对象
let wsStatus = false; // WebSocket 状态
let messageHandler = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1680,
    height: 1080,
    icon: path.join(__dirname, "src/icon.ico"), // 设置图标的路径
    webPreferences: {
      contextIsolation: true, // 启用上下文隔离
      nodeIntegration: false, // 禁用直接访问 Node.js API
      preload: path.join(__dirname, "preload.js"),
    },
  });

  // mainWindow.webContents.openDevTools();
  console.log('exePath:', exePath);

  exePath = exePath.replace('app.asar', 'app.asar.unpacked');
  modelPath = modelPath.replace('app.asar', 'app.asar.unpacked');
  charsetPath = charsetPath.replace('app.asar', 'app.asar.unpacked');

  if (fs.existsSync(exePath) && fs.existsSync(modelPath) && fs.existsSync(charsetPath)) {
    console.log('login.exe 文件存在');
  } else {
    dialog.showErrorBox('错误', `${exePath}, login.exe 文件不存在`);
    app.quit();
  }

  mainWindow.loadFile("index.html");

  mainWindow.on("closed", function () {
    if (ws) {
      ws.close();
    }
    if (pythonProcess) {
      kill(pythonProcess.pid, 'SIGTERM', function (err) {
        if (err) {
          console.log('kill error:', err);
        }
      });
    }
    mainWindow = null;
  });
}

app.on("ready", createWindow);

app.on("window-all-closed", function () {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", function () {
  if (mainWindow === null) createWindow();
});

function waitForServerReady(onReady, onRetry) {
  return new Promise((resolve, reject) => {
    let retries = 0;
    const maxRetries = 5;
    const interval = setInterval(() => {
      retries++;
      if (retries >= maxRetries) {
        clearInterval(interval);
        reject(new Error("WebSocket 服务启动超时"));
      }
      const tempWs = new WebSocket("ws://localhost:8765");
      tempWs.on("open", function () {
        ws = tempWs;
        wsStatus = true;
        onReady();
        clearInterval(interval);
        resolve();
      })
      tempWs.on("error", function () {
        wsStatus = false;
        onRetry();
      });
    }, 1000);
  });
}

ipcMain.handle("get-ws-status", () => { return wsStatus; })

ipcMain.handle("start-server", async (event) => {
  if (pythonProcess == null) {
    pythonProcess = spawn(exePath);

    console.log(pythonProcess.pid)
    pythonProcess.stdout.on("data", (data) => {
      console.log(`Python stdout: ${data}`);
    });
    pythonProcess.on('exit', (code) => {
      console.log(`Python进程退出，退出码: ${code}`);
      pythonProcess = null;
    });
    pythonProcess.on("error", (err) => {
      console.error("Failed to start Python process:", err);
      pythonProcess = null;
      event.sender.send("server-response", { command: "初始化", error: `无法启动 Python 脚本: ${err.message}` });
      return false;
    });
  }
  console.log("脚本服务已就绪");
  event.sender.send("server-response", { command: "初始化", std: "脚本服务已就绪" });

  try {
    await waitForServerReady(
      () => {
        event.sender.send("server-response", {
          command: "初始化",
          std: "WebSocket 服务已就绪",
        });
      },
      () => {
        console.log("WebSocket 服务未就绪，1秒后重试...");
      }
    );
    return true;
  } catch (err) {
    event.sender.send("server-response", {
      command: "初始化",
      error: ("等待 WebSocket 服务启动时发生错误:" + err),
    });
    return false;
  }
});

ipcMain.handle("stop-server", () => {
  if (ws) {
    ws.close();
  }
  if (pythonProcess) {
    kill(pythonProcess.pid, 'SIGTERM', function (err) {
      if (err) {
        console.log('kill error:', err);
      }
    });
    pythonProcess = null;
  }
  return false;
});

ipcMain.on('open-link-externally', (event, url) => {
  console.log('open-link-externally', url);
  shell.openExternal(url);
});

ipcMain.handle('readConfig', () => {
  return new Promise((resolve, reject) => {
    storage.get('UserInfo', (error, data) => {
      if (error) {
        reject(error);
      } else {
        resolve(data);
      }
    });
  });
});
ipcMain.handle('saveConfig', (event, data) => {
  storage.set('UserInfo', data);
});

ipcMain.on("login-request", (event, data) => {
  data.command = "login1";
  data.modelPath = modelPath;
  data.charsetPath = charsetPath;
  if (messageHandler) {
    ws.removeListener('message', messageHandler);
  }

  messageHandler = (data) => {
    // console.log(`Python response: ${data}`);
    event.sender.send('login-response', JSON.parse(data.toString().trim()));
  };

  ws.send(JSON.stringify(data));
  ws.on('message', messageHandler);
});

ipcMain.handle("stop-request", (event) => {
  ws.send(JSON.stringify({ command: "stop" }));
});