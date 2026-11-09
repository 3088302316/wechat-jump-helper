# 微信跳一跳辅助

配合电脑版微信《跳一跳》使用的 Windows 桌面工具。用鼠标指出棋子和目标位置，工具按两点距离计算长按时长。

**[下载 Windows 安装程序](https://github.com/3088302316/wechat-jump-helper/releases/latest)** · Windows 10 22H2 x64 / Windows 11 x64

## 安装与使用

下载并双击 `wechat-jump-helper-setup-x64.exe`。安装时可以选择目录和桌面快捷方式，之后也能从开始菜单打开。安装包已包含 Python 和 Tkinter。

1. 在电脑版微信里打开《跳一跳》，再启动辅助工具。
2. 鼠标指向棋子底部，按 **空格** 记录起点。
3. 鼠标指向下一块平台的顶面中心，再按 **空格** 记录目标。
4. 第三次按 **空格** 执行长按。想重新选点时按 **Backspace** 退回一步。

如果经常跳短或跳过头，可在侧边面板微调按压系数。

## 从源码运行和打包

源码使用 Python 标准库、Tkinter 和 Windows API。装有带 Tkinter 的 Python 后可直接运行：

```powershell
python .\wechat_jump_space_backspace.py
```

生成安装包使用 Python 3.13 x64、PyInstaller 6.16.0 和 Inno Setup 6.7.4：

```powershell
python -m pip install PyInstaller==6.16.0
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-installer.ps1 -IsccPath "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

输出在 `发布/`。可用 `-PythonExe` 指定构建用 Python，用 `-LanguageFile` 指定安装器语言文件。
