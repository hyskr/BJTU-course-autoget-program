const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const fs = require('fs');
const path = require('path');
const spawn = require('child_process').spawn;

let mainWindow;
let exePath = path.join(__dirname, './src/login.exe'); // 使用 path.join 构建正确的路径
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1920,
    height: 1080,
    icon: path.join(__dirname, 'src/icon.ico'), // 设置图标的路径
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // mainWindow.webContents.openDevTools()
  console.log('exePath:', exePath);
  exePath = exePath.replace('app.asar', 'app.asar.unpacked');
  if (fs.existsSync(exePath)) {
    console.log('login.exe 文件存在');
  } else {
    dialog.showErrorBox('错误', `${exePath}, login.exe 文件不存在`);
    app.quit();
  }
  mainWindow.loadFile('index.html');

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

app.on('ready', createWindow);

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', function () {
  if (mainWindow === null) createWindow();
});

let pythonProcess = null;

ipcMain.on('login-request', (event, data) => {
  if (pythonProcess !== null) {
    console.log('Python process already started');
    return;
  }

  // pythonProcess = spawn('python', ['login.py', JSON.stringify(data)]);
  pythonProcess = spawn(exePath, [JSON.stringify(data)]);
  // pythonProcess.stdout.on('data', (data) => {
  //   console.log(`Python response: ${data}`);
  //   event.sender.send('login-response', JSON.parse(data.toString()));
  // });

  pythonProcess.stdout.on('data', (data) => {
    let accumulatedData = '';
    accumulatedData += data.toString();

    let bracketCount = 0;
    let jsonStart = 0;

    for (let i = 0; i < accumulatedData.length; i++) {
      if (accumulatedData[i] === '{') {
        bracketCount++;
        if (bracketCount === 1) {
          // 标记 JSON 对象的开始位置
          jsonStart = i;
        }
      } else if (accumulatedData[i] === '}') {
        bracketCount--;
        if (bracketCount === 0) {
          // 找到了完整的 JSON 对象
          let jsonStr = accumulatedData.substring(jsonStart, i + 1);
          try {
            let jsonObject = JSON.parse(jsonStr);
            console.log(`Python response: ${JSON.stringify(jsonObject)}`);
            event.sender.send('login-response', jsonObject);
            // 清除已解析的数据
            accumulatedData = accumulatedData.substring(i + 1);
            i = -1; // 重置索引
          } catch (e) {
            console.error('JSON 解析失败:', e);
          }
        }
      }
    }
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python error: ${data}`);
    event.sender.send('login-response', { command: "Python error", error: data.toString() });
  });

  pythonProcess.on('exit', (code) => {
    if (code !== 0) {
      event.sender.send('process-response', { command: "finished", error: `Python process exited with code ${code}` });
    } else {
      event.sender.send('process-response', { command: "finished", success: `Python process exited with code ${code}` });
    }
    console.log(`Python process exited with code ${code}`);
    pythonProcess = null;
  });
});

ipcMain.on('stop-request', (event) => {
  console.log('Received stop request from renderer process');

  if (pythonProcess) {
    pythonProcess.kill();
    event.sender.send('process-response', { command: "finished", success: 'Python process stopped' });
    console.log('Python process stopped');
    pythonProcess = null;
  }
});
