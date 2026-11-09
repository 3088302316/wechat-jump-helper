# -*- coding: utf-8 -*-
"""电脑版微信《跳一跳》手动选点辅助（Windows 10/11, Python 3.9+）

鼠标指向棋子底部按空格 -> 指向下一块平台顶面中心按空格 -> 再按空格执行长按。
Backspace 退回上一步（撤销目标或棋子），每次跳跃后自动重新从第一步开始。
侧边窗口微调按压力度，精度 0.001 ms/px；无第三方依赖。
"""

import ctypes
from ctypes import wintypes
import math
import os
import queue
import sys
import threading
import time
import tkinter as tk

if sys.platform != "win32":
    raise SystemExit("此程序仅支持 Windows 10/11。")

# 使鼠标坐标和游戏窗口坐标在 Windows 缩放 125%/150% 时保持一致。
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except (AttributeError, OSError):
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 参数声明：尤其要保证在 64 位 Python 下正确传递指针。
LONG_PTR = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LONG_PTR, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
ENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = (ENUMPROC, wintypes.LPARAM)
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = (wintypes.HWND,)
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindow.argtypes = (wintypes.HWND,)
user32.IsWindow.restype = wintypes.BOOL
user32.IsIconic.argtypes = (wintypes.HWND,)
user32.IsIconic.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
user32.ClientToScreen.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
user32.SetCursorPos.restype = wintypes.BOOL
user32.GetForegroundWindow.argtypes = ()
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
user32.SetWindowsHookExW.restype = wintypes.HANDLE
user32.CallNextHookEx.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.CallNextHookEx.restype = LONG_PTR
user32.UnhookWindowsHookEx.argtypes = (wintypes.HANDLE,)
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
user32.GetMessageW.restype = ctypes.c_int
user32.PeekMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT)
user32.PeekMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = (ctypes.POINTER(wintypes.MSG),)
user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)
user32.mouse_event.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t)
user32.mouse_event.restype = None
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
user32.PostThreadMessageW.restype = wintypes.BOOL

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012
PM_NOREMOVE = 0
VK_SPACE = 0x20
VK_BACK = 0x08
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


def window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value.strip()


def find_game_window():
    """仅匹配真实的“跳一跳”窗口，避免误绑辅助程序自身。"""
    found = []

    @ENUMPROC
    def enum_callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        title = window_title(hwnd)
        if "跳一跳" not in title or "辅助" in title or "力度" in title:
            return True
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        w, h = rect.right - rect.left, rect.bottom - rect.top
        if w < 200 or h < 300:
            return True
        # 以准确标题为最高优先级，避免绑定类似网页搜索结果标题。
        score = (100 if title == "跳一跳" else 0) + min(w * h, 1000000) / 1000000
        found.append((score, hwnd))
        return True

    user32.EnumWindows(enum_callback, 0)
    if not found:
        return None
    return max(found, key=lambda pair: pair[0])[1]


def client_box(hwnd):
    """返回屏幕物理像素系中的游戏客户区(left, top, width, height)。"""
    if not hwnd or not user32.IsWindow(hwnd) or user32.IsIconic(hwnd):
        return None
    rect = wintypes.RECT()
    pt = wintypes.POINT(0, 0)
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    if not user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        return None
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width < 100 or height < 100:
        return None
    return (pt.x, pt.y, width, height)


def cursor_xy():
    pt = wintypes.POINT()
    if user32.GetCursorPos(ctypes.byref(pt)):
        return pt.x, pt.y
    return None


def inside(box, pos):
    x, y, w, h = box
    return x <= pos[0] < x + w and y <= pos[1] < y + h


