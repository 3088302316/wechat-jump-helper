# 微信跳一跳辅助工具

配合电脑版微信《跳一跳》使用的 Windows 桌面辅助脚本。用鼠标手动选择棋子和目标，工具根据两点距离和面板中的系数换算成长按时间。

## 运行

在 Windows 10 或 11 上使用带 Tkinter 的 Python 3.9 或更高版本。用电脑版微信打开《跳一跳》游戏窗口，然后在本目录运行：

```powershell
python .\wechat_jump_space_backspace.py
```

1. 鼠标指向棋子底部，按空格记录起点。
2. 鼠标指向下一块平台顶面中心，再按空格记录目标。
3. 第三次按空格执行长按。Backspace 可退回上一步。

使用侧边窗口微调按压系数。项目依赖 Python 标准库和 Windows API。

本机也可双击项目里的「启动跳一跳.cmd」，或使用桌面和开始菜单入口。

## Windows 安装包

双击 `发布\微信跳一跳辅助-安装程序-Windows-x64.exe`，选择目录，安装后通过桌面或开始菜单启动。安装包已包含 Python 和 Tkinter。打开电脑版微信里的游戏窗口后使用本工具。

维护者可用 64 位 Python 3.13（带 Tkinter）、PyInstaller 6.16.0 和 Inno Setup 6.7.4 构建：

```powershell
python -m pip install PyInstaller==6.16.0
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-installer.ps1 -IsccPath "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

可通过 `-PythonExe` 指定构建用 Python，通过 `-LanguageFile` 指定安装器语言文件。
