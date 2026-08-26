# -*- coding: utf-8 -*-
'''
Created on 25.08.2023

@author: Administrator
'''
import psutil
import win32gui
import win32process
import win32con

def find_process_by_port(port):
    for proc in psutil.process_iter(['pid', 'connections']):
        for conn in proc.info['connections']:
            if conn.laddr.port == port:
                return proc.info['pid']
    return None

def find_window_by_pid(pid):
    hwnds = []
    def callback(hwnd, hwnds):
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid:
            hwnds.append(hwnd)
        return True  # Continue enumeration
    win32gui.EnumWindows(callback, hwnds)
    return hwnds

def bring_window_to_front(hwnd):
    try:
        # Try to restore the window if it is minimized
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
        print(f"Window with handle {hwnd} brought to the front.")
    except Exception as e:
        print(f"Error bringing window to front: {e}")

def bring_window_to_front_by_port(port):
    pid = find_process_by_port(port)
    if pid:
        hwnds = find_window_by_pid(pid)
        if hwnds:
            for hwnd in hwnds:
                window_text = win32gui.GetWindowText(hwnd)
                if "tidal" in window_text.lower() or " - " in window_text.lower():
                    bring_window_to_front(hwnd)
                else:
                    print(f"Window with handle {hwnd} does not contain 'tidal'.")
        else:
            print(f"No window found for PID {pid}.")
    else:
        print(f"No process found using port {port}.")