class KeyListener:
    """鼠标在游戏窗口内，或微信处于前台时，截获空格/退格键。"""

    def __init__(self, hwnd_getter, event_queue):
        self.hwnd_getter = hwnd_getter
        self.events = event_queue
        self.hook = None
        self.callback = None
        self.thread_id = None
        self.started = threading.Event()
        self.error = None
        self.down = set()
        self.thread = threading.Thread(target=self._run, name="wechat-jump-key-hook", daemon=True)

    def start(self):
        self.thread.start()
        self.started.wait(timeout=3)
        return self.hook is not None

    def _run(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)

        @HOOKPROC
        def callback(n_code, w_param, l_param):
            if n_code < 0:
                return user32.CallNextHookEx(None, n_code, w_param, l_param)
            try:
                info = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = int(info.vkCode)
                if vk not in (VK_SPACE, VK_BACK):
                    return user32.CallNextHookEx(None, n_code, w_param, l_param)
                if w_param in (WM_KEYUP, WM_SYSKEYUP):
                    if vk in self.down:
                        self.down.discard(vk)
                        return 1
                    return user32.CallNextHookEx(None, n_code, w_param, l_param)
                if w_param not in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    return user32.CallNextHookEx(None, n_code, w_param, l_param)
                if vk in self.down:
                    return 1  # 抑制长按键盘导致的重复触发

                hwnd = self.hwnd_getter()
                if not hwnd or not user32.IsWindow(hwnd) or user32.IsIconic(hwnd):
                    return user32.CallNextHookEx(None, n_code, w_param, l_param)
                box = client_box(hwnd)
                pos = cursor_xy()
                if not box or not pos:
                    return user32.CallNextHookEx(None, n_code, w_param, l_param)

                # 操作仅在游戏区域或微信窗口为前台时生效，
                # 避免影响其他应用里的空格/退格输入。
                pointer_on_game = inside(box, pos)
                accepted = pointer_on_game or user32.GetForegroundWindow() == hwnd
                if not accepted:
                    return user32.CallNextHookEx(None, n_code, w_param, l_param)
                self.down.add(vk)
                self.events.put(("key", vk, pos, hwnd))
                return 1
            except Exception as exc:
                self.events.put(("hook_error", str(exc)))
                return user32.CallNextHookEx(None, n_code, w_param, l_param)

        self.callback = callback  # 保持对回调的强引用
        self.hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self.callback, kernel32.GetModuleHandleW(None), 0
        )
        if not self.hook:
            self.error = "安装键盘监听失败，Windows 错误码：" + str(kernel32.GetLastError())
            self.started.set()
            return
        self.started.set()
        try:
            while True:
                r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if r <= 0:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnhookWindowsHookEx(self.hook)
            self.hook = None
            self.callback = None

    def stop(self):
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


class JumpPanel:
    MIN_FACTOR = 0.500
    MAX_FACTOR = 7.000
    # 局部力度滑块跨度为 0.300（±0.150），保证拖动一像素约 0.001。
    SLIDER_HALF_RANGE = 0.150

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("跳一跳 · 空格选点")
        self.root.geometry("355x353")
        self.root.resizable(False, False)
        self.root.configure(bg="#f7f9fc")
        self.root.attributes("-topmost", True)

        self.game_hwnd = None
        self.last_box = None
        self.piece = None
        self.target = None
        self.busy = False
        self.closing = False
        self.user_adjusted = False
        self.initial_positioned = False
        self.events = queue.Queue()
        self.factor = tk.DoubleVar(value=2.500)
        self.factor_input = tk.StringVar(value="2.500")
        self.game_text = tk.StringVar(value="正在寻找微信跳一跳窗口…")
        self.piece_text = tk.StringVar(value="第 1 步 · 棋子：未选择")
        self.target_text = tk.StringVar(value="第 2 步 · 目标：未选择")
        self.distance_text = tk.StringVar(value="距离：—       长按：—")
        self.status_text = tk.StringVar(value="将鼠标指向棋子底部，然后按空格")
        self._ignore_slider = False
        self.slider_center = 2.500

        self.make_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.listener = KeyListener(lambda: self.game_hwnd, self.events)
        if not self.listener.start():
            self.status_text.set("键盘监听失败，请检查权限后重启")
        self.root.after(70, self.drain_events)
        self.root.after(350, self.refresh_window)

    def make_widgets(self):
        bg = "#f7f9fc"
        fg = "#1f2937"
        tk.Label(self.root, text="跳一跳 · 空格 / 退格", bg=bg,
                 fg=fg, font=("Microsoft YaHei UI", 14, "bold")).pack(pady=(13, 4))
        tk.Label(self.root, textvariable=self.game_text, bg=bg, fg="#64748b",
                 font=("Microsoft YaHei UI", 9)).pack()

        tk.Label(self.root, textvariable=self.piece_text, bg=bg, fg="#dc2626",
                 font=("Microsoft YaHei UI", 10)).pack(anchor="w", padx=22, pady=(10, 3))
        tk.Label(self.root, textvariable=self.target_text, bg=bg, fg="#16a34a",
                 font=("Microsoft YaHei UI", 10)).pack(anchor="w", padx=22, pady=3)
        tk.Label(self.root, textvariable=self.distance_text, bg=bg, fg=fg,
                 font=("Microsoft YaHei UI", 10)).pack(anchor="w", padx=22, pady=(4, 9))

        row = tk.Frame(self.root, bg=bg)
        row.pack(fill="x", padx=22)
        tk.Label(row, text="力度（毫秒/像素）", bg=bg, fg=fg,
                 font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        self.spinbox = tk.Spinbox(
            row, from_=self.MIN_FACTOR, to=self.MAX_FACTOR,
            increment=0.001, format="%.3f", width=8,
            textvariable=self.factor_input, command=self.commit_factor,
            font=("Consolas", 11), justify="center"
        )
        self.spinbox.pack(side="right")
        self.spinbox.bind("<Return>", self.commit_factor)
        self.spinbox.bind("<FocusOut>", self.commit_factor)

        self.slider = tk.Scale(
            self.root, from_=self.slider_center - self.SLIDER_HALF_RANGE,
            to=self.slider_center + self.SLIDER_HALF_RANGE,
            resolution=0.001, variable=self.factor, orient=tk.HORIZONTAL,
            showvalue=False, length=312, sliderlength=13,
            bg=bg, fg=fg, highlightthickness=0, bd=0,
            troughcolor="#dbe4f0", activebackground="#3b82f6",
            command=self.slider_moved
        )
        self.slider.pack(pady=(1, 0))

        buttons = tk.Frame(self.root, bg=bg)
        buttons.pack(pady=(0, 6))
        for text, delta in (("−0.010", -0.010), ("−0.001", -0.001),
                            ("+0.001", 0.001), ("+0.010", 0.010)):
            tk.Button(buttons, text=text, width=7,
                      command=lambda d=delta: self.adjust_factor(d)).pack(side="left", padx=3)

        tk.Label(self.root, text="滑块为当前力度附近的精调范围；可输入精确数值",
                 bg=bg, fg="#64748b", font=("Microsoft YaHei UI", 9)).pack(pady=(0, 5))
        tk.Label(self.root, textvariable=self.status_text, bg="#e8eef8", fg="#1d4ed8",
                 wraplength=325, justify="center", height=2,
                 font=("Microsoft YaHei UI", 9)).pack(fill="x", padx=12, pady=(2, 9))
        tk.Label(self.root, text="空格：棋子 → 目标 → 跳跃    │    Backspace：撤销",
                 bg=bg, fg="#475569", font=("Microsoft YaHei UI", 9)).pack()

    def set_factor(self, new_factor, mark_user=False):
        """统一处理拖动、数值输入、按钮和窗口大小自动适配。"""
        value = round(max(self.MIN_FACTOR, min(self.MAX_FACTOR, float(new_factor))), 3)
        if mark_user:
            self.user_adjusted = True
        self._ignore_slider = True
        try:
            if abs(value - self.slider_center) > self.SLIDER_HALF_RANGE - 0.002:
                self.slider_center = value
                self.slider.configure(
                    from_=max(self.MIN_FACTOR, value - self.SLIDER_HALF_RANGE),
                    to=min(self.MAX_FACTOR, value + self.SLIDER_HALF_RANGE)
                )
            self.factor.set(value)
            self.slider.set(value)
            self.factor_input.set(f"{value:.3f}")
        finally:
            self._ignore_slider = False
        self.update_distance()

    def slider_moved(self, value):
        if self._ignore_slider:
            return
        value = round(float(value), 3)
        self.user_adjusted = True
        self.factor.set(value)
        self.factor_input.set(f"{value:.3f}")
        self.update_distance()

    def commit_factor(self, _event=None):
        try:
            number = float(self.factor_input.get())
            if not math.isfinite(number):
                raise ValueError("力度必须是有限数值")
        except ValueError:
            self.factor_input.set(f"{self.factor.get():.3f}")
            self.status_text.set("力度格式无效，请输入数字，例如 3.245")
            return
        self.set_factor(number, mark_user=True)

    def adjust_factor(self, delta):
        self.set_factor(self.factor.get() + delta, mark_user=True)

    def refresh_window(self):
        if self.closing:
            return
        hwnd = self.game_hwnd
        if not hwnd or not client_box(hwnd):
            hwnd = find_game_window()
            if hwnd != self.game_hwnd:
                self.game_hwnd = hwnd
                self.reset_points()
                self.last_box = None
            if not hwnd:
                self.game_text.set("未找到窗口：请先打开微信「跳一跳」")
                self.root.after(600, self.refresh_window)
                return
        box = client_box(hwnd)
        if box:
            if self.last_box and self.last_box != box:
                self.reset_points()
                self.status_text.set("游戏窗口移动或改变尺寸，请重新从棋子开始选点")
            self.last_box = box
            self.game_text.set(f"已连接微信游戏 · {box[2]} × {box[3]}")
            if not self.initial_positioned:
                self.initial_positioned = True
                if not self.user_adjusted:
                    guess = 1.35 * 1080.0 / box[2]
                    self.set_factor(guess)
                self.position_beside(box)
                self.status_text.set("就绪：鼠标指向棋子底部，按第一次空格")
        self.root.after(600, self.refresh_window)

    def position_beside(self, box):
        left, top, width, _ = box
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pw, ph = 355, 353
        x = left + width + 12
        if x + pw > screen_w:
            x = left - pw - 12
        x = max(0, min(x, screen_w - pw))
        y = max(15, min(top + 30, screen_h - ph - 60))
        self.root.geometry(f"{pw}x{ph}+{x}+{y}")

    def reset_points(self):
        self.piece = None
        self.target = None
        self.piece_text.set("第 1 步 · 棋子：未选择")
        self.target_text.set("第 2 步 · 目标：未选择")
        self.update_distance()

    def update_distance(self):
        if not self.piece or not self.target:
            self.distance_text.set("距离：—       长按：—")
            return
        dist = math.hypot(self.target[0] - self.piece[0],
                          self.target[1] - self.piece[1])
        milliseconds = round(dist * self.factor.get())
        self.distance_text.set(f"距离：{dist:.1f} px       长按：{milliseconds} ms")

    def locate_text(self, pos):
        box = self.last_box
        if not box:
            return str(pos)
        return f"({pos[0] - box[0]}, {pos[1] - box[1]})"

    def drain_events(self):
        if self.closing:
            return
        try:
            while True:
                item = self.events.get_nowait()
                kind = item[0]
                if kind == "key":
                    _, vk, pos, hwnd = item
                    if hwnd != self.game_hwnd:
                        continue
                    if vk == VK_SPACE:
                        self.advance(pos)
                    elif vk == VK_BACK:
                        self.undo()
                elif kind == "jump_done":
                    self.busy = False
                    self.reset_points()
                    self.status_text.set(item[1] + "；下一跳从棋子开始")
                elif kind == "hook_error":
                    self.status_text.set("键盘监听出现问题：" + item[1][:55])
        except queue.Empty:
            pass
        self.root.after(70, self.drain_events)

    def advance(self, pos):
        if self.busy:
            return
        box = client_box(self.game_hwnd)
        if not box:
            self.status_text.set("未找到有效游戏窗口")
            return
        if self.piece is None:
            if not inside(box, pos):
                self.status_text.set("先将鼠标指向棋子底部，再按空格")
                return
            self.piece = pos
            self.piece_text.set("第 1 步 · 棋子：" + self.locate_text(pos))
            self.status_text.set("棋子已选择 → 鼠标指向目标平台中心，再按空格")
        elif self.target is None:
            if not inside(box, pos):
                self.status_text.set("请将鼠标指向目标平台顶面中心，再按空格")
                return
            self.target = pos
            self.target_text.set("第 2 步 · 目标：" + self.locate_text(pos))
            self.update_distance()
            self.status_text.set("目标已选择 → 再按空格跳跃；按 Backspace 撤销目标")
        else:
            self.jump()

    def undo(self):
        if self.busy:
            self.status_text.set("正在跳跃，无法撤销已开始的长按")
            return
        if self.target is not None:
            self.target = None
            self.target_text.set("第 2 步 · 目标：未选择")
            self.status_text.set("已撤销目标点 → 鼠标指向目标，按空格重新选择")
        elif self.piece is not None:
            self.piece = None
            self.piece_text.set("第 1 步 · 棋子：未选择")
            self.status_text.set("已撤销棋子点 → 鼠标指向棋子，按空格重新选择")
        else:
            self.status_text.set("当前没有可撤销的选点")
        self.update_distance()

    def jump(self):
        if self.busy:
            return
        if not self.piece or not self.target:
            return
        if not self.last_box or not client_box(self.game_hwnd):
            self.status_text.set("微信游戏窗口不存在，请重新打开")
            return
        distance = math.hypot(self.target[0] - self.piece[0],
                              self.target[1] - self.piece[1])
        ms = distance * self.factor.get()
        if distance < 8:
            self.status_text.set("两点过近，请按 Backspace 重新选择目标")
            return
        if ms > 3500:
            self.status_text.set("长按超过 3.5 秒，请调低力度或退格重选")
            return
        self.busy = True
        self.status_text.set(f"跳跃中：{distance:.1f}px × {self.factor.get():.3f} = {ms:.0f}ms")
        threading.Thread(target=self.do_jump, args=(self.game_hwnd, ms), daemon=False).start()

    def do_jump(self, hwnd, ms):
        pressed = False
        result = "跳跃未完成"
        old_pos = cursor_xy()
        try:
            box = client_box(hwnd)
            if not box:
                raise RuntimeError("微信游戏窗口已关闭")
            x = int(box[0] + box[2] * 0.78)
            y = int(box[1] + box[3] * 0.75)
            if not user32.SetCursorPos(x, y):
                raise RuntimeError("鼠标移动失败，请检查权限")
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.07)
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            pressed = True
            # 尽量减少普通 time.sleep 在 Windows 调度下的毫秒级误差。
            deadline = time.perf_counter() + ms / 1000.0
            remaining = deadline - time.perf_counter()
            if remaining > 0.015:
                time.sleep(remaining - 0.012)
            while (remaining := deadline - time.perf_counter()) > 0:
                if remaining > 0.006:
                    time.sleep(remaining - 0.003)
            result = f"已发送 {ms:.0f}ms 长按"
        except Exception as exc:
            result = f"执行失败：{exc}"
        finally:
            if pressed:
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            if old_pos:
                user32.SetCursorPos(*old_pos)
            self.events.put(("jump_done", result))

    def close(self):
        if self.busy:
            self.status_text.set("正在执行长按，结束后再关闭")
            return
        self.closing = True
        self.listener.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    JumpPanel().run()
