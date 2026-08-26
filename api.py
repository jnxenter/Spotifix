import asyncio
import threading

from httpcore import ProxyError
from lxml import html
import os
import io
import logging
import string
import sys
import zipfile
import time
import subprocess
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
import random
from urllib.parse import urlparse
import shutil
import atexit
import signal
import psutil
from colorama import init, Fore
import uuid
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
from comtypes import CLSCTX_ALL
import pythoncom
import json

from requests import RequestException
from websocket import create_connection
import queue
from Crypto.Cipher import AES
import base64
import secrets
import base64
from pathlib import Path
from tkinter import filedialog, messagebox
import hmac
import requests
import random
import string
import hashlib
from functools import wraps
from ConsoleLogger import add_log
import ConsoleLogger
import UtilsService
import asyncio
import websockets
from uiautomator2 import Device
from uiautomator2 import UiObject
from uiautomator2 import UiObjectNotFoundError
import uiautomator2 as ua
import uiautomator2
from time import sleep
from bs4 import BeautifulSoup
from fp.fp import FreeProxy
import adbutils
def resource_path(relative_path):
    """ Get the absolute path to the resource, works for both development and packaged executables """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Use the function to reference the u2.jar file
u2_jar_path = resource_path('uiautomator2/assets/u2.jar')
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

project_dir_old = os.getenv('APPDATA')
project_dir2 = os.path.join(project_dir_old, 'Spotifix')
if not os.path.exists(project_dir2):
    os.makedirs(project_dir2, exist_ok=True)
project_dir = os.path.join(project_dir_old, 'Spotifix', 'Spotify Mobile')
if not os.path.exists(project_dir):
    os.makedirs(project_dir, exist_ok=True)

files = os.path.join(project_dir_old, 'Spotifix', 'Spotify Mobile', 'Files')
if not os.path.exists(files):
    os.makedirs(files, exist_ok=True)

init()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(project_dir, "Files", "batches.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

Bot_name = "Spotifix"
global_bot_name = "SpotiFix"
Bot_version = "4.0.0"
GITHUB_REPO = "rogelioguzmantiti-hub/Spotifix"
backend_state = 'Initializing...'
akey = 'jonex program key'.encode('utf-8')

SUPPORTED_APPS = {
    'spotify': {
        'package': 'com.spotify.music',
        'display_name': 'Spotify',
        'main_activity': '.MainActivity',
        'launch_activity': 'com.spotify.music/com.spotify.music.MainActivity',
    },
    'apple_music': {
        'package': 'com.apple.android.music',
        'display_name': 'Apple Music',
        'main_activity': 'com.apple.android.music',
    },
    'tidal': {
        'package': 'com.aspiro.tidal',
        'display_name': 'Tidal',
        'launch_activity': 'com.aspiro.tidal/com.aspiro.wamp.LoginFragmentActivity',
    },
}

startupinfo = None
if os.name == 'nt':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

try:
    adb_path = adbutils.adb_path()
except Exception:
    adb_path = 'adb'

# Checksum and KeyAuth initialization removed



def generate_secret_key(length=64):
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode()


class Batch(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Batch {self.name}>'


class StreamRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    streams_done = db.Column(db.Integer, nullable=False)
    artist_name = db.Column(db.String(100), nullable=False)
    song_name = db.Column(db.String(100), nullable=False)
    current_playtime = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<StreamRecord {self.timestamp} - {self.streams_done}>'

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    udid = db.Column(db.String(100), nullable=False)
    manufacturer = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    hardware_id = db.Column(db.String(100), nullable=False)
    android_version = db.Column(db.String(100), nullable=True)
    spotify_version = db.Column(db.String(100), nullable=True)
    bindedAccount = db.Column(db.String(100), nullable=True)
    bindedProxy = db.Column(db.String(100), nullable=True)
    accountType = db.Column(db.String(100), nullable=True)
    connected = db.Column(db.Boolean, default=False)
    local_code = db.Column(db.String(50), nullable=True)
    logged_in = db.Column(db.Boolean, default=False)  # New attribute to store logged-in status

    def __repr__(self):
        return f'<Device {self.udid}>'

class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    artist_name = db.Column(db.String(100), nullable=False)
    album_name = db.Column(db.String(100), nullable=False)
    song_count = db.Column(db.Integer, nullable=False)
    time_read = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Link {self.link}>'




worker_bot_running = False
worker_threads = {}
worker_napster_executable_path = None
worker_streams_done = 0
worker_streams_done_spotify = 0
worker_streams_done_tidal = 0
worker_streams_done_apple = 0
worker_devices_connected = 0
worker_successful_logins = 0
worker_unsuccessful_logins = 0
worker_song_likes = 0
worker_album_likes = 0
worker_follows_done = 0
worker_proxy_errors = 0
worker_bot_errors = 0

worker_thread_logging_in = False

previous_streams_per_month = None
current_streams_per_month = 0

worker_loaded_accounts = []
worker_loaded_link = []
worker_loaded_tidal_links = []
worker_loaded_apple_links = []
worker_loaded_proxies = []

config_threads_to_start = 0
config_optimize_napster_app = False
config_streams_to_do = 0
config_album_likes_rate = 0
config_song_likes_rate = 0
config_play_full_song_perc = 0
config_follows_rate = 0
config_playtime_type = ''
config_playtime_seconds = ''
config_spotify_playtime = ''
config_tidal_playtime = ''
config_apple_playtime = ''
config_playtime_percentage = ''
config_use_proxies = False
config_links_batch_id = ''
config_tidal_links_batch_id = ''
config_apple_links_batch_id = ''
config_proxies_batch_id = ''
config_session_time = ''
config_stay_logged_in = False
config_accounts_batch_id = ''
config_use_webhook = False
config_webhook_name = ''
config_webhook_url = ''
config_webhook_interval = 0
config_shuffle_perc = 0
config_search_links_perc = 0
config_streaming_mode_only = False

config_selected_apps = ['spotify']

session_start_global = 0
_multi_session_remaining = 0

config_hide_napster_app = False
config_mute_napster_app = False

config_use_clonned_apks = True
config_use_simultaneously_automation_for_clones = True
confog_amount_of_cloned_apks_to_run = 5

settings_capsolver_api_key = None

start_time = time.time()
used_accounts = set()
used_ports = set()
stop_flags = {}

stream_data_queue = []
stream_data_lock = threading.Lock()
file_lock = threading.Lock()

device_ui_locks = {}

def verify_token(token):
    try:
        # Decrypt the token using the key
        decrypted_data = decrypt_data(token, akey)
        if decrypted_data != "Decryption failed":
            # Further checks like expiration, or matching the user credentials can be added here
            return True
        else:
            return False
    except Exception as e:
        # print(f"Token verification failed: {str(e)}")
        return False


def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token or not verify_token(token):
            return jsonify({"message": "Unauthorized"}), 401

        return f(*args, **kwargs)

    return decorated_function


def save_stream_data():
    while True:
        time.sleep(10)
        records_to_save = []
        with stream_data_lock:
            if len(stream_data_queue) != 0:
                records_to_save = stream_data_queue[:]
                stream_data_queue.clear()
        if records_to_save:
            with app.app_context():
                for record in records_to_save:
                    new_record = StreamRecord(
                        timestamp=record['timestamp'],
                        streams_done=record['streams_done'],
                        artist_name=record['artist_name'],
                        song_name=record['song_name'],
                        current_playtime=record['current_playtime']
                    )
                    db.session.add(new_record)
                db.session.commit()


# Start the consumer thread
consumer_thread = threading.Thread(target=save_stream_data)
consumer_thread.start()


def send_stream_data_to_consumer(timestamp, streams_done, artist_name, song_name, current_playtime):
    stream_data = {
        'timestamp': timestamp,
        'streams_done': streams_done,
        'artist_name': artist_name,
        'song_name': song_name,
        'current_playtime': current_playtime
    }
    with stream_data_lock:
        stream_data_queue.append(stream_data)


def load_used_accounts():
    sessions_folder = os.path.join(project_dir, 'Files', 'Sessions')
    if os.path.exists(sessions_folder):
        for session_dir in os.listdir(sessions_folder):
            account_file_path = os.path.join(sessions_folder, session_dir, 'account.txt')
            if os.path.isfile(account_file_path):
                with open(account_file_path, 'r') as file:
                    account = file.read().strip()
                    used_accounts.add(account)


def save_account_to_file(port, account):
    session_folder = os.path.join(project_dir, 'Files', 'Sessions', str(port))
    if not os.path.exists(session_folder):
        os.makedirs(session_folder, exist_ok=True)
    account_file_path = os.path.join(session_folder, 'account.txt')
    with open(account_file_path, 'w') as file:
        file.write(account)

def kill_process_on_port(port):
    try:
        # Find the process using the specified port
        for proc in psutil.process_iter(['pid', 'connections']):
            for conn in proc.info['connections']:
                if conn.laddr.port == port:
                    pid = proc.info['pid']
                    # Kill the process
                    proc.terminate()  # or proc.kill() to force kill
                    proc.wait(timeout=3)
                    return f"Process with PID {pid} using port {port} successfully terminated."
        return f"No process found using port {port}."
    except psutil.NoSuchProcess:
        return "No such process found."
    except psutil.TimeoutExpired:
        return "Failed to terminate the process within the timeout."
    except Exception as e:
        return f"An error occurred: {e}"


def get_running_time():
    elapsed_time = time.time() - start_time
    days, remainder = divmod(elapsed_time, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(days)} days, {int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def encrypt_data(data, key):
    """Encrypt data with AES encryption using EAX mode for confidentiality and authenticity."""
    key = hashlib.sha256(key).digest()[:32]
    cipher = AES.new(key, AES.MODE_EAX)
    nonce = cipher.nonce
    ciphertext, tag = cipher.encrypt_and_digest(data.encode('utf-8'))
    return base64.b64encode(nonce + tag + ciphertext).decode('utf-8')


def decrypt_data(enc_data, key):
    """Decrypt data with AES encryption, handling potential errors in decryption."""
    try:
        # Decode the data strictly, this raises an exception if there are issues
        enc_data_bytes = base64.b64decode(enc_data, validate=True)
        nonce, tag, ciphertext = enc_data_bytes[:16], enc_data_bytes[16:32], enc_data_bytes[32:]
        key = hashlib.sha256(key).digest()[:32]
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext.decode('utf-8')
    except (ValueError, KeyError, base64.binascii.Error) as e:
        return "Decryption failed"


unhashed_token = ""
crbrstoken = None


# Function to create a JWT token
def create_token(info):
    parts = str(info).split(':', 1)  # Split only on first colon to handle colons in passwords
    email = parts[0]
    password = parts[1] if len(parts) > 1 else ''
    data = json.dumps({"username": email,
                       "password": password})
    global unhashed_token
    global akey
    unhashed_token = encrypt_data(data, akey)
    return unhashed_token


def get_device_manufacturer(udid):
    result = subprocess.run(
        [adb_path, '-s', udid, 'shell', 'getprop', 'ro.product.manufacturer'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        startupinfo=startupinfo
    )
    return result.stdout.strip()

def get_device_model(udid):
    result = subprocess.run(
        [adb_path, '-s', udid, 'shell', 'getprop', 'ro.product.model'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        startupinfo=startupinfo
    )
    return result.stdout.strip()

def get_device_hardware_id(udid):
    result = subprocess.run(
        [adb_path, '-s', udid, 'shell', 'getprop', 'ro.serialno'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        startupinfo=startupinfo
    )
    return result.stdout.strip()

def get_device_android_version(udid):
    result = subprocess.run(
        [adb_path, '-s', udid, 'shell', 'getprop', 'ro.build.version.release'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        startupinfo=startupinfo
    )
    return result.stdout.strip()


def get_device_spotify_version(udid, pkg='com.spotify.music'):
    result = subprocess.run(
        [adb_path, '-s', udid, 'shell', 'dumpsys', 'package', pkg],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        startupinfo=startupinfo
    )
    out = result.stdout or ''
    for line in out.splitlines():
        if 'versionName=' in line and 'minSdk' not in line:
            return line.strip().split('versionName=')[-1].strip()
    return None


# ---------------------------------------------------------------------------
# Spotify UI profiles by version.
#
# Spotify changes its view resource-ids between versions. Each profile maps a
# logical key (stable across versions) to the resource-id suffix used by a
# given Spotify version. The default profile uses the ids of the 9.1.x line;
# if a version is unknown, the default profile is used.
#
# Persisted to <project_dir>/Files/spotify_ui_profiles.json so new versions
# can be registered at runtime without recompiling the backend.
# ---------------------------------------------------------------------------
SPOTIFY_UI_PROFILES = {
    'default': {
        'buttons_container': 'buttons_container',
        'username_text': 'username_text',
        'password_text': 'password_text',
        'login_button': 'login_button',
        'login_error_message': 'login_error_message',
        'home_tab': 'home_tab',
        'premium_tab': 'premium_tab',
        'later_button': 'later_button',
        'dismiss_text': 'dismiss_text',
        'confirm_button': 'confirm_button',
        'update_payment_button': 'update_payment_button',
        'picker_recycler_view': 'picker_recycler_view',
        'pickerTitle': 'pickerTitle',
        'secondary_button': 'secondary_button',
        'secondaryActionButton': 'secondaryActionButton',
        'actionButton': 'actionButton',
        'decline': 'decline',
        'body': 'body',
        'device_name': 'device_name',
        'screensaver_ad_footer': 'screensaver_ad_footer',
        'spotify_logo_no_text': 'spotify_logo_no_text',
        'home_page_recycler': 'home_page_recycler',
        'faceheader': 'faceheader',
        'contextual_audio_secondary_btn': 'contextual_audio_secondary_btn',
        'navigation_bar': 'navigation_bar',
        'search_tab': 'search_tab',
        'browse_search_bar_container': 'browse_search_bar_container',
        'query': 'query',
        'find_search_field_text': 'find_search_field_text',
        'search_content_recyclerview': 'search_content_recyclerview',
        'search_body': 'search_body',
        'no_results_banner_search_root': 'no_results_banner_search_root',
        'row_root': 'row_root',
        'title': 'title',
        'subtitle': 'subtitle',
        'artwork': 'artwork',
        'artwork_slot': 'artwork_slot',
        'metadata_slot': 'metadata_slot',
        'cwp_header_media_slot': 'cwp_header_media_slot',
        'creator_names': 'creator_names',
        'heart_button': 'heart_button',
        'cwp_header_action2': 'cwp_header_action2',
        'shuffle_button': 'shuffle_button',
        'button_play_and_pause': 'button_play_and_pause',
        'now_playing_bar_layout': 'now_playing_bar_layout',
        'nowplaying_elements_playpause_button': 'nowplaying_elements_playpause_button',
        'playback_controls_container': 'playback_controls_container',
        'next_button': 'next_button',
        'cover_image': 'cover_image',
        'close_button': 'close_button',
        'children': 'children',
        'position': 'position',
        'position_text': 'position_text',
        'duration': 'duration',
        'duration_text': 'duration_text',
        'track_info_view_subtitle': 'track_info_view_subtitle',
        'track_info_view_title': 'track_info_view_title',
        'feedback_buttons_container': 'feedback_buttons_container',
        'back_button': 'back_button',
        'follow_button': 'follow_button',
        'collapsing_toolbar': 'collapsing_toolbar',
        'webview_container': 'webview_container',
        'player_overlay_header': 'player_overlay_header',
        'design_bottom_sheet': 'design_bottom_sheet',
        'button_positive': 'button_positive',
        'password_field': 'password_field',
        'continue_button': 'continue_button',
        'container': 'container',
        'sidedrawer_recyclerview': 'sidedrawer_recyclerview',
        'compose_view': 'compose_view',
    },
}


def _load_spotify_ui_profiles():
    try:
        profile_file = os.path.join(project_dir, 'Files', 'spotify_ui_profiles.json')
        if os.path.isfile(profile_file):
            with open(profile_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                for version, mapping in data.items():
                    if version == 'default' and isinstance(mapping, dict):
                        SPOTIFY_UI_PROFILES['default'].update(mapping)
                    elif isinstance(mapping, dict):
                        SPOTIFY_UI_PROFILES[version] = mapping
    except Exception:
        pass


def spotify_ui(pkg, spotify_version, key):
    """Return the resourceId for a logical UI key on a given Spotify version.

    Unknown versions fall back to the default profile; the current code's
    resource-ids are the baseline (identity mapping).
    """
    profile = SPOTIFY_UI_PROFILES.get(spotify_version or '')
    if not isinstance(profile, dict):
        profile = SPOTIFY_UI_PROFILES.get('default', {})
    suffix = profile.get(key) or SPOTIFY_UI_PROFILES['default'].get(key, key)
    return f'{pkg}:id/{suffix}'


def dump_live_nodes(udid, package_hint='com.spotify.music', d=None):
    """Dump the current UI hierarchy of a device and return parsed nodes.

    Merges BOTH the system uiautomator dump and (when an active uiautomator2
    session `d` is available) d.dump_hierarchy(). This covers both cases:
    - Spotify 9.1.68 line: the system dumper captures Compose screens that
      uiautomator2 misses.
    - Spotify 9.1.72 line: the system dumper gets killed by an active ATX
      session (exit 137) while uiautomator2's dump still sees the Compose UI.
    Duplicated nodes are removed.
    """
    def _system_dump():
        dump_out = subprocess.run([adb_path, '-s', udid, 'shell', 'uiautomator', 'dump', '/sdcard/ui_live.xml'],
                                  capture_output=True, timeout=15)
        if 'dumped to' not in (dump_out.stdout or b'').decode(errors='replace') and \
           'dumped to' not in (dump_out.stderr or b'').decode(errors='replace'):
            return None
        pull_out = subprocess.run([adb_path, '-s', udid, 'pull', '/sdcard/ui_live.xml',
                                   os.path.join(tempfile.gettempdir(), 'ui_live.xml')],
                                  capture_output=True, timeout=30)
        xml_path = os.path.join(tempfile.gettempdir(), 'ui_live.xml')
        if not os.path.isfile(xml_path):
            return None
        with open(xml_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    def _usable(nodes):
        return nodes and any(
            n.get('text') or n.get('contentDesc') or n.get('resourceId')
            for n in nodes if not n.get('error')
        )

    def _dedupe(all_nodes):
        seen = set()
        out = []
        for n in all_nodes:
            key = (n.get('text', ''), n.get('contentDesc', ''), n.get('resourceId', ''), n.get('bounds', ''))
            if key in seen:
                continue
            seen.add(key)
            out.append(n)
        return out

    try:
        import tempfile
        merged = []
        # 1) uiautomator2 session dump (works on 9.1.72 line even when the
        #    system dumper is killed by the active ATX session)
        if d is not None:
            try:
                nodes2 = _parse_ui_hierarchy(d.dump_hierarchy(compressed=False), package_hint)
                merged.extend(nodes2 or [])
            except Exception as e:
                print(f"dump_live_nodes u2 hierarchy failed ({e})")
        # 2) system dump (Compose-aware, works on 9.1.68 line)
        try:
            xml = _system_dump()
            if xml:
                merged.extend(_parse_ui_hierarchy(xml, package_hint) or [])
        except Exception as e:
            print(f"dump_live_nodes system dump error: {e}")
        merged = _dedupe(merged)
        if _usable(merged):
            return merged
        return merged if merged else [{'error': 'uiautomator dump failed'}]
    except Exception as e:
        return [{'error': str(e)}]


def _parse_ui_hierarchy(xml, package_hint='com.spotify.music'):
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        nodes = []
        for el in root.iter('node'):
            attrs = el.attrib
            rid = attrs.get('resource-id', '')
            text = attrs.get('text', '')
            desc = attrs.get('content-desc', '')
            if not rid and not text and not desc:
                continue
            # uiautomator dump returns bare resource-ids (username_text) for
            # app views; only filter fully-qualified ids from other packages.
            if package_hint and rid and ':id/' in rid and package_hint not in rid:
                continue
            nodes.append({
                'resourceId': rid,
                'text': text,
                'contentDesc': desc,
                'className': attrs.get('class', ''),
                'clickable': attrs.get('clickable', 'false') == 'true',
                'enabled': attrs.get('enabled', 'false') == 'true',
                'focused': attrs.get('focused', 'false') == 'true',
                'checked': attrs.get('checked', ''),
                'bounds': attrs.get('bounds', ''),
            })
        return nodes
    except Exception as e:
        return [{'error': str(e)}]


def find_login_widgets(nodes):
    """Identify email/password fields and the submit button from a live dump.

    Returns {'email': node|None, 'password': node|None, 'submit': node|None}.
    """
    email = password = submit = None
    edit_nodes = [n for n in nodes if 'EditText' in n.get('className', '')]
    for n in nodes:
        rid = n.get('resourceId', '').lower()
        text = (n.get('text', '') + ' ' + n.get('contentDesc', '')).lower()
        cls = n.get('className', '')
        if 'EditText' in cls:
            if 'pass' in rid or n.get('password') or (n.get('text') or '').lower() in ('contraseña', 'password', 'passwort'):
                password = password or n
            elif 'email' in rid or 'user' in rid or 'username' in rid or email is None:
                email = email or n
    if n.get('clickable') and ('log in' in text or 'iniciar' in text or 'anmelden' in text or 'continuar' in text
                               or 'continue' in text or 'login' in rid or 'continue' in rid):
            submit = submit or n
    return {'email': email, 'password': password, 'submit': submit, 'edit_fields': edit_nodes}


def _live_click_and_type(d, udid, kind, value, nodes=None):
    """Locate a login field on the LIVE screen and type into it.

    Uses the system uiautomator dump (Compose-aware) as the primary detection
    instead of uiautomator2's dump_hierarchy (which misses Compose screens on
    newer Spotify builds) or static per-version resource-ids. Returns True on
    success. kind is 'email' or 'password'.
    """
    try:
        if nodes is None and udid:
            nodes = dump_live_nodes(udid, d=d)
        widgets = find_login_widgets(nodes or [])
        w = widgets.get(kind)
        if not w:
            return False
        b = w.get('bounds', '')
        m = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', b)
        if not m:
            return False
        d.click((int(m.group(1)) + int(m.group(3))) // 2,
                (int(m.group(2)) + int(m.group(4))) // 2)
        sleep(0.5)
        d.shell(f"input text '{value}'")
        return True
    except Exception as e:
        print(f"_live_click_and_type {kind} error: {e}")
        return False


def _live_home_screen(d, udid):
    """Detect the Spotify home screen (login success) from a live dump."""
    try:
        nodes = dump_live_nodes(udid, d=d) if udid else []
        for n in nodes:
            t = (n.get('text', '') + ' ' + n.get('contentDesc', '')).lower().strip()
            if t in ('inicio', 'home', 'search', 'buscar', 'your library', 'tu biblioteca', 'biblioteca'):
                return True
        return False
    except Exception:
        return False


def _live_login_error(d, udid):
    """Detect a wrong-credentials error from a live dump (any language)."""
    try:
        nodes = dump_live_nodes(udid, d=d) if udid else []
        for n in nodes:
            t = (n.get('text', '') + ' ' + n.get('contentDesc', '')).lower()
            if any(k in t for k in ('incorrect', 'contraseña no', 'contrasena no', 'no es correcta',
                                    'invalid', 'falsch', 'isn\'t correct', 'doesn\'t match',
                                    'combinación de correo')):
                return True
        return False
    except Exception:
        return False


def _spotify_code_screen_markers():
    """Text fragments that identify Spotify's email-verification-code screen."""
    return ['introduce el código', 'introduce el codigo', 'te hemos enviado por correo',
            'enter the code', 'code we sent', 'email a code', 'send you a code', 'verification code']


def _spotify_password_fallback_texts():
    """Text fragments of the 'log in with password' link on the code screen."""
    return ['iniciar sesión con contraseña', 'iniciar sesión con la contraseña',
            'iniciar sesion con contrasena', 'log in with a password', 'log in with password',
            'log in with a password instead', 'use a password instead',
            'sign in with password', 'mit passwort anmelden', 'anmelden mit passwort']


def _on_spotify_code_screen(d, timeout=0.5, udid=None):
    """True if the current screen is an email-verification-code screen.

    Uses the SYSTEM uiautomator dump (Compose-aware) when a udid is given,
    because uiautomator2's dump_hierarchy misses Compose screens on newer
    Spotify builds.
    """
    try:
        markers = _spotify_code_screen_markers()
        if udid:
            nodes = dump_live_nodes(udid, d=d)
            low = ' '.join((n.get('text', '') + ' ' + n.get('contentDesc', '')).lower() for n in nodes)
        else:
            text = d.dump_hierarchy()
            if not text:
                return False
            low = text.lower()
        return any(m in low for m in markers)
    except Exception:
        return False


def _live_click_text(d, udid, fragments, timeout=1):
    """Click the first live node whose text contains any of `fragments`.

    Compose-aware. If the matched node is not itself clickable, looks for a
    clickable ancestor/Button that encloses it and clicks that instead, so the
    tap always lands on a real tappable target. Returns True if clicked.
    """
    try:
        if not udid:
            return False
        nodes = dump_live_nodes(udid, d=d)
        for n in nodes:
            t = (n.get('text', '') + ' ' + n.get('contentDesc', '')).lower()
            if not any(f in t for f in fragments):
                continue
            b = n.get('bounds', '')
            m = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', b)
            if not m:
                continue
            x1, y1, x2, y2 = (int(m.group(1)), int(m.group(2)),
                              int(m.group(3)), int(m.group(4)))
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            # if the text node is not clickable, find a clickable element that
            # encloses it (button/row wrapper) and use its center
            if not n.get('clickable'):
                target = None
                for a in nodes:
                    if not a.get('clickable'):
                        continue
                    am = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', a.get('bounds', ''))
                    if not am:
                        continue
                    ax1, ay1, ax2, ay2 = (int(am.group(1)), int(am.group(2)),
                                          int(am.group(3)), int(am.group(4)))
                    if ax1 <= x1 and ay1 <= y1 and ax2 >= x2 and ay2 >= y2:
                        target = a
                        break
                if target:
                    am = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', target.get('bounds', ''))
                    cx = (int(am.group(1)) + int(am.group(3))) // 2
                    cy = (int(am.group(2)) + int(am.group(4))) // 2
            d.click(cx, cy)
            return True
    except Exception:
        pass
    return False


def _live_has_password_fallback(d, udid):
    """True if the live screen shows the 'log in with a password' link."""
    try:
        if not udid:
            return False
        nodes = dump_live_nodes(udid, d=d)
        texts = _spotify_password_fallback_texts()
        for n in nodes:
            t = (n.get('text', '') + ' ' + n.get('contentDesc', '')).lower()
            if any(f in t for f in texts):
                return True
    except Exception:
        pass
    return False


def _click_spotify_password_fallback(d, timeout=0.5, udid=None):
    """Click the 'log in with password' link on the email-code screen."""
    if udid:
        # Compose-aware: locate the fallback link via the system dump and
        # click its coordinates.
        try:
            nodes = dump_live_nodes(udid, d=d)
            texts = _spotify_password_fallback_texts()
            for n in nodes:
                t = (n.get('text', '') + ' ' + n.get('contentDesc', '')).lower()
                if not any(f in t for f in texts):
                    continue
                b = n.get('bounds', '')
                m = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', b)
                if not m:
                    continue
                d.click((int(m.group(1)) + int(m.group(3))) // 2,
                        (int(m.group(2)) + int(m.group(4))) // 2)
                return True
        except Exception:
            pass
    for txt in _spotify_password_fallback_texts():
        try:
            if d(textContains=txt).exists(timeout=timeout):
                d(textContains=txt).click()
                return True
        except Exception:
            pass
    return False


def infer_spotify_ui_mapping(nodes, version=None):
    """Infer a Spotify UI profile from a live UI dump.

    Maps logical keys (username_text, password_text, continue_button,
    login_button, buttons_container, etc.) to the resource-id suffixes
    actually present on screen. Returns a dict for SPOTIFY_UI_PROFILES.
    """
    mapping = {}
    rid_of = {}
    for n in nodes:
        rid = n.get('resourceId', '')
        if not rid:
            continue
        suffix = rid.split(':id/')[-1]
        cls = n.get('className', '')
        text = (n.get('text', '') + ' ' + n.get('contentDesc', '')).lower()
        rid_of.setdefault(suffix, n)
        if 'EditText' in cls:
            if 'pass' in suffix or (n.get('text') or '').lower() in ('contraseña', 'password', 'passwort'):
                mapping.setdefault('password_text', suffix)
            elif 'user' in suffix or 'username' in suffix or 'email' in suffix:
                mapping.setdefault('username_text', suffix)
            elif 'password_text' not in mapping:
                mapping.setdefault('password_text', suffix)
        if n.get('clickable'):
            if 'continue' in suffix:
                mapping.setdefault('continue_button', suffix)
            if 'login' in suffix:
                mapping.setdefault('login_button', suffix)
            if 'button' in suffix and 'positive' in suffix:
                mapping.setdefault('button_positive', suffix)
            if 'buttons_container' in suffix:
                mapping.setdefault('buttons_container', suffix)
        if 'buttons_container' in suffix:
            mapping.setdefault('buttons_container', suffix)
    # fill known keys from the default profile if present in this dump
    for key in ('username_text', 'password_text', 'continue_button', 'login_button',
                'buttons_container', 'login_error_message', 'home_tab', 'later_button',
                'dismiss_text', 'confirm_button', 'navigation_bar', 'premium_tab'):
        if key in mapping:
            continue
        default = SPOTIFY_UI_PROFILES['default'].get(key)
        if default and default in rid_of:
            mapping[key] = default
    return mapping


def register_spotify_ui_version(version, mapping):
    """Persist an inferred UI mapping for a Spotify version."""
    try:
        if not version or not isinstance(mapping, dict) or not mapping:
            return False
        existing = SPOTIFY_UI_PROFILES.get(version)
        if isinstance(existing, dict):
            existing.update(mapping)
        else:
            merged = dict(SPOTIFY_UI_PROFILES.get('default', {}))
            merged.update(mapping)
            SPOTIFY_UI_PROFILES[version] = merged
        profile_file = os.path.join(project_dir, 'Files', 'spotify_ui_profiles.json')
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(SPOTIFY_UI_PROFILES, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


@app.route('/device/live_ui', methods=['POST'])
@require_token
def device_live_ui():
    try:
        data = request.get_json(force=True)
        udid = data.get('udid')
        if not udid:
            return jsonify({'success': False, 'error': 'udid required'}), 400
        nodes = dump_live_nodes(udid)
        widgets = find_login_widgets(nodes)
        version = get_device_spotify_version(udid)
        inferred = infer_spotify_ui_mapping(nodes, version)
        register_spotify_ui_version(version, inferred)
        return jsonify({'success': True, 'udid': udid, 'spotify_version': version,
                        'nodes': nodes, 'widgets': widgets, 'inferred_mapping': inferred})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/spotify_ui_profiles', methods=['GET'])
def get_spotify_ui_profiles():
    return jsonify({'success': True, 'profiles': SPOTIFY_UI_PROFILES})


@app.route('/spotify_ui_profiles', methods=['POST'])
def set_spotify_ui_profiles():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, dict) or 'profiles' not in data:
            return jsonify({'success': False, 'error': 'Expected {"profiles": {...}}'}), 400
        profiles = data['profiles']
        if not isinstance(profiles, dict):
            return jsonify({'success': False, 'error': 'profiles must be an object'}), 400
        if 'default' in profiles and isinstance(profiles['default'], dict):
            SPOTIFY_UI_PROFILES['default'].update(profiles['default'])
        for version, mapping in profiles.items():
            if version == 'default' or not isinstance(mapping, dict):
                continue
            SPOTIFY_UI_PROFILES[version] = mapping
        profile_file = os.path.join(project_dir, 'Files', 'spotify_ui_profiles.json')
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(SPOTIFY_UI_PROFILES, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True, 'profiles': SPOTIFY_UI_PROFILES})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/')
def home():
    return "Welcome to the Napster Bot API"

@app.route('/get_log', methods=['GET'])
def get_log_req():
    return jsonify(ConsoleLogger.log_array)

@app.route('/save_settings', methods=['POST'])
@require_token
def save_settings():
    try:
        settings_data = request.json
        global settings_capsolver_api_key
        settings_capsolver_api_key = settings_data.get('apiKey')
        settings_file_path = os.path.join(project_dir, 'Files', 'settings.json')
        with open(settings_file_path, 'w') as settings_file:
            json.dump(settings_data, settings_file, indent=4)

        return jsonify({"message": "Settings saved successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to save settings: {str(e)}"}), 500


@app.route('/load_settings', methods=['GET'])
@require_token
def load_settings():
    try:
        settings_file_path = os.path.join(project_dir, 'Files', 'settings.json')
        if os.path.exists(settings_file_path):
            with open(settings_file_path, 'r') as settings_file:
                settings_data = json.load(settings_file)
                global settings_capsolver_api_key
                settings_capsolver_api_key = settings_data.get('apiKey')
            return jsonify(settings_data), 200
        else:
            return jsonify({"error": "Settings file not found"}), 404

    except Exception as e:
        return jsonify({"error": f"Failed to load settings: {str(e)}"}), 500


@app.route('/check_cred', methods=['POST'])
def check_cred():
    try:
        credentials_file = os.path.join(project_dir, 'Files', 'credentials.json')

        if os.path.isfile(credentials_file):
            with open(credentials_file, 'r') as f:
                credentials_object = json.load(f)

            username = credentials_object.get("username", "")
            password = credentials_object.get("password", "")

            if username and password:
                token = create_token(str(username) + ":" + str(password))
                return jsonify({"success": True, "message": "Successfully logged in!", "token": token}), 200

        return jsonify({"success": False, "message": "Credentials file not found"}), 404
    except Exception as e:
        print(f"check_cred error: {e}")
        return jsonify({"success": False, "message": "Credentials file not found"}), 404


@app.route('/register', methods=['POST'])
def register():
    username = request.json.get('username')
    token = create_token(username)
    return jsonify({"success": True, "message": "Successfully Registered!", "token": token})


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json or {}
        username = str(data.get('username', ''))
        password = str(data.get('password', ''))
        stayloggedin = data.get('stayloggedin', False)

        if str(stayloggedin).lower().__contains__("true"):
            creds = {
                "username": username,
                "password": password
            }
            json_path = os.path.join(project_dir, 'Files', 'credentials.json')
            with open(json_path, "w") as outfile:
                json.dump(creds, outfile, indent=2)

        token = create_token(username + ":" + password)
        return jsonify({"success": True, "message": "Successfully logged in!", "token": token})
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({"success": False, "message": f"Login error: {str(e)}"}), 500


@app.route('/check_token', methods=['POST'])
def check_token():
    # Get the token from the request
    auth_token = request.headers.get('Authorization')

    if not auth_token:
        return jsonify({"message": "Unauthorized"}), 401

    if verify_token(auth_token):
        return jsonify({"message": "Token is valid"}), 200
    else:
        return jsonify({"message": "Unauthorized"}), 401


@app.route('/delete_batch', methods=['POST'])
@require_token
def delete_batch():
    batch_data = request.json
    batch_type = batch_data.get('type')
    batch_id = batch_data.get('id')

    if not batch_type or not batch_id:
        return jsonify({"error": "Batch type and id are required"}), 400

    batch = Batch.query.filter_by(id=batch_id, type=batch_type).first()
    if batch:
        db.session.delete(batch)
        db.session.commit()
        return jsonify({"message": f"Batch {batch_id} deleted successfully"}), 200
    else:
        return jsonify({"error": "Batch not found"}), 404


@app.route('/update_batch', methods=['POST'])
@require_token
def update_batch():
    batch_data = request.json
    batch_type = batch_data.get('type')
    batch_id = batch_data.get('id')
    batch_name = batch_data.get('name')
    batch_content = batch_data.get('content')

    if not batch_type or not batch_id or not batch_name or not batch_content:
        return jsonify({"error": "Batch type, id, name, and content are required"}), 400

    batch = Batch.query.filter_by(id=batch_id, type=batch_type).first()
    if batch:
        batch.name = batch_name
        batch.content = batch_content
    else:
        batch = Batch(id=batch_id, type=batch_type, name=batch_name, content=batch_content)
        db.session.add(batch)
    db.session.commit()

    return jsonify({"message": f"Batch {batch_name} updated successfully"}), 200


@app.route('/add_batch', methods=['POST'])
@require_token
def add_batch():
    batch_data = request.json
    batch_type = batch_data.get('type')
    batch_name = batch_data.get('name')
    batch_content = batch_data.get('content')

    if not batch_type or not batch_name or not batch_content:
        return jsonify({"error": "Batch type, name, and content are required"}), 400

    batch_id = str(uuid.uuid4())
    batch = Batch(id=batch_id, type=batch_type, name=batch_name, content=batch_content)
    db.session.add(batch)
    db.session.commit()

    return jsonify({"message": f"Batch {batch_name} added successfully", "id": batch_id}), 201


@app.route('/get_batches', methods=['GET'])
@require_token
def get_batches():
    batch_type = request.args.get('type')
    if not batch_type:
        return jsonify({"error": "Batch type is required"}), 400

    batches = Batch.query.filter_by(type=batch_type).all()
    batch_list = [{"type": batch.type, "id": batch.id, "name": batch.name, "content": batch.content} for batch in batches]

    return jsonify({"batches": batch_list})


@app.route('/save_config', methods=['POST'])
@require_token
def save_config():
    config_data = request.json
    config_name = config_data.get("config_name")
    if not config_name:
        return jsonify({"error": "Config name is required"}), 400

    config_path = os.path.join(project_dir, 'Files', 'Configs', f'{config_name}.json')
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=4)

    return jsonify({"message": f"Config {config_name} saved successfully"}), 201


@app.route('/save_tidal_links', methods=['POST'])
@require_token
def save_tidal_links():
    data = request.json
    links_text = data.get('links', '')
    tidal_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TidalLinks.txt')
    with open(tidal_file, 'w') as f:
        f.write(links_text.strip())
    return jsonify({"message": "Tidal links saved", "count": len([l for l in links_text.strip().splitlines() if l.strip()])})

@app.route('/get_tidal_links', methods=['GET'])
@require_token
def get_tidal_links():
    tidal_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TidalLinks.txt')
    if os.path.exists(tidal_file):
        with open(tidal_file, 'r') as f:
            return jsonify({"links": f.read()})
    return jsonify({"links": ""})

@app.route('/save_apple_links', methods=['POST'])
@require_token
def save_apple_links():
    data = request.json
    links_text = data.get('links', '')
    apple_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AppleLinks.txt')
    with open(apple_file, 'w') as f:
        f.write(links_text.strip())
    return jsonify({"message": "Apple Music links saved", "count": len([l for l in links_text.strip().splitlines() if l.strip()])})

@app.route('/get_apple_links', methods=['GET'])
@require_token
def get_apple_links():
    apple_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AppleLinks.txt')
    if os.path.exists(apple_file):
        with open(apple_file, 'r') as f:
            return jsonify({"links": f.read()})
    return jsonify({"links": ""})

@app.route('/save_tidal_accounts', methods=['POST'])
@require_token
def save_tidal_accounts():
    data = request.json
    accounts_text = data.get('accounts', '')
    acc_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TidalAccounts.txt')
    with open(acc_file, 'w') as f:
        f.write(accounts_text.strip())
    return jsonify({"message": "Tidal accounts saved", "count": len([l for l in accounts_text.strip().splitlines() if l.strip()])})

@app.route('/get_tidal_accounts', methods=['GET'])
@require_token
def get_tidal_accounts():
    acc_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TidalAccounts.txt')
    if os.path.exists(acc_file):
        with open(acc_file, 'r') as f:
            return jsonify({"accounts": f.read()})
    return jsonify({"accounts": ""})

@app.route('/save_apple_accounts', methods=['POST'])
@require_token
def save_apple_accounts():
    data = request.json
    accounts_text = data.get('accounts', '')
    acc_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AppleAccounts.txt')
    with open(acc_file, 'w') as f:
        f.write(accounts_text.strip())
    return jsonify({"message": "Apple Music accounts saved", "count": len([l for l in accounts_text.strip().splitlines() if l.strip()])})

@app.route('/get_apple_accounts', methods=['GET'])
@require_token
def get_apple_accounts():
    acc_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AppleAccounts.txt')
    if os.path.exists(acc_file):
        with open(acc_file, 'r') as f:
            return jsonify({"accounts": f.read()})
    return jsonify({"accounts": ""})


@app.route('/scrape_devices', methods=['GET'])
@require_token
def scrape_devices():
    try:
        # Run the adb devices command
        result = subprocess.run(
            [adb_path, 'devices'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo
        )
        devices_output = result.stdout.strip().splitlines()[1:]
        devices = []

        with app.app_context():
            for line in devices_output:
                if '\t' in line:
                    udid, status = line.split('\t')

                    # Get additional device info (e.g., manufacturer, model, hardware ID)
                    manufacturer = get_device_manufacturer(udid)
                    model = get_device_model(udid)
                    hardware_id = get_device_hardware_id(udid)
                    android_version = get_device_android_version(udid)
                    spotify_version = get_device_spotify_version(udid)

                    # Check if the device already exists in the database
                    existing_device = Device.query.filter_by(
                        manufacturer=manufacturer,
                        model=model,
                        hardware_id=hardware_id
                    ).first()

                    if existing_device:
                        # Update the device's udid and connected status
                        existing_device.udid = udid  # Since udid can change
                        existing_device.connected = True
                        existing_device.spotify_version = spotify_version
                        add_log("INFO", "Main", f"Device {udid} already registered, updating udid and setting connected to True.")
                        logged_in = existing_device.logged_in  # Get logged_in status from DB
                        bindedAccount = existing_device.bindedAccount
                        bindedProxy = existing_device.bindedProxy
                        accountType = existing_device.accountType
                    else:
                        # Add a new device to the database with default logged_in status
                        new_device = Device(
                            udid=udid,
                            manufacturer=manufacturer,
                            model=model,
                            hardware_id=hardware_id,
                            android_version=android_version,
                            spotify_version=spotify_version,
                            connected=True,
                            bindedAccount='/',
                            bindedProxy='/',
                            accountType='/',
                            logged_in=False,  # Default to False when a new device is added
                            local_code=str(uuid.uuid4())[:8]  # Generate a unique local_code if needed
                        )
                        db.session.add(new_device)
                        add_log("INFO", "Main", f"New device {udid} added to the database.")
                        logged_in = False  # Default for new devices
                        bindedAccount = '/'
                        bindedProxy = '/'
                        accountType = '/'

                    # Commit the changes
                    db.session.commit()

                    # Enable Multi Audio Focus on every detected device
                    try:
                        threading.Thread(target=_enable_multi_audio_focus, args=(udid,), daemon=True).start()
                    except:
                        pass

                    # Add the device details to the response
                    devices.append({
                        'udid': udid,
                        'status': status,
                        'manufacturer': manufacturer,
                        'model': model,
                        'hardware_id': hardware_id,
                        'android_version': android_version,
                        'spotify_version': spotify_version,
                        'bindedAccount': bindedAccount,
                        'bindedProxy': bindedProxy,
                        'accountType': accountType,
                        'logged_in': logged_in  # Include the logged_in status
                    })

        return jsonify({'devices': devices}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/panda_numbers', methods=['GET'])
@require_token
def panda_numbers():
    """Return the Panda phone numbering (number -> adb serial) for connected devices.
    Reads Panda's device.db (table device, columns onlySerial/sort/name, userDelete=0)
    and crosses it with `adb devices` so only connected devices are listed.
    """
    try:
        import sqlite3 as sqlite3_mod
        db_path = os.path.join(os.path.expandvars('%APPDATA%'), '6WPTMA9HZO', 'device.db')
        panda_rows = []
        if os.path.exists(db_path):
            try:
                conn = sqlite3_mod.connect(db_path)
                rows = conn.execute(
                    "SELECT onlySerial, sort, name FROM device WHERE userDelete=0"
                ).fetchall()
                conn.close()
                for serial, num, name in rows:
                    try:
                        panda_rows.append({'num': int(num), 'serial': str(serial), 'model': str(name or '')})
                    except (ValueError, TypeError):
                        continue
            except Exception as e:
                add_log("WARN", "Main", f"panda_numbers: could not read Panda db: {str(e)}")

        result = subprocess.run(
            [adb_path, 'devices'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            startupinfo=startupinfo, timeout=30
        )
        connected = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith('List of devices') or '\t' not in line:
                continue
            serial, state = line.split('\t', 1)
            if state.strip() == 'device':
                connected.add(serial.strip())

        numbers = []
        for p in panda_rows:
            if p['serial'] in connected:
                numbers.append(p)
        numbers.sort(key=lambda x: x['num'])
        return jsonify({'numbers': numbers}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/update_device', methods=['POST'])
@require_token
def update_device():
    data = request.json
    udid = data.get('udid')
    bindedAccount = data.get('bindedAccount')
    bindedProxy = data.get('bindedProxy')

    if not udid:
        return jsonify({'error': 'UDID is required'}), 400

    device = Device.query.filter_by(udid=udid).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    if bindedAccount is not None:
        device.bindedAccount = bindedAccount
    if bindedProxy is not None:
        device.bindedProxy = bindedProxy

    db.session.commit()
    return jsonify({'message': 'Device updated successfully'}), 200



@app.route('/start_bot', methods=['POST'])
@require_token
def start_stop_bot():
    global worker_bot_running
    if worker_bot_running is False:
        try:
            data = request.json
            config_name = data.get('config_name')
            if not config_name:
                return jsonify({"message": "Config name is required"}), 400

            config_path = os.path.join(os.path.join(project_dir, 'Files', 'Configs'), f"{config_name}.json")
            if not os.path.exists(config_path):
                return jsonify({"message": f"Config {config_name} not found"}), 404

            with open(config_path, 'r') as config_file:
                config_data = json.load(config_file)

            global config_streams_to_do
            global config_album_likes_rate
            global config_song_likes_rate
            global config_play_full_song_perc
            global config_follows_rate
            global config_playtime_seconds
            global config_links_batch_id
            global config_tidal_links_batch_id
            global config_apple_links_batch_id
            global config_session_time
            global config_use_webhook
            global config_webhook_name
            global config_webhook_url
            global config_webhook_interval
            global config_shuffle_perc  # Add this line
            global config_search_links_perc
            global config_streaming_mode_only
            global config_use_clonned_apks
            global config_selected_apps

            config_streams_to_do = int(config_data.get('streams_to_do'))
            if config_streams_to_do == 0:
                config_streams_to_do = 99999999
            config_album_likes_rate = int(config_data.get('album_likes_rate', 0))
            config_song_likes_rate = int(config_data.get('song_likes_rate', 0))
            config_follows_rate = int(config_data.get('follows_rate', 0))
            config_play_full_song_perc = int(config_data.get('full_playtime_rate', 0))
            config_playtime_seconds = config_data.get('playtime_seconds')
            config_spotify_playtime = config_data.get('spotify_playtime', '') or ''
            config_tidal_playtime = config_data.get('tidal_playtime', '') or ''
            config_apple_playtime = config_data.get('apple_playtime', '') or ''
            config_streaming_mode_only = config_data.get('streaming_mode_only')
            config_links_batch_id = config_data.get('links_batch_id')
            config_tidal_links_batch_id = config_data.get('tidal_links_batch_id', '')
            config_apple_links_batch_id = config_data.get('apple_links_batch_id', '')
            config_session_time = config_data.get('session_time') or '8-8'
            config_shuffle_perc = int(config_data.get('shuffle_perc'))
            config_search_links_perc = int(config_data.get('search_links_perc'))

            raw_apps = config_data.get('selected_apps', ['spotify'])
            if isinstance(raw_apps, str):
                raw_apps = [a.strip() for a in raw_apps.split(',') if a.strip()]
            config_selected_apps = [a for a in raw_apps if a in SUPPORTED_APPS]
            if not config_selected_apps:
                config_selected_apps = ['spotify']

            webhook_config = config_data.get('webhook', {})
            config_use_webhook = str(webhook_config.get('use'))
            config_webhook_name = webhook_config.get('name')
            config_webhook_url = webhook_config.get('url')
            config_webhook_interval = webhook_config.get('interval')

            global worker_loaded_accounts
            global worker_loaded_proxies
            global worker_loaded_link
            global worker_loaded_tidal_links
            global worker_loaded_apple_links

            with app.app_context():
                batch = Batch.query.filter_by(id=config_links_batch_id, type='links').first()
                if not batch:
                    raise Exception("Link batch not found")
                links = batch.content.splitlines()
                worker_loaded_link = links

                tidal_links = []
                if config_tidal_links_batch_id:
                    tidal_batch = Batch.query.filter_by(id=config_tidal_links_batch_id, type='links').first()
                    if tidal_batch:
                        tidal_links = tidal_batch.content.splitlines()
                worker_loaded_tidal_links = tidal_links

                apple_links = []
                if config_apple_links_batch_id:
                    apple_batch = Batch.query.filter_by(id=config_apple_links_batch_id, type='links').first()
                    if apple_batch:
                        apple_links = apple_batch.content.splitlines()
                worker_loaded_apple_links = apple_links

            if config_use_webhook == 'True':
                webhook_thread = threading.Thread(target=send_discord_webhook,
                                                  args=(int(config_webhook_interval), config_webhook_url))
                webhook_thread.daemon = True
                webhook_thread.start()

            worker_bot_running = True
            bot_thread = threading.Thread(target=main_function, args=(config_data,))
            bot_thread.start()

            return jsonify({"message": f"Bot started with config {config_name}"}), 200
        except Exception as e:
            print(e)
            return jsonify({"message": f"Failed to load config: {e}"}), 400

    else:
        try:
            for thread_number in list(worker_threads.keys()):
                stop_flags[thread_number] = True

            for thread_info in worker_threads.values():
                thread = thread_info.get("thread")
                if thread and thread.is_alive():
                    thread.join(timeout=3)

            worker_threads.clear()
            worker_bot_running = False
            ConsoleLogger.log_array.clear()
            ConsoleLogger.log_array.append('Spotifix 4.0.0 - [Console Logs]')
            ConsoleLogger.log_array.append('<---------------------------------------->')
            ConsoleLogger.log_array.append(' ')
            return jsonify({"message": "Bot stopped"}), 200
        except Exception as e:
            worker_bot_running = False
            print(f"Error stopping bot: {e}")
            return jsonify({"message": f"Error stopping bot: {e}"}), 500


@app.route('/get_worker_threads', methods=['GET'])
@require_token
def get_worker_threads():
    global worker_threads
    panda_map = _get_panda_numbers()
    worker_threads_serializable = {
        key: {
            "UDID": value["UDID"],
            "panda_number": panda_map.get(value["UDID"], None),
            "app": value.get("app", "Spotify"),
            "app_key": value.get("app_key", "spotify"),
            "status": value["status"],
            "proxy": value["proxy"],
            "streams": value.get("streams", 0),
            "likes": value.get("likes", 0),
            "follows": value.get("follows", 0),
            "errors": value.get("errors", 0),
            "session_time": value.get("session_time", 0)
        }
        for key, value in worker_threads.items()
    }
    return jsonify(list(worker_threads_serializable.values()))


def _count_connected_devices():
    """Count currently connected ADB devices dynamically, deduplicating Panda TCP mirrors."""
    try:
        result = subprocess.run([adb_path, 'devices', '-l'], capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
        model_best = {}
        for line in result.stdout.strip().split('\n')[1:]:
            if '\tdevice' not in line and '   device ' not in line:
                continue
            parts = line.split()
            udid = parts[0]
            model_match = next((p.split(':')[1] for p in parts if p.startswith('model:')), None)
            dedup_key = model_match or udid
            is_tcp = udid.startswith('127.0.0.1:')
            if dedup_key not in model_best:
                model_best[dedup_key] = (udid, is_tcp)
            elif is_tcp and not model_best[dedup_key][1]:
                pass
            elif not is_tcp and model_best[dedup_key][1]:
                model_best[dedup_key] = (udid, is_tcp)
        return len(model_best)
    except Exception:
        return worker_devices_connected

@app.route('/get_worker_stats', methods=['GET'])
@require_token
def get_worker_stats():
    global worker_streams_done, worker_streams_done_spotify, worker_streams_done_tidal, worker_streams_done_apple
    global worker_devices_connected
    global worker_successful_logins
    global worker_unsuccessful_logins
    global worker_song_likes
    global worker_album_likes
    global worker_follows_done
    global worker_proxy_errors
    global worker_bot_errors
    worker_devices_connected = _count_connected_devices()
    return jsonify({
        "worker_streams_done": worker_streams_done,
        "worker_streams_done_spotify": worker_streams_done_spotify,
        "worker_streams_done_tidal": worker_streams_done_tidal,
        "worker_streams_done_apple": worker_streams_done_apple,
        "worker_devices_connected": worker_devices_connected,
        "worker_successful_logins": worker_successful_logins,
        "worker_unsuccessful_logins": worker_unsuccessful_logins,
        "worker_song_likes": worker_song_likes,
        "worker_album_likes": worker_album_likes,
        "worker_follows_done": worker_follows_done,
        "worker_proxy_errors": worker_proxy_errors,
        "worker_bot_errors": worker_bot_errors
    })

@app.route('/get_dashboard', methods=['GET'])
@require_token
def get_dashboard():
    """Return real-time dashboard: bot status, per-device app states, streams, health."""
    global worker_bot_running, worker_streams_done, worker_streams_done_spotify
    global worker_streams_done_tidal, worker_streams_done_apple, config_streams_to_do

    devices_status = []
    seen_udids = set()
    panda_map = _get_panda_numbers()
    for key, thread in worker_threads.items():
        udid_base = key.replace('_multiapp', '').replace('_spotify', '').replace('_tidal', '').replace('_apple_music', '')
        if udid_base in seen_udids:
            continue
        seen_udids.add(udid_base)
        panda_num = panda_map.get(udid_base, None)
        devices_status.append({
            'udid': udid_base,
            'panda_number': panda_num,
            'thread_key': key,
            'status': thread.get('status', ''),
            'streams': thread.get('streams', 0),
            'errors': thread.get('errors', 0),
            'session_time': thread.get('session_time', 0),
        })

    app_states = []
    active_apps_per_udid = {}
    for key in worker_threads:
        udid = key.replace('_multiapp', '').replace('_spotify', '').replace('_tidal', '').replace('_apple_music', '')
        if '_multiapp' in key:
            thread_app_str = worker_threads[key].get('app', '')
            app_names = [a.strip().lower() for a in thread_app_str.split('+')]
            name_to_key = {'spotify': 'spotify', 'tidal': 'tidal', 'apple music': 'apple_music'}
            active = set()
            for name in app_names:
                if name in name_to_key:
                    active.add(name_to_key[name])
            if udid not in active_apps_per_udid:
                active_apps_per_udid[udid] = set()
            active_apps_per_udid[udid].update(active)
        else:
            for app_key in ['spotify', 'tidal', 'apple_music']:
                if key.endswith(f'_{app_key}'):
                    if udid not in active_apps_per_udid:
                        active_apps_per_udid[udid] = set()
                    active_apps_per_udid[udid].add(app_key)

    for udid in list(seen_udids):
        active = active_apps_per_udid.get(udid, set())
        if not active:
            for app_key in ['spotify', 'tidal', 'apple_music']:
                active.add(app_key)
        app_map = {
            'spotify': ('com.spotify.music', 'Spotify'),
            'tidal': ('com.aspiro.tidal', 'Tidal'),
            'apple_music': ('com.apple.android.music', 'Apple Music'),
        }
        for app_key in ['spotify', 'tidal', 'apple_music']:
            if app_key not in active:
                continue
            pkg, label = app_map[app_key]
            state, title, artist = _get_now_playing(udid, pkg)
            app_states.append({
                'udid': udid,
                'app': label,
                'state': state,
                'title': title,
                'artist': artist,
            })

    return jsonify({
        'bot_running': worker_bot_running,
        'streams_done': worker_streams_done,
        'streams_spotify': worker_streams_done_spotify,
        'streams_tidal': worker_streams_done_tidal,
        'streams_apple': worker_streams_done_apple,
        'streams_target': config_streams_to_do,
        'devices': devices_status,
        'apps': app_states,
    })

@app.route('/get_config', methods=['GET'])
@require_token
def get_config():
    config_name = request.args.get('name')
    config_path = os.path.join(project_dir, 'Files', 'Configs', f'{config_name}.json')

    if not os.path.exists(config_path):
        return jsonify({"error": "Config not found"}), 404

    with open(config_path, 'r') as file:
        config_data = json.load(file)

    return jsonify(config_data)

@app.route('/get_configs', methods=['GET'])
@require_token
def get_configs():
    config_path = os.path.join(project_dir, 'Files', 'Configs')
    configs = [f.split('.')[0] for f in os.listdir(config_path) if f.endswith('.json')]
    return jsonify({"configs": configs})


@app.route('/get_streams_done', methods=['GET'])
@require_token
def get_streams_done():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Start date and end date are required"}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    streams = StreamRecord.query.filter(StreamRecord.timestamp >= start_date,
                                        StreamRecord.timestamp <= end_date).all()
    streams_list = [
        {"timestamp": stream.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "streams_done": stream.streams_done} for
        stream in streams]

    return jsonify({"streams": streams_list})




def freeze_rotation_port(d):
    try:
        orientation = d.orientation
        if orientation != 'natural':
            d.freeze_rotation(False)
            d.set_orientation("n")
            d.freeze_rotation()
            d.shell("settings put system accelerometer_rotation 0")
            d.shell("content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0")
            d.shell("settings put system user_rotation 0")
            d.freeze_rotation()
    except:
        pass

def ensure_screen_on(d):
    """Keep the device screen awake and turn it on safely if it is off.

    Uses KEYCODE_WAKEUP (d.screen_on) instead of d.press("power"), which
    toggles the power state and can turn the screen OFF when the reported
    'screenOn' value is stale (common on real devices / mirroring apps),
    causing black screens.
    """
    try:
        d.shell("svc power stayon true")
        d.shell("settings put system screen_off_timeout 2147483647")
        if not d.info.get('screenOn'):
            d.screen_on()
            time.sleep(0.5)
        current_package = d.info.get('currentPackageName')
        lock_screen_packages = ['com.android.systemui', 'com.android.keyguard']
        if current_package in lock_screen_packages:
            d.keyevent('82')
    except Exception:
        pass

def is_tcpip_device(udid):
    # Regex to match the IP:port format (common for TCP/IP connected devices)
    return re.match(r'\d+\.\d+\.\d+\.\d+:\d+', udid) is not None

def reconnect_tcpip_device(udid, timeout=10):
    """
    Attempt to reconnect to a device running over TCP/IP using the udid (IP:Port).
    Tries to reconnect for a specified timeout duration (in seconds).

    :param udid: The device's UDID (in the form of IP:Port) to reconnect.
    :param timeout: The time duration to attempt reconnection (default is 10 seconds).
    :return: True if the connection is successful, False otherwise.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Run the adb connect command
            result = subprocess.run([adb_path, 'connect', udid], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
            output = result.stdout.strip() + result.stderr.strip()

            # Check if the connection was successful
            if "connected" in output.lower():
                return True
            elif "unable to connect" in output.lower():
                print(f"Failed to connect to {udid}. Output: {output}")
            else:
                print(f"Retrying connection to {udid}...")

        except Exception as e:
            print(f"Error during reconnection attempt: {str(e)}")

        # Wait for 1 second before retrying
        time.sleep(1)

    # If the function exits the loop, the connection attempt has failed
    print(f"Failed to reconnect to {udid} within {timeout} seconds.")
    return True

def handle_vpn_permission(d):
    """Handle VPN permission prompt if it appears on the device."""
    try:
        if d(resourceId="com.android.vpndialog:id/button_allow").exists:
            d(resourceId="com.android.vpndialog:id/button_allow").click()
            time.sleep(2)
            return True
        return False
    except Exception as e:
        print(f"Error handling VPN permission: {e}")
        return False

def set_proxy_by_oxyproxymanager(d, udid, proxyline, connection_type):
    try:
        freeze_rotation_port(d)
        """Set a proxy on a device using OxyProxyManager and handle reconnections."""
        update_thread_status(udid, 'Setting proxy', None, False, False, False, False, False)

        # Parse the proxyline (IP, port, and optionally username, password)
        username, password = None, None
        if proxyline.count(":") == 3:
            ip, port, username, password = proxyline.split(":")
        else:
            ip, port = proxyline.split(":")

        d.implicitly_wait(5)

        # Try to add a new proxy in the OxyProxyManager
        try:
            d(text="Add new proxy").click(5)
        except:
            d.xpath(
                '//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[3]').click(20)
        d(className="android.widget.ScrollView").wait(5)
        d.xpath('//android.widget.ScrollView/android.widget.EditText[1]').click()
        d.shell("input text 'JNX'")
        # d.xpath('//android.widget.ScrollView/android.widget.EditText[1]').send_keys("JNX")
        screen_width, screen_height = d.window_size()

        try:
            element = d.xpath('//android.widget.ScrollView/android.widget.EditText[1]')
            if element.exists:
                bounds = element.info['bounds']
                start_x = (bounds['left'] + bounds['right']) // 2  # Middle of the element horizontally
                start_y = bounds['bottom']  # Bottom of the element
                end_x = start_x  # Keeping the horizontal position constant for a vertical swipe
                swipe_distance = int(screen_height * 0.8)  # 80% of the screen height
                end_y = max(0, start_y - swipe_distance)  # Ensure end_y remains within screen bounds
                d.swipe(start_x, start_y, end_x, end_y, duration=0.3)  # Ensure it's a swipe up
        except:
            pass
        if username is not None:
            d(text="Password").sibling(className='android.widget.EditText')[4].set_text(password)
            d(text="Username").sibling(className='android.widget.EditText')[3].set_text(username)
            d(text="Port").sibling(className='android.widget.EditText')[2].set_text(port)
            d(text="Server IP").sibling(className='android.widget.EditText')[1].set_text(ip)
            '''if d.xpath('//android.widget.ScrollView/android.widget.EditText[5]').exists:
                d.xpath('//android.widget.ScrollView/android.widget.EditText[5]').click()
                d.shell(f"input text '{password}'")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[4]').click()
                d.shell(f"input text '{username}'")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[3]').click()
                d.shell(f"input text '{port}'")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[2]').click()
                d.shell(f"input text '{ip}'")
            else:
                d.xpath('//android.widget.ScrollView/android.widget.EditText[4]').click()
                d.shell(f"input text '{password}'")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[3]').click()
                d.shell(f"input text '{username}'")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[2]').click()
                d.shell(f"input text '{port}'")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[1]').click()
                d.shell(f"input text '{ip}'")'''

            '''if d.xpath('//android.widget.ScrollView/android.widget.EditText[5]').exists:
                d.xpath('//android.widget.ScrollView/android.widget.EditText[5]').set_text(password)
                d.xpath('//android.widget.ScrollView/android.widget.EditText[4]').set_text(username)
                d.xpath('//android.widget.ScrollView/android.widget.EditText[3]').set_text(port)
                d.xpath('//android.widget.ScrollView/android.widget.EditText[2]').set_text(ip)
            else:
                d.xpath('//android.widget.ScrollView/android.widget.EditText[4]').set_text(password)
                d.xpath('//android.widget.ScrollView/android.widget.EditText[3]').set_text(username)
                d.xpath('//android.widget.ScrollView/android.widget.EditText[2]').set_text(port)
                d.xpath('//android.widget.ScrollView/android.widget.EditText[1]').set_text(ip)'''

        else:
            d(text="Port").sibling(className='android.widget.EditText')[2].set_text(port)
            d(text="Server IP").sibling(className='android.widget.EditText')[1].set_text(ip)
            '''if d.xpath('//android.widget.ScrollView/android.widget.EditText[5]').exists:
                d.xpath('//android.widget.ScrollView/android.widget.EditText[3]').click()
                d.shell(f"input text '{port}'")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[2]').click()
                d.shell(f"input text '{ip}'")
            else:
                d.xpath('//android.widget.ScrollView/android.widget.EditText[2]').click()
                d.shell(f"input text '{port}'")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[1]').click()
                d.shell(f"input text '{ip}'")'''

            '''if d.xpath('//android.widget.ScrollView/android.widget.EditText[5]').exists:
                d.xpath('//android.widget.ScrollView/android.widget.EditText[5]').set_text("")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[4]').set_text("")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[3]').set_text(port)
                d.xpath('//android.widget.ScrollView/android.widget.EditText[2]').set_text(ip)
            else:
                d.xpath('//android.widget.ScrollView/android.widget.EditText[4]').set_text("")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[3]').set_text("")
                d.xpath('//android.widget.ScrollView/android.widget.EditText[2]').set_text(port)
                d.xpath('//android.widget.ScrollView/android.widget.EditText[1]').set_text(ip)'''
        try:
            d(text="Create").click(2)
        except:
            d.xpath(
                '//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[2]/android.widget.Button[1]').click(
                5)

        # Wait for proxy to connect and handle VPN permission if it appears
        connected = False
        while not connected:
            try:
                if d(textContains="Connected").exists(3):
                    connected = True

                if d(text="JNX").exists:
                    d(text="JNX").click()
                    if handle_vpn_permission(d):
                        print("VPN permission granted.")
                else:
                    time.sleep(1)  # Add a small delay between retries

                if d(resourceId="com.android.permissioncontroller:id/permission_deny_button").exists:
                    try:
                        d(resourceId="com.android.permissioncontroller:id/permission_deny_button").click()
                    except:
                        pass
                # Handle any pop-up messages (like "OK" confirmations)
                if d(text="OK").exists:
                    d(text="OK").click()

                # Check for additional dialogs and permissions
                if d.xpath('//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[3]/android.view.View[2]').exists:
                    try:
                        d.xpath('//androidx.compose.ui.platform.ComposeView/android.view.View[1]/android.view.View[3]/android.view.View[2]').click()
                    except:
                        pass
                    
                if "oxylabs" not in str(d.current_app):
                    d.app_start("io.oxylabs.proxymanager")
                    d.app_wait("io.oxylabs.proxymanager")
            except Exception as e:
                print(f"An error occurred while setting the proxy: {e}")
                time.sleep(1)  # Retry after a brief delay
                if connection_type == "TCP/IP":
                    reconnect_tcpip_device(udid)

        update_thread_status(udid, 'Proxy set', None, False, False, False, False, False)

        # Reconnect the device if it got disconnected during proxy setup
        if not d.info.get('screenOn'):
            print(f"Device {udid} might have disconnected. Attempting to reconnect...")
            if reconnect_tcpip_device(udid):
                print(f"Successfully reconnected to device {udid} after setting proxy.")
        ensure_screen_on(d)

        return True, ''

    except Exception as e:
        return False, f"Failed in proxy function: {str(e)}"

def solve_spotify_captcha(udid):
    """Detect and solve the Spotify reCAPTCHA challenge page using CapSolver.

    Works for any Spotify version: the challenge is served in a CustomTab
    (chromium/chrome) at challenge.spotify.com. We expose the device's
    devtools socket, find the challenge page over CDP, solve it with
    CapSolver and inject the token, then click the continue/verify button.
    Returns True if solved, False otherwise.
    """
    import urllib.request as _urlreq
    try:
        if not settings_capsolver_api_key:
            print("CapSolver API key not set")
            return False

        # expose the CustomTab devtools socket on the host
        subprocess.run([adb_path, '-s', udid, 'forward', 'tcp:9222', 'localabstract:chrome_devtools_remote'],
                       capture_output=True, timeout=15)
        subprocess.run([adb_path, '-s', udid, 'forward', 'tcp:9223', 'localabstract:chrome_devtools_remote'],
                       capture_output=True, timeout=15)

        def get_targets():
            try:
                with _urlreq.urlopen('http://127.0.0.1:9222/json/list', timeout=5) as r:
                    return json.loads(r.read().decode())
            except Exception:
                try:
                    with _urlreq.urlopen('http://127.0.0.1:9223/json/list', timeout=5) as r:
                        return json.loads(r.read().decode())
                except Exception:
                    return []

        def eval_js(ws_url, expr, msgid=1):
            ws = create_connection(ws_url, timeout=40)
            ws.send(json.dumps({'id': msgid, 'method': 'Runtime.evaluate',
                                'params': {'expression': expr, 'returnByValue': True, 'awaitPromise': True}}))
            while True:
                resp = json.loads(ws.recv())
                if resp.get('id') == msgid:
                    ws.close()
                    return resp.get('result', {}).get('result', {}).get('value')

        # wait for the challenge page
        ws_url = page_url = None
        for attempt in range(20):
            for t in get_targets():
                if 'challenge.spotify.com' in t.get('url', ''):
                    ws_url = t.get('webSocketDebuggerUrl')
                    page_url = t.get('url')
                    break
            if ws_url:
                break
            time.sleep(2)
        if not ws_url:
            print("challenge page not found over CDP")
            return False

        sitekey = '6LeO36obAAAAALSBZrY6RYM1hcAY7RLvpDDcJLy3'
        payload = {'clientKey': settings_capsolver_api_key,
                   'task': {'type': 'ReCaptchaV2EnterpriseTaskProxyLess',
                            'websiteURL': page_url, 'websiteKey': sitekey, 'isInvisible': False}}
        req = _urlreq.Request('https://api.capsolver.com/createTask',
                              data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        r = json.loads(_urlreq.urlopen(req, timeout=60).read().decode())
        if not r.get('taskId'):
            print("capsolver createTask failed:", json.dumps(r)[:200])
            return False
        task_id = r['taskId']

        token = None
        for i in range(60):
            time.sleep(5)
            get_req = _urlreq.Request('https://api.capsolver.com/getTaskResult',
                                      data=json.dumps({'clientKey': settings_capsolver_api_key, 'taskId': task_id}).encode(),
                                      headers={'Content-Type': 'application/json'})
            rr = json.loads(_urlreq.urlopen(get_req, timeout=60).read().decode())
            if rr.get('status') == 'ready':
                token = rr.get('solution', {}).get('gRecaptchaResponse')
                break
            if rr.get('status') == 'failed':
                print("capsolver failed:", json.dumps(rr)[:200])
                return False
        if not token:
            print("no token from capsolver")
            return False

        expr = ("(() => {"
                "  const tk = %s;"
                "  document.querySelectorAll('textarea[name=\"g-recaptcha-response\"], #g-recaptcha-response').forEach(t => { t.value = tk; });"
                "  let called = [];"
                "  if (typeof window.onChange === 'function') { try { window.onChange(tk); called.push('onChange'); } catch(e) { called.push('onChangeErr:'+e.message); } }"
                "  if (window.___grecaptcha_cfg) {"
                "    for (const cid in window.___grecaptcha_cfg.clients) {"
                "      const c = window.___grecaptcha_cfg.clients[cid];"
                "      const g = c.g && c.g.g;"
                "      if (g) { const cb = window[g.callback]; if (typeof cb === 'function') { try { cb(tk); called.push('cfg.cb:'+g.callback); } catch(e) { called.push('errcb:'+e.message); } } }"
                "    }"
                "  }"
                "  return called;"
                "})()") % json.dumps(token)
        inj = eval_js(ws_url, expr, 1)
        print("captcha injected:", json.dumps(inj))

        time.sleep(2)
        # click the verify / continue button on the challenge page
        click_expr = ("(() => {"
                      "  const btns = Array.from(document.querySelectorAll('button, input[type=button], [role=button]'));"
                      "  const txt = btns.find(b => /Verificar|Verify|Continuar|Continue/i.test((b.innerText||'').trim()));"
                      "  if (txt) { txt.click(); return txt.innerText; }"
                      "  return null;"
                      "})()")
        clicked = eval_js(ws_url, click_expr, 2)
        print("challenge button clicked:", json.dumps(clicked))
        return True
    except Exception as e:
        print(f"solve_spotify_captcha error: {str(e)}")
        return False


def spotify_login(d, account, udid=None):
    try:
        email, password = str(account).split(':')
        thread = 'Main'

        # --- live identification: detect version + infer UI profile ---
        spotify_version = get_device_spotify_version(udid) if udid else None
        if spotify_version:
            print(f"spotify_login: detected Spotify version {spotify_version} on {udid}")
        def ui(key):
            return spotify_ui('com.spotify.music', spotify_version, key)
        def ensure_ui_registered():
            """Dump the live screen and persist any inferred resource-ids."""
            try:
                if not udid:
                    return
                nodes = dump_live_nodes(udid, d=d)
                mapping = infer_spotify_ui_mapping(nodes, spotify_version)
                if mapping:
                    register_spotify_ui_version(spotify_version, mapping)
                    print(f"spotify_login: inferred UI mapping for {spotify_version}: {json.dumps(mapping)}")
            except Exception as e:
                print(f"ensure_ui_registered error: {e}")

        ensure_screen_on(d)
        d.implicitly_wait(5)
        try:
            d(text="Allow all cookies").click_exists(1)
        except:
            d(text="Allow all cookies").click_exists(1)

        time.sleep(5)
        ensure_ui_registered()
        if udid and _live_click_text(d, udid, ('log in', 'iniciar sesión', 'iniciar sesion', 'anmelden')):
            pass
        elif d(text="Log in").exists:
            d(text="Log in").click()
        elif d(text="Iniciar sesión").exists:
            d(text="Iniciar sesión").click()
        elif d(text="Anmelden").exists:
            d(text="Anmelden").click()
        else:
            d(resourceId=ui("buttons_container")).child(className='android.widget.Button', index=1).click()

        time.sleep(3)

        if udid and _live_click_text(d, udid, ('weiter mit email', 'continue with email', 'continuar con correo', 'continuar con email')):
            pass
        else:
            d(text='Weiter mit email').click_exists(1)
            d(text='Continue with email').click_exists(1)
            d(text='Continuar con correo').click_exists(1)
            d(text='Continuar con email').click_exists(1)
        d(resourceId="android:id/button1").click_exists(0.1)

        # identify the email field LIVE first (Compose-aware dump), then fall
        # back to the per-version resource-id.
        _email_typed = False
        if udid:
            _email_typed = _live_click_and_type(d, udid, 'email', email)
        if not _email_typed:
            try:
                found_email = d(resourceId=ui("username_text")).exists(timeout=15)
            except Exception as e:
                print(f"username_text exists() error: {e}")
                found_email = False
            if found_email:
                try:
                    d(resourceId=ui("username_text")).set_text(email)
                    _email_typed = True
                except Exception as e:
                    print(f"set_text email error: {e}")
            if not _email_typed:
                ensure_ui_registered()
                try:
                    d.shell(f"input text '{email}'")
                except Exception as e:
                    print(f"input text email error: {e}")
        sleep(0.7)

        _clicked_continue = False
        if udid and _live_click_text(d, udid, ('continuar', 'continue')):
            _clicked_continue = True
            sleep(2)
        if not _clicked_continue:
            if d(text="Continuar").exists(timeout=5) or d(text="Continue").exists(timeout=2) or d(resourceId=ui("continue_button")).exists(timeout=2):
                if d(text="Continuar").exists(timeout=1):
                    d(text="Continuar").click()
                elif d(text="Continue").exists(timeout=1):
                    d(text="Continue").click()
                else:
                    d(resourceId=ui("continue_button")).click()
                sleep(2)
        # if the app asks for an emailed code, fall back to password login
        _code_fallback_deadline = time.time() + 15
        _fell_back = False
        while time.time() < _code_fallback_deadline:
            if d(resourceId=ui("password_field")).exists(timeout=1) or d(resourceId=ui("password_text")).exists(timeout=1):
                break
            # click the 'log in with a password' link directly if visible
            if _click_spotify_password_fallback(d, udid=udid):
                _fell_back = True
                print("password link: clicked 'Iniciar sesión con contraseña' fallback")
                sleep(2)
                break
            if not _on_spotify_code_screen(d, udid=udid) and not _live_has_password_fallback(d, udid):
                break
            sleep(1)
        if _fell_back:
            sleep(1)
        _password_typed = False
        if udid:
            _password_typed = _live_click_and_type(d, udid, 'password', password)
        if not _password_typed:
            if d(resourceId=ui("password_field")).exists:
                try:
                    d(resourceId=ui("password_field")).set_text(password)
                    _password_typed = True
                except Exception as e:
                    print(f"set_text password_field error: {e}")
            if not _password_typed and d(resourceId=ui("password_text")).exists:
                try:
                    d(resourceId=ui("password_text")).set_text(password)
                    _password_typed = True
                except Exception as e:
                    print(f"set_text password_text error: {e}")
            if not _password_typed:
                ensure_ui_registered()
                try:
                    d.shell(f"input text '{password}'")
                except Exception as e:
                    print(f"input text password error: {e}")
        sleep(0.3)
        if udid and _live_click_text(d, udid, ('iniciar sesión', 'iniciar sesion', 'log in', 'anmelden')):
            pass
        elif d(text="Iniciar sesión").exists:
            d(text="Iniciar sesión").click()
        elif d(text="Log in").exists:
            d(text="Log in").click()
        elif d(text="Anmelden").exists:
            d(text="Anmelden").click()
        elif d(resourceId=ui("login_button")).exists:
            d(resourceId=ui("login_button")).click()
        else:
            d(resourceId=ui("login_button")).click_exists(1)

        time.sleep(5)
        d(resourceId="com.android.chrome:id/signin_fre_dismiss_button").click_exists(10)

        type = False
        invalid_creds = False
        d.implicitly_wait(0.1)
        _captcha_wait_deadline = time.time() + 600
        _loop_deadline = time.time() + 300
        _code_fallback_retries = 0
        _last_live_check = 0.0
        while type is False and time.time() < _loop_deadline:
            try:
                # live dump every ~3s: detect home (success) / wrong creds on any
                # Spotify version regardless of resource-id availability
                if udid and (time.time() - _last_live_check) >= 3:
                    _last_live_check = time.time()
                    if _live_home_screen(d, udid):
                        print("live check: home screen detected -> login OK")
                        invalid_creds = False
                        type = True
                        continue
                    if _live_login_error(d, udid):
                        print("live check: wrong credentials error detected")
                        invalid_creds = True
                        type = True
                        continue
            except Exception as _e:
                print(f"live check error: {_e}")
            try:
                cur = d.app_current()
                if str(cur.get('package', '')).startswith('com.android.chrome') or str(cur.get('package', '')).startswith('com.android.chromium'):
                    print(f"reCAPTCHA CustomTab detected: {cur.get('package')} - waiting for user to solve it manually")
                    if udid:
                        # manual captcha resolution: wait until the user solves
                        # the challenge and the CustomTab closes (back to Spotify)
                        while time.time() < _captcha_wait_deadline:
                            time.sleep(3)
                            try:
                                _cur = d.app_current()
                                _pkg = str(_cur.get('package', ''))
                                if not (_pkg.startswith('com.android.chrome') or _pkg.startswith('com.android.chromium')):
                                    print("CustomTab closed - captcha solved manually, continuing")
                                    break
                            except:
                                pass
                        else:
                            print("captcha wait deadline reached, continuing anyway")
                    continue
            except:
                pass
            try:
                if str(d(resourceId=ui("login_error_message")).get_text()).lower().__contains__(
                        'mail'):
                    print(f"Invalid case 1: {d(resourceId=ui('login_error_message')).get_text()}")
                    invalid_creds = True
                    type = True
            except:
                pass

            try:
                if str(d(resourceId=ui("login_error_message")).get_text()).strip() == "":
                    pass
                elif str(d(resourceId=ui("login_error_message")).get_text()).strip() == "None":
                    pass
                elif d(resourceId=ui("login_error_message")).get_text() is None:
                    pass
                else:
                    print(f"Invalid case 2: {d(resourceId=ui('login_error_message')).get_text()}")
                    invalid_creds = True
                    type = True
            except:
                pass
            try:
                if d(resourceId=ui("design_bottom_sheet")).exists:
                    if d(resourceId=ui("secondary_button"), index=5).exists:
                        invalid_creds = "Proxy"
                        type = True
                if d(className="android.widget.ImageView", index=0).exists:
                    pass
                else:
                    print(f"Invalid case 3")
                    invalid_creds = False
                    type = True
            except:
                pass

            try:
                if str(d(resourceId=ui("body")).get_text()).lower().__contains__("pass"):
                    print(f"Invalid case 4")
                    invalid_creds = False
                    type = True
                elif str(d(resourceId=ui("body")).get_text()).__contains__("?"):
                    print(f"proxy issue on login")
                    invalid_creds = "Proxy"
                    type = True
            except:
                pass

            try:
                if _on_spotify_code_screen(d, udid=udid) or _live_has_password_fallback(d, udid):
                    print(f"code screen detected, trying password fallback")
                    if _code_fallback_retries >= 3:
                        print(f"code screen: password accepted, email code requested")
                        invalid_creds = "codigo"
                        type = True
                    elif _click_spotify_password_fallback(d, udid=udid):
                        _code_fallback_retries += 1
                        sleep(2)
                        try:
                            _pw_typed = False
                            if udid:
                                _pw_typed = _live_click_and_type(d, udid, 'password', password)
                            if not _pw_typed:
                                if d(resourceId=ui("password_field")).exists:
                                    d(resourceId=ui("password_field")).set_text(password)
                                elif d(resourceId=ui("password_text")).exists:
                                    d(resourceId=ui("password_text")).set_text(password)
                                else:
                                    d.shell(f"input text '{password}'")
                            sleep(0.3)
                            if udid and _live_click_text(d, udid, ('iniciar sesión', 'iniciar sesion', 'log in', 'anmelden')):
                                pass
                            elif d(text="Iniciar sesión").exists:
                                d(text="Iniciar sesión").click()
                            elif d(text="Log in").exists:
                                d(text="Log in").click()
                            elif d(text="Anmelden").exists:
                                d(text="Anmelden").click()
                            elif d(resourceId=ui("login_button")).exists:
                                d(resourceId=ui("login_button")).click()
                        except Exception as e:
                            print(f"password fallback retry error: {e}")
                        time.sleep(4)
                        continue
                    else:
                        print(f"code screen: password accepted, email code requested")
                        invalid_creds = "codigo"
                        type = True
            except:
                pass

            try:
                if d(textContains="combinación de correo y contraseña es incorrecta").exists(timeout=1):
                    print(f"wrong credentials")
                    invalid_creds = True
                    type = True
            except:
                pass

            try:
                if d(resourceId=ui("username_text")).exists:
                    type = None
            except:
                pass

            try:
                if d(resourceId=ui("home_tab")).exists:
                    invalid_creds = False
                    type = True
            except:
                pass

            try:
                if d(resourceId=ui("later_button")).exists:
                    invalid_creds = False
                    type = True
            except:
                pass

            try:
                if d.xpath('//*[@resource-id="android:id/hearty_service_autofill_save"]').exists:
                    invalid_creds = False
                    type = True
            except:
                pass

            try:
                if d(resourceId=ui("update_payment_button")).exists:
                    invalid_creds = "X"
                    type = True
            except:
                pass
            try:
                if d(resourceId=ui("picker_recycler_view")).exists:
                    invalid_creds = "no-reg"
                    type = True
            except:
                pass

            try:
                if d(resourceId=ui("pickerTitle")).exists:
                    invalid_creds = "no-reg"
                    type = True
            except:
                pass

            try:
                if d.xpath(
                        '//hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/androidx.recyclerview.widget.RecyclerView/android.view.ViewGroup[3]/android.widget.ImageView').exists:
                    invalid_creds = "no-reg"
                    type = True
            except:
                pass
            try:
                if d(resourceId=ui("confirm_button")).exists:
                    invalid_creds = False
                    type = True
            except:
                pass

            try:
                if d(resourceId=ui("body")).exists:
                    if str(d(resourceId=ui("body")).get_text()).__contains__("14"):
                        d(resourceId=ui("button_positive")).click()
                        invalid_creds = "14"
                        type = True
            except:
                pass


            #d(resourceId=ui("button_positive")).click_exists(0.1)

        if invalid_creds == "Proxy":
            add_log("EXC.", thread, "Proxy to slow/not working!")
            return False, "Proxy to slow/not working!"

        elif invalid_creds == False and type is False and time.time() >= _loop_deadline:
            add_log("EXC.", thread, "Login timed out (stuck on a screen).")
            return False, "Login timed out."

        elif invalid_creds == "X":
            add_log("ERR.", thread, str("Account: " + email + ":" + password + ", needs payment updated."))
            return False, str("Account: " + email + ":" + password + ", needs payment updated.")

        elif invalid_creds == "offline":
            if str(d(resourceId=ui("body")).get_text()).lower().__contains__('mail'):
                add_log("INFO", thread, str("Failed to login with: " + email + ":" + password + ", credentials wrong."))
                return False,  str("Failed to login with: " + email + ":" + password + ", credentials wrong.")

            else:
                add_log("EXC.", thread, str("Seems like device isn't connected to the Internet."))
                return False, str("Seems like device isn't connected to the Internet.")

        elif invalid_creds == "14":
            add_log("ERR.", thread, str("Failed to login with: " + email + ":" + password + ", You can only use Spotify abroad for 14 days. Update your location at Spotify.com to continue using it."))
            return False, str("Failed to login with: " + email + ":" + password + ", You can only use Spotify abroad for 14 days. Update your location at Spotify.com to continue using it.")

        elif invalid_creds == True:
            add_log("ERR.", thread, str("Failed to login with: " + email + ":" + password + ", credentials wrong."))
            return False, str("Failed to login with: " + email + ":" + password + ", credentials wrong.")

        elif invalid_creds == "codigo":
            add_log("INFO", thread, str("Login requires email verification code for: " + email))
            return False, str("Login requires email verification code for: " + email)

        elif invalid_creds == "no-reg":
            d(resourceId=ui("pickerTitle")).wait(30)
            sleep(3)
            if d.xpath("//android.view.ViewGroup[@index='5']").exists:
                d.xpath("//android.view.ViewGroup[@index='5']").click_exists(10)
                d.xpath("//android.view.ViewGroup[@index='4']").click_exists(10)
                d.xpath("//android.view.ViewGroup[@index='3']").click_exists(10)
                d(resourceId=ui("secondaryActionButton")).click_exists(1)
            else:
                d(resourceId=ui("decline")).click_exists(1)
                sleep(3)
                d.xpath(
                    f'//*[@resource-id="{ui("picker_recycler_view")}"]/android.view.ViewGroup[3]').click()
                d.xpath(
                    f'//*[@resource-id="{ui("picker_recycler_view")}"]/android.view.ViewGroup[2]').click()
                d.xpath(
                    f'//*[@resource-id="{ui("picker_recycler_view")}"]/android.view.ViewGroup[1]').click()
                d(resourceId=ui("secondaryActionButton")).click_exists(1)
            d(resourceId=ui("actionButton")).click_exists(1)

            d.xpath(
                '//hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[1]/android.widget.FrameLayout[1]/android.webkit.WebView/android.view.View/android.view.View/android.view.View[2]/android.view.View/android.view.View[2]/android.widget.Button').click_exists(
                1)

            d.xpath(
                '//hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[1]/android.widget.FrameLayout[2]/android.webkit.WebView/android.view.View/android.view.View/android.view.View[2]/android.view.View/android.view.View[2]/android.widget.Button').click_exists(
                1)

            d(resourceId=ui("contextual_audio_secondary_btn")).click_exists(1)
            d(resourceId=ui("secondary_button")).click_exists(1)
            sleep(5)

        d.implicitly_wait(1)
        if d.xpath('//*[@resource-id="android:id/hearty_service_autofill_save"]').exists:
            d(resourceId="android:id/button2").click()
        d(resourceId=ui("later_button")).click_exists(1)

        d(resourceId=ui("confirm_button")).click_exists(1)

        d.implicitly_wait(1)
        if d.xpath('//*[@resource-id="android:id/hearty_service_autofill_save"]').exists:
            d(resourceId="android:id/button2").click()

        if d(resourceId=ui("update_payment_button")).exists:
            add_log("INFO", thread, "Account has failed sub.")
            return False, "Account has failed sub."

        if d(resourceId=ui("device_name")).exists:
            add_log("INFO", thread, "Account is being used by another user!")
            return False, "Account is being used by another user!"

        d(resourceId=ui("dismiss_text")).click_exists(1)

        d(resourceId=ui("screensaver_ad_footer")).click_exists(1)
        d.implicitly_wait(1)
        if d.xpath('//*[@resource-id="android:id/hearty_service_autofill_save"]').exists:
            d(resourceId="android:id/button2").click()

        d.xpath(
            f'//*[@resource-id="{ui("webview_container")}"]/android.webkit.WebView[1]/android.webkit.WebView[1]/android.view.View[1]/android.view.View[1]/android.view.View[1]').click_exists(1)

        d(resourceId=ui("later_button")).click_exists(1)
        d(resourceId=ui("home_tab")).wait(20)
        d.implicitly_wait(20)

        if not d.xpath(f'//*[@resource-id="{ui("navigation_bar")}"]/android.widget.LinearLayout[1]').exists:
            add_log("ERR.", thread, str("Failed to login with: " + email + ":" + password + ", credentials wrong."))
            return False, str("Failed to login with: " + email + ":" + password + ", credentials wrong.")

        d.implicitly_wait(10)
        if d(resourceId=ui("premium_tab")).exists:
            account_type = "Free"
        elif d(descriptionContains='Premium, Tab').exists:
            account_type = "Free"
        else:
            account_type = "Premium"
            d.implicitly_wait(5)
            try:
                d(className='android.widget.ImageButton', index=2).click()
                d.xpath('//*[@resource-id="android:id/list"]/android.widget.FrameLayout[1]').click()
                account_type_text = d.xpath(f'//*[@resource-id="{ui("container")}"]/android.view.ViewGroup[1]/android.widget.TextView').get_text()  # get sub | Premium Duo | Premium Family | Free plan | Premium Individual | Premium Student
                if 'duo' in str(account_type_text).lower():
                    account_type = "premium duo"
                elif 'family' in str(account_type_text).lower():
                    account_type = "premium family"
                elif 'individual' in str(account_type_text).lower():
                    account_type = "premium individual"
                elif 'student' in str(account_type_text).lower():
                    account_type = "premium student"
                elif 'trial' in str(account_type_text).lower():
                    account_type = "premium trial"
                else:
                    account_type = "others"
            except:
                try:
                    d(resourceId=ui("faceheader")).click()
                    d.xpath(f'//*[@resource-id="{ui("sidedrawer_recyclerview")}"]/android.view.ViewGroup[3]').click()
                    d.xpath(f'//*[@resource-id="{ui("compose_view")}"]/android.view.View[1]/android.view.View[1]/android.view.View[1]/android.view.View[1]').click()
                    account_type_text =d.xpath(f'//*[@resource-id="{ui("compose_view")}"]/android.view.View[1]/android.view.View[1]/android.view.View[1]/android.view.View[5]/android.widget.TextView[1]').get_text()
                    if 'duo' in str(account_type_text).lower():
                        account_type = "premium duo"
                    elif 'family' in str(account_type_text).lower():
                        account_type = "premium family"
                    elif 'individual' in str(account_type_text).lower():
                        account_type = "premium individual"
                    elif 'student' in str(account_type_text).lower():
                        account_type = "premium student"
                    elif 'trial' in str(account_type_text).lower():
                        account_type = "premium trial"
                    else:
                        account_type = "others"
                except:
                    pass


        add_log("SUCC", thread, str("Successfully logged in with: " + account + " | " + account_type))
        '''
                if random.randrange(100) < int(config_only_use_premiums_perc):
            if str(account_type) == "Free":
                add_log("INFO", thread, str("Logging out now because account type is " + account_type))
                return False, account_type, 0, Account, links_array'''
        return True, account_type
    except Exception as e:
        add_log("ERR.", 'Main', "Fail in Start app Function: " + str(e))
        return False, "Fail in Start app Function: " + str(e)


def perform_device_action(udid, action, account, proxy):
    try:
        device = Device.query.filter_by(udid=udid).first()
        if device is None:
            # The device may not be registered yet (e.g. batch login from the
            # frontend passes a serial not present in the DB). Register it on
            # the fly so the action can complete and the result is persisted.
            device = Device(
                udid=udid,
                manufacturer=get_device_manufacturer(udid),
                model=get_device_model(udid),
                hardware_id=get_device_hardware_id(udid),
                android_version=get_device_android_version(udid),
                spotify_version=get_device_spotify_version(udid),
                bindedAccount="/",
                bindedProxy="/",
                accountType="/",
                logged_in=False,
                connected=True,
                local_code=str(uuid.uuid4())[:8],
            )
            db.session.add(device)
            db.session.commit()
            print(f"perform_device_action: auto-registered device {udid}")
        d = ua.connect(udid)
        ensure_screen_on(d)
        d.set_input_ime(True)
        freeze_rotation_port(d)
        connection_type = "TCP/IP" if is_tcpip_device(udid) else "USB"
        try:
            d.app_info("io.oxylabs.proxymanager")
        except Exception as e:
            if 'package "io.oxylabs.proxymanager" not found' in str(e):
                add_log("ERR.", udid, "Oxy Proxy Manager apk is not installed, please install it manually.")

        try:
            d.app_info("com.spotify.music")
        except Exception as e:
            if 'package "com.spotify.music" not found' in str(e):
                add_log("ERR.", udid, "Spotify apk is not installed, please install it manually.")
        setProxy = True
        print(str(proxy).lower().rstrip())
        if str(proxy).lower().rstrip() == '/':
            setProxy = False
        elif str(proxy).lower().rstrip() == '':
            setProxy = False
        elif str(proxy).lower().rstrip() == 'none':
            setProxy = False
        if setProxy is True:
            proxy_set = False
            while not proxy_set:
                d.app_clear("io.oxylabs.proxymanager")
                if connection_type == "TCP/IP":
                    reconnect_tcpip_device(udid)
                freeze_rotation_port(d)
                d.app_start("io.oxylabs.proxymanager", stop=True, use_monkey=True)
                d.app_wait("io.oxylabs.proxymanager")
                freeze_rotation_port(d)
                proxy_set, proxy_set_msg = set_proxy_by_oxyproxymanager(d, udid, proxy, connection_type)
                if proxy_set is False:
                    print(proxy_set_msg)
        d(resourceId='android:id/button1').click_exists(1)
        d.app_stop("com.spotify.music")
        if action == 'login':
            d.app_clear("com.spotify.music")
        d.app_start("com.spotify.music", ".MainActivity")
        if action == 'login':
            logged_in, msg = spotify_login(d, account, udid=udid)
            device.logged_in = logged_in

            if logged_in is True:
                print(f"login success {msg}")
                device.bindedAccount = account
                device.bindedProxy = proxy
                device.accountType = msg
                db.session.commit()
                return {'message': f'Successfully logged in on Device {udid} with account {account} and proxy {proxy} | Account type: {msg}'}, 200
            else:
                print(f"login not successfull {msg}")
                db.session.commit()
                return {'message': f'Failed to login on Device {udid} logged in with account {account} and proxy {proxy} | Reason: {msg}'}, 400

        elif action == 'check':
            d.implicitly_wait(1)
            still_logged_in = True
            for i in range(30):
                if d(resourceId="com.spotify.music:id/home_page_recycler").exists:
                    print("Account still logged in")
                    break
                if d(resourceId="com.spotify.music:id/spotify_logo_no_text").exists:
                    print("Account logged out")
                    still_logged_in = False
                    break
            device.logged_in = still_logged_in

            if still_logged_in is True:
                d.implicitly_wait(10)
                if d(resourceId="com.spotify.music:id/premium_tab").exists:
                    account_type = "Free"
                else:
                    account_type = "Premium"
                    try:
                        d(className='android.widget.ImageButton', index=2).click()
                        d.xpath('//*[@resource-id="android:id/list"]/android.widget.FrameLayout[1]').click()
                        account_type_text = d(className='android.widget.TextView', index=1).get_text()  # get sub | Premium Duo | Premium Family | Free plan | Premium Individual | Premium Student
                        if 'duo' in str(account_type_text).lower():
                            account_type = "Premium Duo"
                        elif 'family' in str(account_type_text).lower():
                            account_type = "Premium Family"
                        elif 'individual' in str(account_type_text).lower():
                            account_type = "Premium Individual"
                        elif 'student' in str(account_type_text).lower():
                            account_type = "Premium Student"
                        elif 'trial' in str(account_type_text).lower():
                            account_type = "Premium Trial"
                        else:
                            account_type = "Others"
                    except:
                        pass
                device.accountType = account_type
                db.session.commit()
                return {'message': f'Account: {account} on device {udid} is still logged in!'}, 200
            else:
                device.bindedAccount = '/'
                device.bindedProxy = '/'
                device.accountType = '/'
                db.session.commit()
                return {'message': f'Account: {account} is logged out on device!'}, 400

        else:
            return {'message': f'Invalid action: {action}'}, 400
    except Exception as e:
        return {'message': f'Failed: {str(e)}'}, 400


def _bundle_app_dir():
    """Locate the app directory in a frozen (PyInstaller) bundle."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if os.path.basename(exe_dir) == 'api':
            return os.path.dirname(exe_dir)
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))


def _find_scrcpy():
    """Locate the scrcpy binary (bare name, .exe, or .bat) in known locations."""
    candidates = []
    base_dirs = [project_dir, _bundle_app_dir()]
    for base in base_dirs:
        for sub in ('Files', 'Files/Adb', 'Adb', ''):
            candidates.append(os.path.join(base, sub, 'scrcpy'))
            candidates.append(os.path.join(base, sub, 'scrcpy.exe'))
            candidates.append(os.path.join(base, sub, 'scrcpy.bat'))
    for c in candidates:
        try:
            if os.path.isfile(c):
                return c
        except Exception:
            pass
    # last resort: PATH
    try:
        import shutil
        return shutil.which('scrcpy')
    except Exception:
        return None


def _launch_scrcpy(udid):
    """Open a scrcpy mirror window of the device (best-effort, never throws)."""
    try:
        scrcpy_bin = _find_scrcpy()
        if not scrcpy_bin:
            print("scrcpy not found; skipping live view")
            return None
        proc = subprocess.Popen(
            [scrcpy_bin, '-s', udid, '--stay-awake'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        )
        return proc
    except Exception as e:
        print(f"scrcpy launch error: {e}")
        return None


@app.route('/device/<action>', methods=['POST'])
@require_token
def device_action(action):
    # Extracting data from the request body
    data = request.json
    udid = data.get('udid')
    launchScrcpy = data.get('launchScrcpy')
    if action == 'login':
        account = data.get('bindedAccount')
        proxy = data.get('bindedProxy')
    else:
        device = Device.query.filter_by(udid=udid).first()
        account = device.bindedAccount
        proxy = device.bindedProxy

    if not udid:
        return jsonify({"error": "UDID is required"}), 400
    _scrcpy_proc = None
    if str(launchScrcpy).lower() == 'true':
        _scrcpy_proc = _launch_scrcpy(udid)
        if _scrcpy_proc:
            try:
                _scrcpy_proc.wait(timeout=5)
            except Exception:
                pass

    response, status_code = perform_device_action(udid, action, account, proxy)
    if _scrcpy_proc:
        try:
            _scrcpy_proc.terminate()
        except Exception:
            pass

    return jsonify(response), status_code


PATCH_LOCK = threading.Lock()


def _list_adb_serial():
    try:
        r = subprocess.run([adb_path, 'devices'], capture_output=True, text=True,
                           startupinfo=startupinfo, timeout=30)
        serials = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith('List of devices') or '\t' not in line:
                continue
            serial, state = line.split('\t', 1)
            if state.strip() == 'device':
                serials.append(serial.strip())
        # Prefer real devices over emulators: an emulator often still has an
        # already-patched Spotify installed, so pulling from it would re-patch
        # an already-patched APK (which is a no-op and falls back to baksmali).
        serials.sort(key=lambda s: s.startswith('emulator-'))
        return serials
    except Exception:
        return []


def run_spotify_patch():
    try:
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            base_dir = os.path.dirname(exe_dir) if os.path.basename(exe_dir) == 'api' else exe_dir
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        tools_dir = os.path.join(base_dir, 'Tools')
        patcher_file = os.path.join(base_dir, 'SpotifyPatcher.py')
        add_log("INFO", "Spotifix", f"Fix screen iniciado. Tools: {tools_dir}")
        if not os.path.isfile(patcher_file):
            add_log("ERR.", "Spotifix", "No se encontró el módulo del fix screen.")
            return
        if not os.path.isdir(tools_dir):
            add_log("ERR.", "Spotifix", f"No se encontró la carpeta Tools en {tools_dir}")
            return
        import importlib.util
        spec = importlib.util.spec_from_file_location('SpotifyPatcher', patcher_file)
        patcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(patcher)

        serials = _list_adb_serial()
        if not serials:
            add_log("ERR.", "Spotifix", "No se detectaron dispositivos ADB conectados.")
            return
        add_log("INFO", "Spotifix", f"Dispositivos detectados: {len(serials)}")

        patch_root = os.path.join(files, 'SpotifyPatch')
        os.makedirs(patch_root, exist_ok=True)
        patched_apk = os.path.join(patch_root, 'spotify_patched.apk')
        base_apk = None

        # 1) Pull the base APK plus any split APKs. Play Store bundle installs
        #    put the native libs in split_config.<abi>.apk; a base-only pull
        #    produced an APK with no .so that crashed on open
        #    ('liborbit-jni-spotify.so not found').
        splits_dir = os.path.join(patch_root, 'splits')
        source_serial = None
        for serial in serials:
            try:
                r = subprocess.run([adb_path, '-s', serial, 'shell', 'pm', 'path', 'com.spotify.music'],
                                   capture_output=True, text=True, startupinfo=startupinfo, timeout=60)
                paths = [l.strip() for l in r.stdout.splitlines() if l.strip().startswith('package:')]
                if not paths:
                    add_log("WARN", serial, "Spotify no está instalado en este dispositivo, se omite como origen.")
                    continue
                os.makedirs(splits_dir, exist_ok=True)
                device_apks = [p[len('package:'):].strip() for p in paths]
                base_apk = os.path.join(patch_root, 'spotify_base.apk')
                split_apks = []
                for i, device_apk in enumerate(device_apks):
                    local = base_apk if i == 0 else os.path.join(splits_dir, os.path.basename(device_apk))
                    add_log("INFO", serial, f"Descargando APK de Spotify desde el dispositivo: {device_apk}")
                    subprocess.run([adb_path, '-s', serial, 'pull', device_apk, local],
                                   capture_output=True, text=True, startupinfo=startupinfo, timeout=300)
                    if i > 0 and os.path.isfile(local):
                        split_apks.append(local)
                if os.path.isfile(base_apk):
                    source_serial = serial
                    add_log("INFO", serial, f"APKs obtenidos: 1 base + {len(split_apks)} split(s).")
                    break
            except Exception as e:
                add_log("WARN", serial, f"No se pudo obtener el APK: {e}")

        if not base_apk or not os.path.isfile(base_apk):
            add_log("ERR.", "Spotifix", "No se pudo obtener un APK de Spotify instalado. Instala Spotify en algún dispositivo y reintenta.")
            return

        import hashlib
        with open(base_apk, 'rb') as fh:
            base_sha = hashlib.sha256(fh.read()).hexdigest()[:16]

        if split_apks:
            # Instalación por splits (bundle de Play Store). El FLAG_SECURE vive
            # en el dex del base; los splits llevan libs y recursos (p. ej.
            # split_config.xxhdpi contiene el drawable 'launcher_screen'). Se
            # modifica solo el base y se firman base + splits con el mismo
            # keystore para reinstalarlos juntos con install-multiple. Unir solo
            # las libs en un APK único eliminaba los recursos de los splits de
            # configuración y Spotify crasheaba (Resources$NotFoundException).
            patched_base = os.path.join(patch_root, f'spotify_patched_{base_sha}.apk')
            if os.path.isfile(patched_base):
                add_log("INFO", "Spotifix", "Fix screen ya aplicado para esta versión, se reutiliza.")
            else:
                add_log("INFO", "Spotifix", "Aplicando fix screen a Spotify (quitar restricción de captura). Tarda unos minutos...")
                try:
                    ok, msg = patcher.patch_apk(base_apk, patched_base, tools_dir, os.path.join(patch_root, 'work'))
                    if not ok:
                        add_log("ERR.", "Spotifix", f"Fallo al aplicar fix screen: {msg}")
                        return
                    add_log("INFO", "Spotifix", f"Fix screen aplicado correctamente: {msg}")
                except Exception as e:
                    add_log("ERR.", "Spotifix", f"Error al aplicar fix screen: {e}")
                    return
            patched_splits = []
            for i, sp in enumerate(split_apks):
                out = os.path.join(patch_root, f'spotify_patched_{base_sha}.split{i}.apk')
                try:
                    ok, msg = patcher.resign_apk(sp, out, tools_dir, os.path.join(patch_root, 'work'))
                except Exception as e:
                    ok, msg = False, repr(e)
                if not ok:
                    add_log("ERR.", "Spotifix", f"Fallo al firmar split {os.path.basename(sp)}: {msg}")
                    return
                patched_splits.append(out)
            install_files = [patched_base] + patched_splits
        else:
            # APK único (universal): unir splits es no-op; se modifica y se instala.
            try:
                abi = ''
                if source_serial:
                    r = subprocess.run([adb_path, '-s', source_serial, 'shell', 'getprop', 'ro.product.cpu.abi'],
                                       capture_output=True, text=True, startupinfo=startupinfo, timeout=30)
                    abi = (r.stdout or '').strip()
                merged_apk = os.path.join(patch_root, 'spotify_base_merged.apk')
                ok, msg = patcher.merge_split_libs(base_apk, split_apks, abi, merged_apk,
                                                   os.path.join(patch_root, 'work'))
                if not ok:
                    add_log("ERR.", "Spotifix", f"Fallo al fusionar splits: {msg}")
                    return
                if split_apks:
                    add_log("INFO", "Spotifix", f"Fusión de splits: {msg}")
                base_apk = merged_apk
            except Exception as e:
                add_log("ERR.", "Spotifix", f"Error al fusionar splits: {e}")
                return
            patched_apk = os.path.join(patch_root, f'spotify_patched_{base_sha}.apk')
            if os.path.isfile(patched_apk):
                add_log("INFO", "Spotifix", "Fix screen ya aplicado para esta versión, se reutiliza.")
            else:
                add_log("INFO", "Spotifix", "Aplicando fix screen a Spotify (quitar restricción de captura). Tarda unos minutos...")
                try:
                    ok, msg = patcher.patch_apk(base_apk, patched_apk, tools_dir, os.path.join(patch_root, 'work'))
                    if not ok:
                        add_log("ERR.", "Spotifix", f"Fallo al aplicar fix screen: {msg}")
                        return
                    add_log("INFO", "Spotifix", f"Fix screen aplicado correctamente: {msg}")
                except Exception as e:
                    add_log("ERR.", "Spotifix", f"Error al aplicar fix screen: {e}")
                    return
            install_files = [patched_apk]

        # 3) Reinstalar en todos los dispositivos.
        for serial in serials:
            try:
                add_log("INFO", serial, "Deteniendo Spotify antes de reinstalar...")
                subprocess.run([adb_path, '-s', serial, 'shell', 'am', 'force-stop', 'com.spotify.music'],
                               capture_output=True, text=True, startupinfo=startupinfo, timeout=60)
                add_log("INFO", serial, "Desinstalando Spotify original...")
                subprocess.run([adb_path, '-s', serial, 'uninstall', 'com.spotify.music'],
                               capture_output=True, text=True, startupinfo=startupinfo, timeout=120)
                add_log("INFO", serial, "Instalando Spotify con fix screen (sin restricción de captura)...")
                r = subprocess.run([adb_path, '-s', serial, 'install-multiple'] + install_files,
                                   capture_output=True, text=True, startupinfo=startupinfo, timeout=600)
                if r.returncode != 0 or 'Success' not in r.stdout:
                    add_log("ERR.", serial, f"Fallo al instalar: {(r.stdout or r.stderr)[-300:]}")
                    continue
                add_log("INFO", serial, "Spotify con fix screen instalado correctamente.")
                subprocess.Popen([adb_path, '-s', serial, 'shell', 'am', 'start', '-n', 'com.spotify.music/.MainActivity'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                add_log("ERR.", serial, f"Error al reinstalar: {e}")
        add_log("INFO", "Spotifix", "Fix screen finalizado.")
    except Exception as e:
        add_log("ERR.", "Spotifix", f"Error inesperado al aplicar fix screen: {e}")


@app.route('/patch_spotify', methods=['POST'])
@require_token
def patch_spotify():
    if not PATCH_LOCK.acquire(blocking=False):
        return jsonify({'message': 'Ya hay un fix screen de Spotify en curso. Espera a que termine.'}), 409
    t = threading.Thread(target=_run_spotify_patch_guarded, daemon=True)
    t.start()
    return jsonify({'message': 'Fix screen de Spotify iniciado en segundo plano. Puede tardar unos minutos, mira la consola.'}), 200


def _run_spotify_patch_guarded():
    try:
        run_spotify_patch()
    finally:
        PATCH_LOCK.release()

def get_time():
    t = time.localtime()
    return time.strftime("%H:%M:%S", t)


COLORS = {
    "white": Fore.WHITE,
    "magenta": Fore.MAGENTA,
    "light_green": Fore.LIGHTGREEN_EX,
    "dark_green": Fore.GREEN,
    "green": Fore.GREEN,
    "light_red": Fore.LIGHTRED_EX,
    "dark_red": Fore.RED,
    "red": Fore.RED,
    "yellow": Fore.YELLOW,
    "blue": Fore.LIGHTBLUE_EX,
    "gray": Fore.LIGHTBLACK_EX,
}


def print_log(type, color, thread, message):
    current_time = datetime.now().strftime("[%H:%M:%S]")
    color_code = COLORS.get(color.lower(), Fore.WHITE)
    thread_str = thread
    add_log(type, thread_str, message)
    #print(f"{current_time}|Thread {thread_str} {color_code} [{type}] {Fore.WHITE} - {message}")


def send_discord_webhook(interval, url):
    while True:
        try:
            global previous_streams_per_month
            global current_streams_per_month
            global worker_devices_connected
            global worker_successful_logins
            global worker_unsuccessful_logins
            global worker_streams_done
            global worker_streams_done_spotify, worker_streams_done_tidal, worker_streams_done_apple
            global worker_song_likes
            global worker_album_likes
            global worker_follows_done
            global worker_bot_errors
            cpu_usage = psutil.cpu_percent(1)
            ram_usage = psutil.virtual_memory()[2]
            elapsed_time = time.time() - start_time
            streams_per_second = worker_streams_done / elapsed_time if elapsed_time > 0 else 0
            streams_per_hour = streams_per_second * 3600
            streams_per_day = streams_per_hour * 24
            streams_per_month = streams_per_day * 30

            if previous_streams_per_month is not None:
                if streams_per_month > previous_streams_per_month:
                    trend_emoji = "📈"  # Up
                elif streams_per_month < previous_streams_per_month:
                    trend_emoji = "📉"  # Down
                else:
                    trend_emoji = "⚖️"  # Steady
            else:
                trend_emoji = "🔄"  # Initial value

            previous_streams_per_month = current_streams_per_month
            current_streams_per_month = streams_per_month

            payload = {
                "content": "",
                "tts": False,
                "embeds": [
                    {
                        "id": 10674342,
                        "description": f"**Machine Name:** {config_webhook_name} \n[CPU: {cpu_usage}% | RAM {ram_usage}%]",
                        "color": 6313836,
                        "fields": [
                            {
                                "id": 564153579,
                                "name": "Devices Connected:",
                                "value": str(worker_devices_connected),
                                "inline": True
                            },
                            {
                                "id": 445057359,
                                "name": "Successful Logins:",
                                "value": str(worker_successful_logins),
                                "inline": True
                            },
                            {
                                "id": 955958044,
                                "name": "Unsuccessful Logins:",
                                "value": str(worker_unsuccessful_logins),
                                "inline": True
                            },
                            {
                            "id": 53898218,
                                "name": "Streams (Total):",
                                "value": str(worker_streams_done),
                                "inline": True
                            },
                            {
                            "id": 53898219,
                                "name": "└ Spotify:",
                                "value": str(worker_streams_done_spotify),
                                "inline": True
                            },
                            {
                            "id": 53898220,
                                "name": "└ Tidal:",
                                "value": str(worker_streams_done_tidal),
                                "inline": True
                            },
                            {
                            "id": 53898221,
                                "name": "└ Apple Music:",
                                "value": str(worker_streams_done_apple),
                                "inline": True
                            },
                            {
                                "id": 711494525,
                                "name": "Song Likes:",
                                "value": str(worker_song_likes),
                                "inline": True
                            },
                            {
                                "id": 970976981,
                                "name": "Album Likes:",
                                "value": str(worker_album_likes),
                                "inline": True
                            },
                            {
                                "id": 513764591,
                                "name": "Followers:",
                                "value": str(worker_follows_done),
                                "inline": True
                            },
                            {
                                "id": 17774328,
                                "name": "Errors:",
                                "value": str(worker_bot_errors),
                                "inline": True
                            },
                            {
                                "id": 970976989,
                                "name": "Time running:",
                                "value": get_running_time(),
                                "inline": True
                            },
                            {
                                "id": 7793137,
                                "name": "Streams Per Hour:",
                                "value": f"{streams_per_hour:,.0f}".replace(',', '.'),
                                "inline": True
                            },
                            {
                                "id": 7793138,
                                "name": "Streams Per Day:",
                                "value": f"{streams_per_day:,.0f}".replace(',', '.'),
                                "inline": True
                            },
                            {
                                "id": 7793139,
                                "name": "Streams Per Month:",
                                "value": f"{streams_per_month:,.0f}".replace(',', '.'),
                                "inline": True
                            },
                            {
                                "id": "stream_trend",
                                "name": "Streaming Trend",
                                "value": trend_emoji,
                                "inline": True
                            }
                        ],
                        "footer": {
                            "text": "Spotifix 4.0.0"
                        }
                    }
                ],
                "components": [],
                "actions": {},
                "username": "Spotifix"
            }
            headers = {
                'Content-Type': 'application/json'
            }
            requests.post(url, headers=headers, data=json.dumps(payload))
            time.sleep(interval * 60)  # Convert interval from minutes to seconds
        except:
            add_log('ERR.', 'Main', "Failed to send webhook")


def update_thread_status(udid, status=None, proxy=None, increment_logins=False, increment_streams=False,
                         increment_likes=False, increment_follows=False, increment_errors=False, session_time=None):
    global worker_threads
    global worker_successful_logins
    global worker_streams_done
    global worker_song_likes
    global worker_follows_done
    global worker_bot_errors

    if udid in worker_threads:
        thread = worker_threads[udid]
    elif f"{udid}_multiapp" in worker_threads:
        thread = worker_threads[f"{udid}_multiapp"]
    elif f"{udid}_spotify" in worker_threads:
        thread = worker_threads[f"{udid}_spotify"]
    elif f"{udid}_tidal" in worker_threads:
        thread = worker_threads[f"{udid}_tidal"]
    elif f"{udid}_apple_music" in worker_threads:
        thread = worker_threads[f"{udid}_apple_music"]
    else:
        print(f"Thread with UDID {udid} not found in worker_threads. | {worker_threads}")
        return

    if status:
        thread["status"] = status

    if proxy:
        thread["proxy"] = proxy

    if increment_logins:
        thread["logins"] += 1

    if increment_streams:
        thread["streams"] += 1

    if increment_likes:
        thread["likes"] += 1

    if increment_follows:
        thread["follows"] += 1

    if increment_errors:
        thread["errors"] += 1

    if session_time:
        thread['session_time'] = session_time




def check_http_https(proxy):
    proxies = {
        "http": proxy,
        "https": proxy,
    }
    url = "https://ipinfo.io/ip"
    try:
        response = requests.get(url, proxies=proxies, timeout=5)
        if response.status_code == 200:
            return "HTTP/HTTPS", "Working"
        else:
            return None, f"Failed with status code {response.status_code}"
    except requests.exceptions.ProxyError as e:
        return None, "Proxy error: Possibly wrong credentials or unauthorized IP"
    except requests.exceptions.RequestException as e:
        return None, f"Request error: {str(e)}"
    return None, "Unknown error"

def check_socks5(proxy_ip, proxy_port, username=None, password=None):
    if username and password:
        proxy_url = f"socks5://{username}:{password}@{proxy_ip}:{proxy_port}"
    else:
        proxy_url = f"socks5://{proxy_ip}:{proxy_port}"
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }
    url = "http://ipinfo.io/ip"
    try:
        response = requests.get(url, proxies=proxies, timeout=5)
        if response.status_code == 200:
            return "SOCKS5", "Working"
        else:
            return None, f"Failed with status code {response.status_code}"
    except ProxyError as e:
        if "authentication failed" in str(e):
            return None, "Authentication failed: Possibly wrong credentials"
        else:
            return None, f"Proxy error: {str(e)}"
    except RequestException as e:
        return None, f"Request error: {str(e)}"
    return None, "Unknown error"

def determine_proxy_protocol(proxy):
    parts = proxy.split(":")
    if len(parts) == 2:
        proxy_ip, proxy_port = parts
        proxy_port = int(proxy_port)
        username = None
        password = None
        proxy_http_https = f"http://{proxy_ip}:{proxy_port}"
    elif len(parts) == 4:
        proxy_ip, proxy_port, username, password = parts
        proxy_port = int(proxy_port)
        proxy_http_https = f"http://{username}:{password}@{proxy_ip}:{proxy_port}"
    else:
        return "Invalid proxy format", "N/A"

    # Check HTTP/HTTPS

    protocol, status = check_http_https(proxy_http_https)

    if protocol:
        return protocol, status

    # Check SOCKS5
    protocol, status = check_socks5(proxy_ip, proxy_port, username, password)
    if protocol:
        return protocol, status

    return None, "Failed to determine protocol"


def request_with_proxy(url, proxy, max_retries=10, delay=1):
    proxy_dict = {
        'http': proxy,
        'https': proxy
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, proxies=proxy_dict, timeout=10)
            if response.status_code == 200:
                return response
        except RequestException as e:
            print(f"Attempt {attempt}: Request failed with exception: {e}")

        time.sleep(delay)
    return None




def initialize():
    files_dir = os.path.join(project_dir, 'Files')
    if not os.path.exists(files_dir):
        os.makedirs(files_dir, exist_ok=True)

    configs_dir = os.path.join(files_dir, 'Configs')
    if not os.path.exists(configs_dir):
        os.makedirs(configs_dir, exist_ok=True)

    napster_app_dir = os.path.join(files_dir, 'Adb')
    if not os.path.exists(napster_app_dir):
        os.makedirs(napster_app_dir, exist_ok=True)

    sessions_dir = os.path.join(files_dir, 'Sessions')
    if not os.path.exists(sessions_dir):
        os.makedirs(sessions_dir, exist_ok=True)

    logs_dir = os.path.join(files_dir, 'Logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)

    # Initial adb check and taskkill
    adb_dest = os.path.join(files_dir, 'Adb', 'adb.exe')
    if not os.path.isfile(adb_dest):
        os.system('start /min /wait cmd /c "TASKKILL /F /IM adb.exe"')
        try:
            adb_src = adbutils.adb_path()
            shutil.copy2(adb_src, adb_dest)
            for dll in ['AdbWinApi.dll', 'AdbWinUsbApi.dll']:
                dll_src = os.path.join(os.path.dirname(adb_src), dll)
                if os.path.isfile(dll_src):
                    shutil.copy2(dll_src, os.path.join(files_dir, 'Adb', dll))
        except Exception:
            pass

    # scrcpy: copy from the bundle (Files/Adb) into appdata if missing so the
    # live login view works out of the box on any PC.
    try:
        _scrcpy_dest = os.path.join(files_dir, 'Adb', 'scrcpy.exe')
        if not os.path.isfile(_scrcpy_dest):
            _scrcpy_bundle = os.path.join(_bundle_app_dir(), 'Files', 'Adb', 'scrcpy.exe')
            if os.path.isfile(_scrcpy_bundle):
                os.makedirs(os.path.join(files_dir, 'Adb'), exist_ok=True)
                shutil.copy2(_scrcpy_bundle, _scrcpy_dest)
                for _f in ['scrcpy-server', 'avcodec-62.dll', 'avformat-62.dll', 'avutil-60.dll',
                           'libusb-1.0.dll', 'SDL3.dll', 'swresample-6.dll']:
                    _s = os.path.join(os.path.dirname(_scrcpy_bundle), _f)
                    if os.path.isfile(_s):
                        shutil.copy2(_s, os.path.join(files_dir, 'Adb', _f))
                print("scrcpy copied from bundle to appdata")
    except Exception as e:
        print(f"scrcpy bundle copy skipped: {e}")


    # Create the database tables
    with app.app_context():
        db.create_all()
        try:
            # Migration: add spotify_version column if missing (SQLite ALTER TABLE)
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(db.engine)
            if 'spotify_version' not in [c['name'] for c in insp.get_columns('device')]:
                db.session.execute(db.text('ALTER TABLE device ADD COLUMN spotify_version VARCHAR(100)'))
                db.session.commit()
                add_log('INFO', 'Main', 'Added spotify_version column to device table.')
        except Exception as mig_exc:
            add_log('WARN', 'Main', f'Migration spotify_version skipped: {str(mig_exc)}')

    settings_file_path = os.path.join(project_dir, 'Files', 'settings.json')
    if os.path.exists(settings_file_path):
        with open(settings_file_path, 'r') as settings_file:
            settings_data = json.load(settings_file)
            global settings_capsolver_api_key
            settings_capsolver_api_key = settings_data.get('apiKey')
    #add_log('INFO', 'Main', f'CapSolver API Key: {settings_capsolver_api_key}')
    _load_spotify_ui_profiles()
    global backend_state
    backend_state = 'Ready!'


initialize()





def artist_links_function(link_o, type, artist_name, album_name, song_count):
    try:
        # Check if the link already exists in the database
        with app.app_context():
            existing_link = Link.query.filter_by(link=link_o).first()

            if existing_link:
                # If the link exists and is older than 5 days, rescrape the data
                if datetime.utcnow() - existing_link.time_read > timedelta(days=5):
                    scraped_data = scrape_artist_link(link_o)
                    if scraped_data:
                        existing_link.artist_name = scraped_data['artist_name']
                        existing_link.album_name = scraped_data['album_name']
                        existing_link.song_count = scraped_data['song_count']
                        existing_link.time_read = datetime.utcnow()
                        db.session.commit()

                return existing_link.type, existing_link.artist_name, existing_link.album_name, existing_link.song_count

            # If the link doesn't exist, scrape it and add it to the database
            scraped_data = scrape_artist_link(link_o)
            if scraped_data:
                new_link = Link(
                    link=link_o,
                    type=scraped_data['type'],
                    artist_name=scraped_data['artist_name'],
                    album_name=scraped_data['album_name'],
                    song_count=scraped_data['song_count'],
                    time_read=datetime.utcnow()
                )
                db.session.add(new_link)
                db.session.commit()
                return new_link.type, new_link.artist_name, new_link.album_name, new_link.song_count

            return None, None, None, None

    except Exception as e:
        add_log("CRUC", "Main", f"Crucial error in artist_links_function: {str(e)}")
        return "failed", None, None, None


def scrape_artist_link(link_o):
    """Scrape the link to extract artist name, album name, song count, and type."""
    try:
        while True:
            r = requests.get(link_o)
            soup = BeautifulSoup(r.content, 'html.parser')
            title = str(soup.title.text).split(" | ")[0]

            # Retry with proxy if the page is not available
            if 'Page not available' in title:
                proxy = FreeProxy().get()
                proxies = {'http': proxy, 'https': proxy}
                r = requests.get(link_o, proxies=proxies)
                soup = BeautifulSoup(r.content, 'html.parser')
                title = str(soup.title.text).split(" | ")[0]

            break
        og_description = soup.find('meta', property='og:description')['content']
        songs_match = re.search(r'(\d+) songs', og_description)
        artist_name = title.split(" by ")[1]
        album_name = title.split(" - ")[0]
        link_type = title.split(" - ")[1].split(" by ")[0]

        pass
        # Adjust link type
        if "song" in link_type:
            link_type = "Track"

        song_count = int(songs_match.group(1)) if songs_match else 1

        if artist_name.lower() == "null" or song_count == 0:
            return None

        return {
            'artist_name': artist_name,
            'album_name': album_name,
            'song_count': song_count,
            'type': link_type
        }

    except Exception as e:
        print(f"Error scraping link: {str(e)}")
        return None



def get_random_proxy():
    proxy = random.choice(worker_loaded_proxies)
    return proxy


def get_random_account():
    account = random.choice(worker_loaded_accounts)
    used_accounts.add(account)
    return account


def get_random_link():
    link = random.choice(worker_loaded_link)
    return link


def check_and_click(d, album_name, artist_name, pkg, spotify_version=None):
    # Spotify 9.x: search results are rows inside the search_content_recyclerview.
    d.implicitly_wait(3)

    def scan_results():
        recycler = d(resourceId=spotify_ui(pkg, spotify_version, 'search_content_recyclerview'))
        if not recycler.exists():
            return None
        rows = recycler.child(resourceId=spotify_ui(pkg, spotify_version, 'row_root'))
        count = rows.count
        best = None
        for i in range(count):
            try:
                row = rows[i]
                title = str(row.child(resourceId=spotify_ui(pkg, spotify_version, 'title')).get_text())
                subtitle = str(row.child(resourceId=spotify_ui(pkg, spotify_version, 'subtitle')).get_text()).lower()
            except Exception:
                continue
            if album_name.lower() not in title.lower():
                continue
            # Skip plain song/episode rows; only release rows (album/single/ep).
            if 'canción' in subtitle or 'song' in subtitle or 'episodio' in subtitle or 'episode' in subtitle:
                continue
            if artist_name.lower() in subtitle:
                if 'álbum' in subtitle or 'album' in subtitle:
                    return row  # exact album row, click immediately
                if best is None:
                    best = row  # single/ep with matching artist
        return best

    # First pass: scan the mixed results, scrolling a few times.
    for attempt in range(4):
        row = scan_results()
        if row is not None:
            row.click()
            return True, ''
        d.swipe(540, 1700, 540, 900, duration=0.4)
        d.implicitly_wait(1)

    # Second pass: filter to albums only and scan again.
    try:
        alb_tab = d(text='Álbumes')
        if alb_tab.exists():
            alb_tab.click()
            sleep(2)
    except Exception:
        pass
    row = scan_results()
    if row is not None:
        row.click()
        return True, ''
    return False, ''


def _atx_reconnect(udid):
    """Restart the device's uiautomator2 driver and return a fresh session.

    The -32002 error (UiAutomationNotConnectedError) happens when the
    uiautomator2 driver of a device dies. reset_uiautomator() restarts the
    service (am instrument) and waits until it responds.
    """
    try:
        import uiautomator2 as ua2
        d = ua2.connect(udid)
        try:
            d.reset_uiautomator()
        except Exception as e:
            print(f"_atx_reconnect reset failed for {udid}: {e}")
        d.implicitly_wait(10)
        # Warm up so a broken driver is forced to actually start before we
        # hand the session back to the worker.
        d.app_current()
        return d
    except Exception as e:
        print(f"_atx_reconnect failed for {udid}: {e}")
        return None


def _load_link_error(d, udid, e):
    try:
        freeze_rotation_port(d)
    except:
        pass
    update_thread_status(udid, 'Error while Loading link', None, False, False, False, False, True, None)
    add_log("ERR.", udid, "Error while Loading link: " + str(e))
    global worker_bot_errors
    worker_bot_errors += 1
    return False, 0, d


def load_link(d, udid, account_type, pkg, spotify_version=None):
    """Wrapper: retries the whole link load once with a fresh session if the
    ATX session dies mid-way (-32002)."""
    for attempt in range(2):
        try:
            return _load_link_impl(d, udid, account_type, pkg, spotify_version)
        except Exception as e:
            if '-32002' in str(e) and attempt == 0:
                add_log("WARN", udid, f"ATX session lost in load_link, reconnecting and retrying: {e}")
                d2 = _atx_reconnect(udid)
                if d2 is None:
                    return _load_link_error(d, udid, e)
                d = d2
                sleep(1)
                continue
            return _load_link_error(d, udid, e)
    return False, 0, d


def _load_link_impl(d, udid, account_type, pkg, spotify_version=None):
    try:
        if not str(d.app_current()).lower().__contains__('spotify'):
            d.app_start(pkg, ".MainActivity")
        link = get_random_link()

        global config_search_links_perc
        search_play = False

        d.implicitly_wait(5)
        try:
            # Only treat as logged out when the actual login form is present, so a
            # transient splash/loading logo does not hard-block the worker.
            if d(resourceId=spotify_ui(pkg, spotify_version, 'spotify_logo_no_text')).exists() and \
                    d(resourceId=spotify_ui(pkg, spotify_version, 'username_text')).exists(3):
                add_log("EXC.", udid, f"Device is logged out: {udid}!")
                update_thread_status(udid, 'Logged out', None, False, False, False, False, False, None)
                input()
        except:
            pass


        link_type, artist_name, album_name, song_count = artist_links_function(link, None, None, None, None)

        songs_in_link = song_count
        if not str(d.app_current()).lower().__contains__('spotify'):
            d.app_start(pkg, ".MainActivity")


        if d(resourceId=spotify_ui(pkg, spotify_version, 'later_button')).exists:
            d(resourceId=spotify_ui(pkg, spotify_version, 'later_button')).click_exists(1)
        if d(resourceId=spotify_ui(pkg, spotify_version, 'dismiss_text')).exists:
            d(resourceId=spotify_ui(pkg, spotify_version, 'dismiss_text')).click_exists(1)

        if d(resourceId=spotify_ui(pkg, spotify_version, 'player_overlay_header')).child(className='androidx.compose.ui.platform.ComposeView').exists:
            d(resourceId=spotify_ui(pkg, spotify_version, 'player_overlay_header')).child(className='androidx.compose.ui.platform.ComposeView').click_exists(1)

        d.xpath(
            f'//*[@resource-id="{pkg}:id/webview_container"]/android.webkit.WebView[1]/android.webkit.WebView[1]/android.view.View[1]/android.view.View[1]/android.view.View[1]').click_exists(
            0.1)
        d.implicitly_wait(5)
        if random.randrange(100) < int(config_search_links_perc):
            search_play = True
            try:
                if not str(d.app_current()).lower().__contains__('spotify'):
                    d.app_start(pkg, ".MainActivity")
                # Close any full screen page (e.g. full player) so the bottom nav bar is visible.
                for _ in range(4):
                    if d(resourceId=spotify_ui(pkg, spotify_version, 'navigation_bar')).exists(timeout=2):
                        break
                    d.press('back')
                    sleep(1)
                if d(resourceId=spotify_ui(pkg, spotify_version, 'search_tab')).exists:
                    d(resourceId=spotify_ui(pkg, spotify_version, 'search_tab')).click()
                else:
                    tab = d.xpath(
                        f'//*[@resource-id="{pkg}:id/navigation_bar"]/android.view.View/android.view.View[2]')
                    if tab.wait(timeout=3):
                        tab.click()
                    else:
                        d.click(405, 1848)  # Buscar tab center on 1080x1920
            except:
                d(resourceId=spotify_ui(pkg, spotify_version, 'dismiss_text')).click_exists(1)
                d.press('back')
                if not str(d.app_current()).lower().__contains__('spotify'):
                    d.app_start(pkg, ".MainActivity")
                if d(resourceId=spotify_ui(pkg, spotify_version, 'search_tab')).exists:
                    d(resourceId=spotify_ui(pkg, spotify_version, 'search_tab')).click()
                else:
                    tab = d.xpath(
                        f'//*[@resource-id="{pkg}:id/navigation_bar"]/android.view.View/android.view.View[2]')
                    if tab.wait(timeout=3):
                        tab.click()
                    else:
                        d.click(405, 1848)  # Buscar tab center on 1080x1920
            d.shell("settings put secure preferred_input_method com.android.inputmethod.latin/.LatinIME")
            d(resourceId=spotify_ui(pkg, spotify_version, 'browse_search_bar_container')).click_exists(3)
            sleep(1)
            try:
                d(className='android.widget.EditText').set_text(f'{artist_name} {album_name}')
            except Exception as _set_txt_err:
                if '-32002' in str(_set_txt_err):
                    add_log("WARN", udid, f"ATX session lost while typing search, reconnecting: {_set_txt_err}")
                    _newd = _atx_reconnect(udid)
                    if _newd is not None:
                        d = _newd
                        sleep(1)
                        d(className='android.widget.EditText').set_text(f'{artist_name} {album_name}')
                    else:
                        raise
                else:
                    d(resourceId=spotify_ui(pkg, spotify_version, 'find_search_field_text')).click_exists(2)
                    d(resourceId=spotify_ui(pkg, spotify_version, 'browse_search_bar_container')).click_exists(1)
                    d(className='android.widget.EditText').set_text(f'{artist_name} {album_name}')
            sleep(0.5)
            d.press("enter")
            add_log("INFO", udid, f"Searching for {artist_name} {album_name}")

            for i in range(50):
                if d(resourceId=spotify_ui(pkg, spotify_version, 'search_content_recyclerview')).exists:
                    break
                if d(resourceId=spotify_ui(pkg, spotify_version, 'search_body')).exists:
                    break
                if d(resourceId=spotify_ui(pkg, spotify_version, 'no_results_banner_search_root')).exists:
                    break
                time.sleep(0.1)

            if d(resourceId=spotify_ui(pkg, spotify_version, 'no_results_banner_search_root')).exists:
                loaded = False
                msg = "No results found"
            else:
                loaded, msg = check_and_click(d, album_name, artist_name, pkg, spotify_version)

            d.implicitly_wait(15)
            if loaded is False:
                update_thread_status(udid, 'Search not found', None, False, False, False, False, False, None)
                add_log("EXC.", udid, f'Failed to find link: {link} via search tab!')
                cmd = f'am start -a android.intent.action.VIEW -d "{link}" {pkg}'  # -s {d.serial}c
                d.shell(cmd)
        else:
            cmd = f'am start -a android.intent.action.VIEW -d "{link}" {pkg}'  # -s {d.serial}c
            d.shell(cmd)

        found_element = None
        for i in range(20):
            if d(text="This content is no longer available").exists:
                add_log("EXC.", udid, f"Link is dead: {link}")
                return False, 0, d
            if d(resourceId=spotify_ui(pkg, spotify_version, 'artwork')).exists:
                found_element = d(resourceId=spotify_ui(pkg, spotify_version, 'artwork'))
                break
            if d(resourceId=spotify_ui(pkg, spotify_version, 'artwork_slot')).exists:
                found_element = d(resourceId=spotify_ui(pkg, spotify_version, 'artwork_slot'))
                break
            if d(resourceId=spotify_ui(pkg, spotify_version, 'metadata_slot')).exists:
                found_element = d(resourceId=spotify_ui(pkg, spotify_version, 'metadata_slot'))
                break
            if d(resourceId=spotify_ui(pkg, spotify_version, 'cwp_header_media_slot')).exists:
                found_element = d(resourceId=spotify_ui(pkg, spotify_version, 'cwp_header_media_slot'))
                break
            if d(resourceId=spotify_ui(pkg, spotify_version, 'creator_names')).exists:
                found_element = d(resourceId=spotify_ui(pkg, spotify_version, 'creator_names'))
                break
            d(resourceId=spotify_ui(pkg, spotify_version, 'dismiss_text')).click_exists(1)

        add_log("INFO", udid,str("Loaded new link, " + artist_name + " - " + album_name + " with " + str(songs_in_link) + " Song/s in it."))
        update_thread_status(udid, 'Link Loaded', None, False, False, False, False, False, None)

        try:
            bounds = found_element.info['bounds']
            start_x = (bounds['left'] + bounds['right']) // 2  # Middle of the element horizontally
            start_y = bounds['bottom']  # Bottom of the element
            end_x = start_x  # Keeping the horizontal position constant for a vertical swipe
            swipe_distance = int(d.window_size()[1] * 0.1)  # 80% of the screen height
            end_y = max(0, start_y - swipe_distance)  # Ensure end_y remains within screen bounds
            d.swipe(start_x, start_y, end_x, end_y, duration=0.3)  # Ensure it's a swipe up
        except:
            pass


        if random.randrange(100) < int(config_album_likes_rate):
            try:
                if account_type == "Free":
                    d(resourceId=spotify_ui(pkg, spotify_version, 'heart_button')).click_exists(1)  # Link like free account
                else:
                    d(resourceId=spotify_ui(pkg, spotify_version, 'cwp_header_action2')).click_exists(1)  # Link like premium account
                update_thread_status(udid, 'Link Loaded', None, False, False, True, False, False, None)

                global worker_album_likes
                worker_album_likes += 1
                add_log("SUCC", udid, str("Liked link: " + album_name))
            except:
                add_log("ERR.", udid, "Failed to like link!")

        if random.randrange(100) < int(config_shuffle_perc):
            d(resourceId=spotify_ui(pkg, spotify_version, 'shuffle_button')).click_exists(1)

        if d.xpath(f'//*[@resource-id="{pkg}:id/page_loader_view"]/android.widget.FrameLayout[1]/android.widget.FrameLayout[1]/androidx.recyclerview.widget.RecyclerView[1]/android.widget.FrameLayout[2]/android.view.View[1]').exists:
            if d(resourceId=f"{pkg}:id/text").exists:
                if str(d(resourceId=f"{pkg}:id/text").get_text()).lower().__contains__("internet"):
                    add_log("EXC.", udid, "Proxy is to slow/not working!")
                    return False, 0, d
                elif str(d(resourceId=f"{pkg}:id/text").get_text()).lower().__contains__("connection"):
                    add_log("EXC.", udid, "Proxy is to slow/not working!")
                    return False, 0, d
                elif str(d(resourceId=f"{pkg}:id/text").get_text()).lower().__contains__("wifi"):
                    add_log("EXC.", udid, "Proxy is to slow/not working!")
                    return False, 0, d


        '''if random.randrange(100) < int(config_make_playlist_and_stream):
            d.implicitly_wait(20)
            if account_type != "Premium":
                d(resourceId="com.spotify.music:id/context_menu_button").click()
                d.xpath('//*[@resource-id="com.spotify.music:id/context_menu_rows"]/android.view.ViewGroup[5]').click()
                d(resourceId="com.spotify.music:id/new_playlist_button").click()
                playlistNameOld = d(resourceId="com.spotify.music:id/entity_name").get_text()
                number = re.findall(r'\d+', playlistNameOld)[0]
                playlist_name = f'{number} {album_name}'
                d(resourceId="com.spotify.music:id/entity_name").set_text(playlist_name)
                d(resourceId="com.spotify.music:id/continue_button").click()
                if d(resourceId="com.spotify.music:id/app_rater_dialog_button_dismiss").exists:
                    d(resourceId="com.spotify.music:id/app_rater_dialog_button_dismiss").click()
                d(resourceId="com.spotify.music:id/your_library_tab").click()
                d(resourceId="com.spotify.music:id/library_sort_row_root").wait(20)
                if d(resourceId="com.spotify.music:id/title", text=playlist_name).exists:
                    d(resourceId="com.spotify.music:id/title", text=playlist_name).click()
                elif d(resourceId="com.spotify.music:id/title", textContains=f'{number}').exists:
                    d(resourceId="com.spotify.music:id/title", textContains=f'{number}').click()
                elif d(resourceId="com.spotify.music:id/title", textContains=f'{album_name}').exists:
                    d(resourceId="com.spotify.music:id/title", textContains=f'{album_name}').click()
                else:
                    if worker_log_mode == "log":
                        print_log("EXC.", "yellow", thread, f'Failed to find created playlist: {playlist_name}')
                    add_log("EXC.", thread, f'Failed to find created playlist: {playlist_name}')
                    d.press('back')

                if worker_log_mode == "log":
                    print_log("SUCC", "green", thread, f'Generated new Playlist: {playlist_name}, streaming it now!')
                add_log("SUCC", thread, f'Generated new Playlist: {playlist_name}, streaming it now!')
            else:
                d(resourceId="com.spotify.music:id/context_menu_button").click()
                d.xpath('//*[@resource-id="com.spotify.music:id/context_menu_rows"]/android.view.ViewGroup[6]').click()
                d(resourceId="com.spotify.music:id/new_playlist_button").click()
                playlistNameOld = d(resourceId="com.spotify.music:id/entity_name").get_text()
                number = re.findall(r'\d+', playlistNameOld)[0]
                playlist_name = f'{number} {album_name}'
                d(resourceId="com.spotify.music:id/entity_name").set_text(playlist_name)
                d(resourceId="com.spotify.music:id/continue_button").click()
                if d(resourceId="com.spotify.music:id/app_rater_dialog_button_dismiss").exists:
                    d(resourceId="com.spotify.music:id/app_rater_dialog_button_dismiss").click()
                d(resourceId="com.spotify.music:id/your_library_tab").click()
                d(resourceId="com.spotify.music:id/library_sort_row_root").wait(20)
                if d(resourceId="com.spotify.music:id/title", text=playlist_name).exists:
                    d(resourceId="com.spotify.music:id/title", text=playlist_name).click()
                elif d(resourceId="com.spotify.music:id/title", textContains=f'{number}').exists:
                    d(resourceId="com.spotify.music:id/title", textContains=f'{number}').click()
                elif d(resourceId="com.spotify.music:id/title", textContains=f'{album_name}').exists:
                    d(resourceId="com.spotify.music:id/title", textContains=f'{album_name}').click()
                else:
                    if worker_log_mode == "log":
                        print_log("EXC.", "yellow", thread, f'Failed to find cCreated playlist: {playlist_name}')
                    add_log("EXC.", thread, f'Failed to find created playlist: {playlist_name}')
                    d.press('back')

                if worker_log_mode == "log":
                    print_log("SUCC", "green", thread, f'Generated new Playlist: {playlist_name}, streaming it now!')
                add_log("SUCC", thread, f'Generated new Playlist: {playlist_name}, streaming it now!')'''

        # Spotify 9.x: make the loaded album the now playing context, then open the full player.
        # The mini player can show a stale track (even from the same artist), so start the
        # loaded album with its real play button unless it is already playing.
        d.implicitly_wait(5)
        try:
            play_btn = d(resourceId=spotify_ui(pkg, spotify_version, 'button_play_and_pause'))
            desc = str(play_btn.info.get('contentDescription', '')).lower()
            if desc not in ('pausar', 'pause'):
                play_btn.click()  # start the album
        except:
            pass
        if d(resourceId=spotify_ui(pkg, spotify_version, 'now_playing_bar_layout')).exists(timeout=8):
            d(resourceId=spotify_ui(pkg, spotify_version, 'now_playing_bar_layout')).click()
        else:
            try:
                if account_type.lower() == "free":
                    d(resourceId=spotify_ui(pkg, spotify_version, 'children')).child(className='android.widget.Button').click()
                else:
                    d(resourceId=spotify_ui(pkg, spotify_version, 'button_play_and_pause')).click()  # play button
            except:
                d(resourceId=spotify_ui(pkg, spotify_version, 'close_button')).click_exists(1)
                if account_type.lower() == "free":
                    d(resourceId=spotify_ui(pkg, spotify_version, 'children')).child(className='android.widget.Button').click()
                else:
                    d(resourceId=spotify_ui(pkg, spotify_version, 'button_play_and_pause')).click()  # play button
            d(resourceId=spotify_ui(pkg, spotify_version, 'cover_image')).click_exists(5)
        # Ensure playback is actually running (the full player opens paused on 9.x).
        d.implicitly_wait(5)
        try:
            playpause = d(resourceId=spotify_ui(pkg, spotify_version, 'nowplaying_elements_playpause_button'))
            if playpause.exists:
                if str(playpause.info.get('contentDescription', '')).lower() in ('reproducir', 'play'):
                    playpause.click()
        except:
            pass
        d.implicitly_wait(10)
        if account_type == "Premium":
            if random.randrange(100) < int(config_shuffle_perc):
                d.implicitly_wait(5)
                try:
                    if str(d(resourceId=spotify_ui(pkg, spotify_version, 'playback_controls_container')).child(className="android.widget.ImageButton", index=0)).__contains__("off"):
                        d(resourceId=spotify_ui(pkg, spotify_version, 'playback_controls_container')).child(className="android.widget.ImageButton", index=0).click()
                    elif str(d(resourceId=spotify_ui(pkg, spotify_version, 'playback_controls_container')).child(className="android.widget.ImageButton", index=0).info['contentDescription']).__contains__("beenden"):
                        d(resourceId=spotify_ui(pkg, spotify_version, 'playback_controls_container')).child(className="android.widget.ImageButton", index=0).click()
                except:
                    if str(d(resourceId=spotify_ui(pkg, spotify_version, 'shuffle_button')).info['contentDescription']).__contains__(
                            "off"):
                        d(resourceId=spotify_ui(pkg, spotify_version, 'shuffle_button')).click()
                    elif str(d(resourceId=spotify_ui(pkg, spotify_version, 'shuffle_button')).info['contentDescription']).__contains__(
                            "beenden"):
                        d(resourceId=spotify_ui(pkg, spotify_version, 'shuffle_button')).click()

        return True, int(songs_in_link), d
    except Exception as e:
        if '-32002' in str(e):
            raise
        try:
            freeze_rotation_port(d)
        except:
            pass
        update_thread_status(udid, 'Error while Loading link', None, False, False, False, False, True, None)
        add_log("ERR.", udid, "Error while Loading link: " + str(e))
        global worker_bot_errors
        worker_bot_errors += 1
        return False, 0, d



def _safe_get_text(d, udid, pkg, spotify_version, key, alt_key=None, attempts=3, timeout=15):
    for attempt in range(attempts):
        try:
            d.implicitly_wait(timeout)
            el = d(resourceId=spotify_ui(pkg, spotify_version, key))
            if el.exists(timeout=timeout):
                return str(el.get_text())
        except Exception:
            pass
        if alt_key and attempt == attempts - 2:
            key = alt_key
        time.sleep(2)
    return ''


def _read_track_info(d, udid, pkg, spotify_version):
    artistInfo = _safe_get_text(d, udid, pkg, spotify_version, 'track_info_view_subtitle', attempts=3, timeout=15)
    titleInfo = _safe_get_text(d, udid, pkg, spotify_version, 'track_info_view_title', attempts=3, timeout=15)
    if not artistInfo or not titleInfo:
        add_log("INFO", udid, "Track info not fully ready, continuing without it.")
    return artistInfo, titleInfo


def _get_playtime_for_app(app_key='spotify'):
    """Return (playtime1, playtime2) using per-app override if set, else global."""
    global config_playtime_seconds, config_spotify_playtime, config_tidal_playtime, config_apple_playtime
    pt = ''
    if app_key == 'spotify' and config_spotify_playtime:
        pt = config_spotify_playtime
    elif app_key == 'tidal' and config_tidal_playtime:
        pt = config_tidal_playtime
    elif app_key == 'apple_music' and config_apple_playtime:
        pt = config_apple_playtime
    if not pt:
        pt = config_playtime_seconds
    if not pt or '-' not in str(pt):
        return 30, 60
    try:
        return map(int, str(pt).split('-'))
    except (ValueError, AttributeError):
        return 30, 60


def play_song(d, udid, account_type, ppa, songs_num, pkg, spotify_version=None):
    try:
        update_thread_status(udid, 'Streaming', None, False, False, False, False, False, None)
        d.implicitly_wait(0.1)
        if d.xpath(f'//*[@resource-id="{pkg}:id/webview_container"]/android.webkit.WebView[1]/android.webkit.WebView[1]/android.view.View[1]/android.view.View[1]/android.view.View[1]').exists:
            add_log("EXC.", udid, "Free Account has reached Maximum skips per day!")
            return False, 0, d


        playtime1, playtime2 = _get_playtime_for_app('spotify')
        finalplaytime = playtime1 if playtime1 == playtime2 else random.randrange(playtime1, playtime2)
        artistInfo, titleInfo = _read_track_info(d, udid, pkg, spotify_version)

        if random.randrange(100) < int(config_song_likes_rate):
            if d(resourceId=spotify_ui(pkg, spotify_version, 'feedback_buttons_container')).child(
                    className="android.widget.ImageButton", index=1).exists:
                like_el = str(d(resourceId=spotify_ui(pkg, spotify_version, 'feedback_buttons_container')).child(
                    className="android.widget.ImageButton", index=1).info['contentDescription'])
                if like_el.__contains__("Item added"):
                    pass
                elif like_el.__contains__('Element wurde hinzugefügt'):
                    pass
                elif like_el.__contains__('Elemento añadido'):
                    pass
                elif like_el.__contains__('Elemento agregado'):
                    pass
                else:
                    try:
                        d.implicitly_wait(10)
                        if d(resourceId=spotify_ui(pkg, spotify_version, 'heart_button')).exists:
                            d(resourceId=spotify_ui(pkg, spotify_version, 'heart_button')).click()  # Song Like button free account
                        else:
                            d(resourceId=spotify_ui(pkg, spotify_version, 'feedback_buttons_container')).child(
                                className="android.widget.ImageButton", index=1).click()
                            d(resourceId=spotify_ui(pkg, spotify_version, 'back_button')).click_exists(3)
                        global worker_song_likes
                        worker_song_likes += 1
                        add_log("SUCC", udid, str("Liked song: " + titleInfo))
                        update_thread_status(udid, 'Song Liked', None, False, False, True, False, False, None)
                    except:
                        add_log("EXC.", udid, "Failed to like song!")
            else:
                try:
                    d.implicitly_wait(10)
                    if d(resourceId=spotify_ui(pkg, spotify_version, 'heart_button')).exists:
                        d(resourceId=spotify_ui(pkg, spotify_version, 'heart_button')).click()  # Song Like button free account
                    else:
                        d(resourceId=spotify_ui(pkg, spotify_version, 'feedback_buttons_container')).child(
                            className="android.widget.ImageButton", index=1).click()
                        d(resourceId=spotify_ui(pkg, spotify_version, 'back_button')).click_exists(3)
                    worker_song_likes += 1
                    add_log("SUCC", udid, str("Liked song: " + titleInfo))
                    update_thread_status(udid, 'Song Liked', None, False, False, True, False, False, None)
                except:
                    add_log("EXC.", udid, "Failed to like song!")
        if random.randrange(100) < int(config_follows_rate):
            d.implicitly_wait(10)
            d(resourceId=spotify_ui(pkg, spotify_version, 'track_info_view_subtitle')).click()
            d(resourceId=spotify_ui(pkg, spotify_version, 'dismiss_text')).click_exists(2)
            time.sleep(2)
            if d(resourceId=spotify_ui(pkg, spotify_version, 'follow_button')).exists:
                d(resourceId=spotify_ui(pkg, spotify_version, 'follow_button')).click()
                artist = d.xpath(
                    f'//*[@resource-id="{pkg}:id/collapsing_toolbar"]/android.view.ViewGroup[1]/android.widget.TextView[1]').get_text()
                add_log("SUCC", udid, str("Followed: " + artist))
                global worker_follows_done
                worker_follows_done += 1
                update_thread_status(udid, 'Artist Followed', None, False, False, False, True, False, None)

            d.shell('input keyevent KEYCODE_BACK')
            d(resourceId=spotify_ui(pkg, spotify_version, 'cover_image')).click_exists(2)

        full_playtime_run = False
        d.implicitly_wait(20)
        if random.randrange(100) < int(config_play_full_song_perc):
            full_playtime_run = True

            def time_to_seconds(time_str):
                minutes, seconds = map(int, time_str.split(":"))
                return minutes * 60 + seconds

            d.implicitly_wait(0.1)
            playtime2 = _safe_get_text(d, udid, pkg, spotify_version, 'duration', 'duration_text', attempts=3, timeout=15)
            try:
                playtime2_seconds = time_to_seconds(playtime2)
            except:
                playtime2_seconds = 240  # fallback: no se pudo leer la duración
            if playtime2_seconds <= 0:
                playtime2_seconds = 240
            done = False
            msg = None
            last_playtime1_seconds = None

            # Start time for the timeout check
            start_time = time.time()
            while done is False:
                elapsed_time = time.time() - start_time
                if elapsed_time > 300:  # 360 seconds = 6 minutes
                    msg = "stuck"
                    break
                d.implicitly_wait(0.1)
                playtime1 = _safe_get_text(d, udid, pkg, spotify_version, 'position', 'position_text', attempts=2, timeout=10)
                d.implicitly_wait(10)
                try:
                    playtime1_seconds = time_to_seconds(playtime1)
                except:
                    playtime1_seconds = last_playtime1_seconds if last_playtime1_seconds is not None else 0
                time_remaining = playtime2_seconds - playtime1_seconds
                if last_playtime1_seconds is None:
                    last_playtime1_seconds = playtime1_seconds
                else:
                    if last_playtime1_seconds == playtime1_seconds:
                        d(description="Play").click_exists(1)
                        playpause = d(resourceId=spotify_ui(pkg, spotify_version, 'nowplaying_elements_playpause_button'))
                        if playpause.exists:
                            if str(playpause.info.get('contentDescription', '')).lower() in ('reproducir', 'play'):
                                playpause.click()

                last_playtime1_seconds = playtime1_seconds


                if time_remaining <= 13:
                    done = True
                sleep(3)
            if msg is not None:
                if msg == "stuck":
                    add_log("EXC.", udid, "Full playtime check got stuck!")
        else:
            finalplaytime = finalplaytime - 5
            sleep(finalplaytime)
        global worker_streams_done, worker_streams_done_spotify
        worker_streams_done += 1
        worker_streams_done_spotify += 1
        global config_streams_to_do
        if config_streams_to_do == 0:
            add_log("FINAL", udid, "All Streams were made!")
            sleep(5)
            os._exit(0)
        else:
            config_streams_to_do -= 1
        ppa -= 1

        update_thread_status(udid, 'Stream done', None, False, True, False, False, False, None)

        d.implicitly_wait(1)
        songTime1 = _safe_get_text(d, udid, pkg, spotify_version, 'position', 'position_text', attempts=2, timeout=10)
        songTime2 = _safe_get_text(d, udid, pkg, spotify_version, 'duration', 'duration_text', attempts=2, timeout=10)
        d.implicitly_wait(10)

        if full_playtime_run is True:
            add_log("SUCC", udid,
                    str("Streamed " + titleInfo + " by " + artistInfo + ", with full playtime | PPA left: " + str(
                        ppa)))
        else:
            add_log("SUCC", udid,
                    str("Streamed " + titleInfo + " by " + artistInfo + ", with " + songTime1 + "/" + songTime2 + " | PPA left: " + str(
                        ppa)))

        if ppa == 0:
            add_log("INFO", udid, "All Streams for Account done")
            return False, 0, d
        if full_playtime_run is True:
            sleep(14)
        else:
            if songs_num != 1:
                try:
                    d.implicitly_wait(1)
                    if d(resourceId=spotify_ui(pkg, spotify_version, 'next_button')).exists:
                        d(resourceId=spotify_ui(pkg, spotify_version, 'next_button')).click()  # next button
                    else:
                        d(resourceId=spotify_ui(pkg, spotify_version, 'playback_controls_container')).child(
                            className="android.widget.ImageButton", index=3).click()
                except:
                    pass
        return True, ppa, d

    except Exception as e:
        update_thread_status(udid, 'Error while Playing song', None, False, False, False, False, True, None)
        add_log("ERR.", udid, "Error while Playing song: " + str(e))
        global worker_bot_errors
        worker_bot_errors += 1
        if '-32002' in str(e):
            _newd = _atx_reconnect(udid)
            if _newd is not None:
                d = _newd
        return False, 0, d

def restart_spotify_if_crashed(d, restart, pkg):
    try:
        if str(d(resourceId="android:id/alertTitle").get_text()).lower().__contains__('spotify'):
            d(resourceId="android:id/aerr_close").click_exists(5)
            d.app_stop(pkg)
            if restart is True:
                d.app_start(pkg)
                d.app_wait(pkg)
            return True
            #d(resourceId="android:id/aerr_close").click()
        return False
    except:
        pass


def disable_autoplay(d, udid, pkg):
    try:
        from PIL import Image
    except Exception:
        add_log("ERR.", udid, "disable_autoplay skipped, Pillow not available.")
        return
    try:
        d(description='Inicio, Pestaña 1 de 4').click_exists(3)
        time.sleep(1.5)
        if not d(description='Ir al perfil y a la configuración').exists:
            add_log("INFO", udid, "disable_autoplay: profile button not found.")
            return
        d(description='Ir al perfil y a la configuración').click()
        time.sleep(1.5)
        if not d(text='Configuración y privacidad').exists:
            d.press('back')
            return
        d(text='Configuración y privacidad').click()
        time.sleep(1.5)
        if not d(text='Reproducción').exists:
            d.press('back')
            d.press('back')
            return
        d(text='Reproducción').click()
        time.sleep(1.5)
        if not d(text='Autoplay').exists:
            d.press('back')
            d.press('back')
            d.press('back')
            return
        d.swipe(540, 1500, 540, 1100, duration=0.3)
        time.sleep(1.5)
        xml = d.dump_hierarchy(False)
        m = re.search(r'text="Autoplay"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if not m:
            d.press('back')
            d.press('back')
            d.press('back')
            return
        lt = int(m.group(2))
        lb = int(m.group(4))
        sw = None
        for mm in re.finditer(r'<node[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*/?>', xml):
            x1, y1, x2, y2 = map(int, mm.groups())
            if x1 > 700 and y1 >= lt - 120 and y2 <= lb + 160:
                sw = (x1, y1, x2, y2)
                break
        if sw is None:
            d.press('back')
            d.press('back')
            d.press('back')
            return
        shot = d.screenshot()
        if shot is None:
            d.press('back')
            d.press('back')
            d.press('back')
            return
        region = shot.crop((sw[0] - 20, sw[1] - 30, sw[2] + 20, sw[3] + 30))
        green = 0
        for px in region.getdata():
            r, g, b = px[0], px[1], px[2]
            if g > 140 and r < 110 and b < 150:
                green += 1
        if green > 150:
            d.click((sw[0] + sw[2]) // 2, (sw[1] + sw[3]) // 2)
            time.sleep(1.5)
            add_log("SUCC", udid, "Autoplay disabled (no more suggested tracks).")
        else:
            add_log("INFO", udid, "Autoplay already disabled.")
        d.press('back')
        time.sleep(1)
        d(description='Inicio, Pestaña 1 de 4').click_exists(2)
        time.sleep(1)
    except Exception as e:
        add_log("ERR.", udid, f"disable_autoplay failed: {e}")


def get_spotify_packages(d):
    """
    Returns a list of installed package names that contain 'com.spotify'
    using d.app_list().
    """
    # Use the built-in app_list() method with a filter string.
    packages = d.app_list("com.spotify")
    return packages


def _get_tidal_links_file():
    """Return the path to the TidalLinks.txt file."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'TidalLinks.txt')

def _get_random_tidal_link():
    """Pick a random Tidal link from TidalLinks.txt."""
    tidal_file = _get_tidal_links_file()
    if not os.path.exists(tidal_file):
        return None
    with open(tidal_file, 'r') as f:
        links = [l.strip() for l in f if l.strip()]
    if not links:
        return None
    return random.choice(links)

def _scrape_link_info(url):
    """Scrape a Tidal or Apple Music link to extract artist_name and album_name.
    Returns (artist_name, album_name) or (None, None) on failure."""
    try:
        from bs4 import BeautifulSoup as _BS

        if 'music.apple.com' in url:
            slug = url.rstrip('/').split('/')[-1]
            try:
                r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
                soup = _BS(r.content, 'html.parser')
                title = soup.title.text if soup.title else ''

                if ' by ' in title and ' on ' in title:
                    parts = title.split(' by ')
                    album_name = parts[0].strip()
                    artist_name = parts[1].split(' on ')[0].strip()
                    return artist_name, album_name

                og_title = soup.find('meta', property='og:title')
                if og_title:
                    content = og_title['content']
                    if ' by ' in content:
                        parts = content.split(' by ')
                        name = parts[0].strip()
                        artist = parts[1].split(' on ')[0].strip() if ' on ' in parts[1] else parts[1].strip()
                        return artist, name

                if slug and slug not in ('album', 'song', 'playlist'):
                    name_pretty = slug.replace('-', ' ').title()
                    return None, name_pretty
            except Exception:
                pass

            if slug and slug not in ('album', 'song', 'playlist'):
                name_pretty = slug.replace('-', ' ').title()
                return None, name_pretty
            return None, None

        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        soup = _BS(r.content, 'html.parser')
        title = soup.title.text if soup.title else ''

        if 'tidal.com' in url:
            if ' by ' in title and ' on ' in title:
                parts = title.split(' by ')
                album_name = parts[0].strip()
                artist_name = parts[1].split(' on ')[0].strip()
                return artist_name, album_name

            og_title = soup.find('meta', property='og:title')
            if og_title:
                content = og_title['content']
                if ' by ' in content:
                    parts = content.split(' by ')
                    return parts[1].strip(), parts[0].strip()
                elif ' - ' in content:
                    return content.split(' - ', 1)

        return None, None
    except Exception:
        return None, None

def _count_tidal_songs_from_link(link):
    """Estimate song count from a Tidal link. Album ~ 10-15 songs, playlist ~ 20-50."""
    if '/album/' in link:
        return random.randint(8, 15)
    elif '/playlist/' in link:
        return random.randint(15, 40)
    return 10

def _tidal_open_link(d, udid, link):
    """Open a Tidal link via intent and wait for it to load."""
    try:
        add_log("INFO", udid, f"[Tidal] Opening link: {link}")
        d.shell(f'am start -a android.intent.action.VIEW -d "{link}" -t android.intent.action.VIEW')
        time.sleep(6)
        ensure_screen_on(d)
        return True
    except Exception as e:
        add_log("ERR.", udid, f"[Tidal] Failed to open link: {e}")
        return False

def _tidal_play_from_link(d, udid):
    """Tap the Play/Reproducir button on a Tidal album/playlist screen."""
    try:
        play_btn = (d(description='Reproducir') or d(description='Play') or 
                     d(description='Play button') or d(text='Reproducir') or d(text='Play'))
        if play_btn.exists(timeout=5):
            play_btn.click()
            add_log("INFO", udid, "[Tidal] Play button tapped")
            time.sleep(3)
            return True
        else:
            add_log("WARN", udid, "[Tidal] Play button not found, trying first song")
            first_song = d(className='android.widget.TextView', clickable=True)
            if first_song.exists(timeout=3):
                first_song.click()
                time.sleep(3)
            return True
    except Exception as e:
        add_log("ERR.", udid, f"[Tidal] Play failed: {e}")
        return False

def _get_apple_links_file():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'AppleLinks.txt')

def _get_random_apple_link():
    apple_file = _get_apple_links_file()
    if not os.path.exists(apple_file):
        return None
    with open(apple_file, 'r') as f:
        links = [l.strip() for l in f if l.strip()]
    if not links:
        return None
    return random.choice(links)

def _count_apple_songs_from_link(link):
    if '/album/' in link:
        return random.randint(8, 15)
    elif '/playlist/' in link:
        return random.randint(15, 40)
    return 10

def _apple_open_link(d, udid, link):
    try:
        add_log("INFO", udid, f"[Apple Music] Opening link: {link}")
        d.shell(f'am start -a android.intent.action.VIEW -d "{link}" -t android.intent.action.VIEW')
        time.sleep(6)
        ensure_screen_on(d)
        return True
    except Exception as e:
        add_log("ERR.", udid, f"[Apple Music] Failed to open link: {e}")
        return False

def _apple_play_from_link(d, udid):
    try:
        play_btn = (d(description='Play') or d(description='Play button') or
                     d(text='Play') or d(description='Reproducir') or d(text='Reproducir'))
        if play_btn.exists(timeout=5):
            play_btn.click()
            add_log("INFO", udid, "[Apple Music] Play button tapped")
            time.sleep(3)
            return True
        else:
            add_log("WARN", udid, "[Apple Music] Play button not found, trying first song")
            first_song = d(className='android.widget.TextView', clickable=True)
            if first_song.exists(timeout=3):
                first_song.click()
                time.sleep(3)
            return True
    except Exception as e:
        add_log("ERR.", udid, f"[Apple Music] Play failed: {e}")
        return False

def _app_generic_load_link(d, udid, pkg, display_name):
    """Generic link loading for non-Spotify apps (Apple Music, Tidal).
    For Tidal: opens Tidal link directly. For others: parses Spotify link and searches."""
    try:
        if pkg == 'com.aspiro.tidal':
            link = _get_random_tidal_link()
            if not link:
                add_log("ERR.", udid, "[Tidal] No links found in TidalLinks.txt")
                return False, 0, d
            songs_in_link = _count_tidal_songs_from_link(link)
            _tidal_open_link(d, udid, link)
            _tidal_play_from_link(d, udid)
            update_thread_status(udid, '[Tidal] Link Loaded', None, False, False, False, False, False, None)
            add_log("INFO", udid, f"[Tidal] Loaded: {link} ({songs_in_link} songs)")
            return True, int(songs_in_link), d
        else:
            link = get_random_link()
            link_type, artist_name, album_name, song_count = artist_links_function(link, None, None, None, None)
            songs_in_link = song_count
            add_log("INFO", udid, f"[{display_name}] Loading: {artist_name} - {album_name} ({songs_in_link} songs)")

            if str(d.app_current()).get('package', '') != pkg:
                d.app_start(pkg)
                d.app_wait(pkg)
                time.sleep(3)

            search_term = f"{artist_name} {album_name}"
            _app_search_and_play(d, udid, pkg, display_name, search_term, artist_name, album_name)

            update_thread_status(udid, f'[{display_name}] Link Loaded', None, False, False, False, False, False, None)
            add_log("INFO", udid, f"[{display_name}] Loaded link: {artist_name} - {album_name} with {songs_in_link} songs")
            return True, int(songs_in_link), d
    except Exception as e:
        add_log("ERR.", udid, f"[{display_name}] Error loading link: {str(e)}")
        global worker_bot_errors
        worker_bot_errors += 1
        return False, 0, d


def _app_search_and_play(d, udid, pkg, display_name, search_term, artist_name, album_name):
    """Search for content in any music app using its search UI, then play."""
    d.implicitly_wait(5)

    d.app_start(pkg)
    time.sleep(3)
    d.app_wait(pkg)

    search_ui = {
        'com.apple.android.music': {
            'search_tab': lambda: d(description='Search').click_exists(3) or d(text='Search').click_exists(3),
            'search_field': lambda: d(className='android.widget.EditText').click_exists(3),
            'type_and_search': lambda term: d(className='android.widget.EditText').set_text(term),
        },
        'com.aspiro.tidal': {
            'search_tab': lambda: (d(description='Explorar').click_exists(3)),
            'search_field': lambda: (d(resourceId='com.aspiro.tidal:id/search_src_text').click_exists(3) or d(className='android.widget.AutoCompleteTextView').click_exists(3)),
            'type_and_search': lambda term: d(resourceId='com.aspiro.tidal:id/search_src_text').set_text(term) if d(resourceId='com.aspiro.tidal:id/search_src_text').exists(timeout=2) else d(className='android.widget.AutoCompleteTextView').set_text(term),
        },
    }

    ui = search_ui.get(pkg, {})
    if not ui:
        add_log("WARN", udid, f"[{display_name}] No search UI defined, using generic approach")
        return

    try:
        ui.get('search_tab', lambda: None)()
        time.sleep(1)
        ui.get('search_field', lambda: None)()
        time.sleep(0.5)
        ui.get('type_and_search', lambda t: None)(search_term)
        time.sleep(1)
        d.press("enter")
        time.sleep(3)

        first_result = d(className='android.widget.TextView', textContains=artist_name)
        if first_result.exists(timeout=5):
            first_result.click()
            time.sleep(2)

        play_btn = d(description='Play') or d(description='Reproducir') or d(description='Play button')
        if play_btn.exists(timeout=3):
            play_btn.click()
    except Exception as e:
        add_log("ERR.", udid, f"[{display_name}] Search failed: {str(e)}")


def _app_generic_play_song(d, udid, pkg, display_name, ppa, songs_num):
    """Generic play_song for non-Spotify apps. Waits playtime then advances. When multi-app is active, uses ADB media commands to avoid stealing UI focus."""
    try:
        update_thread_status(udid, f'[{display_name}] Streaming', None, False, False, False, False, False, None)
        app_key = 'tidal' if 'tidal' in pkg.lower() else 'apple_music' if 'apple' in pkg.lower() else 'spotify'
        playtime1, playtime2 = _get_playtime_for_app(app_key)
        finalplaytime = playtime1 if playtime1 == playtime2 else random.randrange(playtime1, playtime2)

        if len(config_selected_apps) > 1:
            add_log("INFO", udid, f"[{display_name}] Multi-app mode: waiting {finalplaytime}s via ADB (no UI)")
            sleep(finalplaytime)
        else:
            sleep(finalplaytime)

        global worker_streams_done, worker_streams_done_spotify, worker_streams_done_tidal, worker_streams_done_apple, config_streams_to_do
        worker_streams_done += 1
        if 'spotify' in display_name.lower():
            worker_streams_done_spotify += 1
        elif 'tidal' in display_name.lower():
            worker_streams_done_tidal += 1
        elif 'apple' in display_name.lower():
            worker_streams_done_apple += 1
        if config_streams_to_do == 0:
            add_log("FINAL", udid, f"[{display_name}] All Streams were made!")
            sleep(5)
            os._exit(0)
        else:
            config_streams_to_do -= 1
        ppa -= 1

        update_thread_status(udid, f'[{display_name}] Stream done', None, False, True, False, False, False, None)
        add_log("SUCC", udid, f"[{display_name}] Stream done | PPA left: {ppa}")

        if ppa == 0:
            add_log("INFO", udid, f"[{display_name}] All Streams for Account done")
            return False, 0, d

        if len(config_selected_apps) > 1:
            _adb_media_next(udid)
            add_log("INFO", udid, f"[{display_name}] Sent NEXT via ADB media")
        else:
            next_btn = d(description='Next') or d(description='Siguiente') or d(description='Skip')
            if next_btn.exists(timeout=2):
                next_btn.click()

        return True, ppa, d
    except Exception as e:
        add_log("ERR.", udid, f"[{display_name}] Error playing song: {str(e)}")
        global worker_bot_errors
        worker_bot_errors += 1
        return False, 0, d


def _app_generic_restart_if_crashed(d, restart, pkg):
    """Generic crash handler for any app."""
    try:
        alert_title = str(d(resourceId="android:id/alertTitle").get_text()).lower()
        if alert_title:
            d(resourceId="android:id/aerr_close").click_exists(5)
            d.app_stop(pkg)
            if restart:
                d.app_start(pkg)
                d.app_wait(pkg)
            return True
    except:
        pass
    return False


def _adb_shell(udid, cmd):
    """Run an adb shell command via subprocess (no UiAutomation needed)."""
    try:
        result = subprocess.run(
            [adb_path, '-s', udid, 'shell'] + cmd.split(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10,
            startupinfo=startupinfo
        )
        return result.stdout.strip()
    except Exception as e:
        return ''

def _adb_media_next(udid):
    """Send media NEXT via adb shell media dispatch."""
    _adb_shell(udid, 'media dispatch next')

def _adb_media_pause(udid):
    """Send media PAUSE via adb shell."""
    _adb_shell(udid, 'media dispatch pause')

def _adb_media_play(udid):
    """Send media PLAY via adb shell."""
    _adb_shell(udid, 'media dispatch play')

def _ensure_volume_max(udid):
    """Set media volume to maximum before streaming."""
    try:
        _adb_shell(udid, 'cmd audio set-volume STREAM_MUSIC max')
        _adb_shell(udid, 'media volume --set 15')
        _adb_shell(udid, 'cmd media_session volume --set 15')
    except Exception:
        pass

def _adb_is_audio_playing(udid, pkg=None):
    """Check if audio is playing via dumpsys audio."""
    out = _adb_shell(udid, 'dumpsys audio')
    if 'isPlaying=true' in out.lower() or 'stream_music' in out.lower():
        return True
    return False

def _get_device_ui_lock(udid):
    """Get or create a threading Lock for a specific device's UI."""
    if udid not in device_ui_locks:
        device_ui_locks[udid] = threading.RLock()
    return device_ui_locks[udid]

def _adb_go_home(udid):
    """Press Home button via adb."""
    _adb_shell(udid, 'input keyevent KEYCODE_HOME')

def _launch_app_via_intent(udid, pkg, activity=None):
    """Launch an app via am start without UiAutomation."""
    if activity:
        _adb_shell(udid, f'am start -n {activity}')
    else:
        _adb_shell(udid, f'monkey -p {pkg} -c android.intent.category.LAUNCHER 1')

def _stop_app_via_adb(udid, pkg):
    """Force stop an app via adb."""
    _adb_shell(udid, f'am force-stop {pkg}')


# ── Human-like helpers ───────────────────────────────────────────────

def _human_delay(min_s=0.3, max_s=1.2):
    """Random delay to mimic human pause."""
    time.sleep(random.uniform(min_s, max_s))


def _human_type(udid, text):
    """Type text character by character with random inter-key delays via ADB."""
    for ch in text:
        if ch == ' ':
            _adb_shell(udid, 'input keyevent 62')
        elif ch == "'":
            _adb_shell(udid, 'input text "\'"')
        elif ch == '"':
            _adb_shell(udid, 'input text "\\""')
        elif ch in ('/', '@', ':', '-', '.', '&', '=', '+', '#', '%'):
            _adb_shell(udid, f"input text '{ch}'")
        else:
            _adb_shell(udid, f'input text {ch}')
        time.sleep(random.uniform(0.05, 0.18))


def _human_tap(d, resource_id=None, description=None, text_match=None, text_contains=None, cls=None, timeout=4):
    """Human-like element tap: scroll slightly, wait, tap."""
    el = None
    if resource_id:
        el = d(resourceId=resource_id)
    elif description:
        el = d(description=description)
    elif text_match:
        el = d(text=text_match)
    elif text_contains:
        el = d(textContains=text_contains)
    elif cls:
        el = d(className=cls)
    if el and el.exists(timeout=timeout):
        _human_delay(0.2, 0.6)
        el.click()
        _human_delay(0.3, 0.8)
        return True
    return False


def _human_launch_app(d, udid, pkg):
    """Go Home, then launch app via monkey (simulates tapping the icon)."""
    _adb_go_home(udid)
    _human_delay(1.0, 2.5)
    _adb_shell(udid, f'monkey -p {pkg} -c android.intent.category.LAUNCHER 1')
    _human_delay(2.0, 4.0)
    ensure_screen_on(d)


def _parse_link_info(link):
    """Parse a URL to determine type (album/track/playlist) and extract info.
    Returns (link_type, slug_or_id)."""
    link = link.strip()
    if 'tidal.com' in link:
        if '/album/' in link:
            return 'Album', link.split('/album/')[-1].split('/')[0].split('?')[0]
        elif '/track/' in link:
            return 'Track', link.split('/track/')[-1].split('/')[0].split('?')[0]
        elif '/playlist/' in link:
            return 'Playlist', link.split('/playlist/')[-1].split('/')[0].split('?')[0]
    elif 'music.apple.com' in link:
        if '/album/' in link:
            return 'Album', link.split('/album/')[-1].split('/')[0].split('?')[0]
        elif '/song/' in link:
            return 'Track', link.split('/song/')[-1].split('/')[0].split('?')[0]
        elif '/playlist/' in link:
            return 'Playlist', link.split('/playlist/')[-1].split('/')[0].split('?')[0]
    elif 'open.spotify.com' in link:
        if '/album/' in link:
            return 'Album', link.split('/album/')[-1].split('/')[0].split('?')[0]
        elif '/track/' in link:
            return 'Track', link.split('/track/')[-1].split('/')[0].split('?')[0]
        elif '/playlist/' in link:
            return 'Playlist', link.split('/playlist/')[-1].split('/')[0].split('?')[0]
        elif '/artist/' in link:
            return 'Artist', link.split('/artist/')[-1].split('/')[0].split('?')[0]
    return 'Unknown', link


def _songs_for_type(link_type, explicit_count=None):
    """Return estimated song count for a link type."""
    if explicit_count:
        return int(explicit_count)
    if link_type == 'Track':
        return 1
    if link_type == 'Album':
        return random.randint(8, 15)
    if link_type == 'Playlist':
        return random.randint(15, 40)
    if link_type == 'Artist':
        return random.randint(10, 25)
    return random.randint(8, 15)



def _get_panda_numbers():
    """Read Panda's device.db and return {serial: panda_number}."""
    import sqlite3 as _sqlite3
    result_map = {}
    candidates = [
        os.path.join(os.environ.get('APPDATA', ''), '6WPTMA9HZO', 'device.db'),
    ]
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        for sub in os.listdir(appdata):
            db = os.path.join(appdata, sub, 'device.db')
            if os.path.isfile(db):
                candidates.append(db)
    for db_path in candidates:
        if not os.path.isfile(db_path):
            continue
        try:
            conn = _sqlite3.connect(db_path)
            cursor = conn.execute("SELECT onlySerial, sort FROM device WHERE userDelete=0")
            for serial, sort_num in cursor:
                if serial and sort_num:
                    result_map[str(serial).strip()] = sort_num
            conn.close()
            if result_map:
                return result_map
        except Exception:
            continue
    return result_map


def _get_now_playing(udid, pkg):
    """Query media_session to get current song title and state for a given package."""
    try:
        result = subprocess.run(
            [adb_path, '-s', udid, 'shell', 'dumpsys', 'media_session'],
            capture_output=True, text=True, timeout=10, startupinfo=startupinfo
        )
        output = result.stdout or ''
        lines = output.split('\n')
        current_pkg = None
        state = 'unknown'
        title = ''
        artist = ''
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('package='):
                current_pkg = stripped.split('=', 1)[1].split()[0]
            if current_pkg == pkg:
                if 'state=' in stripped and 'PlaybackState' in stripped:
                    m = re.search(r'state=(\d+)', stripped)
                    if m:
                        s = int(m.group(1))
                        state = {0: 'STOPPED', 1: 'PAUSED', 2: 'BUFFERING', 3: 'PLAYING'}.get(s, f'STATE_{s}')
                if stripped.startswith('metadata:') and 'description=' in stripped:
                    mm = re.search(r'description=([^,\n]+),\s*([^,\n]+)', stripped)
                    if mm:
                        t = mm.group(1).strip()
                        a = mm.group(2).strip()
                        if 'null' not in t.lower() and 'anuncio' not in t.lower() and t:
                            title = t
                            artist = a
        if title:
            return state, title, artist
        return state, '', ''
    except Exception as e:
        return 'ERROR', '', str(e)


def _open_spotify_human(d, udid, link, artist_name, album_name, pkg='com.spotify.music', link_type=None):
    """Open Spotify and navigate to a link like a human: launch, dismiss dialogs,
    go to Search tab, type artist+album, select result, play."""
    spotify_version = get_device_spotify_version(udid, pkg)

    if not str(d.app_current()).lower().__contains__('spotify'):
        d.app_start(pkg, ".MainActivity")
    _human_delay(2.0, 4.0)

    d(resourceId=spotify_ui(pkg, spotify_version, 'later_button')).click_exists(1)
    d(resourceId=spotify_ui(pkg, spotify_version, 'dismiss_text')).click_exists(1)
    _human_delay(0.5, 1.5)

    for _ in range(4):
        if d(resourceId=spotify_ui(pkg, spotify_version, 'navigation_bar')).exists(timeout=2):
            break
        d.press('back')
        _human_delay(0.8, 1.5)

    add_log("INFO", udid, f"[Spotify Human] Navigating to Search tab...")

    if d(resourceId=spotify_ui(pkg, spotify_version, 'search_tab')).exists:
        _human_delay(0.3, 0.8)
        d(resourceId=spotify_ui(pkg, spotify_version, 'search_tab')).click()
    else:
        tab = d.xpath(
            f'//*[@resource-id="{pkg}:id/navigation_bar"]/android.view.View/android.view.View[2]')
        if tab.wait(timeout=3):
            _human_delay(0.3, 0.8)
            tab.click()
        else:
            _human_delay(0.3, 0.6)
            d.click(405, 1848)

    _human_delay(1.0, 2.0)

    add_log("INFO", udid, f"[Spotify Human] Clicking search bar...")

    query_field = d(resourceId=spotify_ui(pkg, spotify_version, 'query'))
    if not query_field.exists(timeout=2):
        d.click(540, 360)
        _human_delay(1.0, 2.0)

    query_field = d(resourceId=spotify_ui(pkg, spotify_version, 'query'))
    edit_field = d(className='android.widget.EditText')
    search_field = query_field if query_field.exists(timeout=2) else (edit_field if edit_field.exists(timeout=2) else None)

    if not search_field:
        d(textContains="apetece").click_exists(3)
        _human_delay(1.0, 2.0)
        query_field = d(resourceId=spotify_ui(pkg, spotify_version, 'query'))
        edit_field = d(className='android.widget.EditText')
        search_field = query_field if query_field.exists(timeout=2) else (edit_field if edit_field.exists(timeout=2) else None)

    search_term = f"{artist_name} {album_name}"
    add_log("INFO", udid, f"[Spotify Human] Typing: {search_term}")

    if search_field:
        try:
            search_field.set_text(search_term)
        except Exception as e:
            if '-32002' in str(e):
                add_log("WARN", udid, f"[Spotify Human] ATX session lost, reconnecting...")
                _newd = _atx_reconnect(udid)
                if _newd:
                    d = _newd
                    _human_delay(1.0, 2.0)
                    rf = d(resourceId=spotify_ui(pkg, spotify_version, 'query'))
                    ef = d(className='android.widget.EditText')
                    sf = rf if rf.exists(timeout=2) else ef
                    if sf.exists(timeout=2):
                        sf.set_text(search_term)
                else:
                    raise
            else:
                raise
    else:
        add_log("WARN", udid, f"[Spotify Human] No search field found after all attempts")
        d.press("escape")
        return False

    _human_delay(0.8, 1.5)
    d.press("enter")
    add_log("INFO", udid, f"[Spotify Human] Search sent, waiting for results...")

    for i in range(50):
        if d(resourceId=spotify_ui(pkg, spotify_version, 'search_content_recyclerview')).exists:
            break
        if d(resourceId=spotify_ui(pkg, spotify_version, 'search_body')).exists:
            break
        if d(resourceId=spotify_ui(pkg, spotify_version, 'no_results_banner_search_root')).exists:
            break
        time.sleep(0.1)

    if d(resourceId=spotify_ui(pkg, spotify_version, 'no_results_banner_search_root')).exists:
        add_log("WARN", udid, f"[Spotify Human] No results found, falling back to link intent...")
        d.shell(f'am start -a android.intent.action.VIEW -d "{link}" {pkg}')
        _human_delay(4.0, 7.0)
    else:
        loaded, msg = check_and_click(d, album_name, artist_name, pkg, spotify_version)
        _human_delay(1.5, 3.0)
        if loaded:
            add_log("SUCC", udid, f"[Spotify Human] Found and selected: {artist_name} - {album_name}")
        else:
            add_log("WARN", udid, f"[Spotify Human] Search result not found, using intent fallback...")
            d.shell(f'am start -a android.intent.action.VIEW -d "{link}" {pkg}')
            _human_delay(4.0, 7.0)

    d.implicitly_wait(15)
    for i in range(20):
        if d(resourceId=spotify_ui(pkg, spotify_version, 'artwork')).exists:
            break
        if d(resourceId=spotify_ui(pkg, spotify_version, 'artwork_slot')).exists:
            break
        if d(resourceId=spotify_ui(pkg, spotify_version, 'metadata_slot')).exists:
            break
        if d(resourceId=spotify_ui(pkg, spotify_version, 'cwp_header_media_slot')).exists:
            break
        if d(text="This content is no longer available").exists:
            add_log("ERR.", udid, f"[Spotify Human] Link is dead")
            return False
        d(resourceId=spotify_ui(pkg, spotify_version, 'dismiss_text')).click_exists(1)
        time.sleep(0.3)

    _human_delay(0.5, 1.5)

    try:
        already_playing = False
        play_btn = d(resourceId=spotify_ui(pkg, spotify_version, 'button_play_and_pause'))
        if play_btn.exists(timeout=3):
            desc = str(play_btn.info.get('contentDescription', '')).lower()
            if desc in ('pausar', 'pause'):
                already_playing = True

        if not already_playing:
            _human_delay(0.3, 0.8)

            if link_type and link_type in ('Track', 'Single'):
                scroll_down = random.randint(0, 1)
            else:
                scroll_down = random.randint(1, 3)
            for _ in range(scroll_down):
                d.swipe(540, 1400, 540, 800, duration=random.uniform(0.4, 0.8))
                _human_delay(0.8, 1.5)

            song_items = d(resourceId='com.spotify.music:id/track_row')
            if not song_items.exists:
                song_items = d(resourceId='com.spotify.music:id/simple播list_row')
            if not song_items.exists:
                song_items = d(resourceId='com.spotify.music:id/item_root')

            clicked_song = False
            if song_items.exists(timeout=3):
                count = song_items.count
                if count > 0:
                    pick = random.randint(0, min(count - 1, 5))
                    _human_delay(0.3, 0.8)
                    song_items[pick].click()
                    clicked_song = True
                    add_log("SUCC", udid, f"[Spotify Human] Clicked song #{pick+1} of {count}")

            if not clicked_song:
                _human_delay(0.3, 0.8)
                play_btn.click()
                add_log("SUCC", udid, f"[Spotify Human] Playing album (play button)")
    except Exception as e:
        add_log("WARN", udid, f"[Spotify Human] Play error: {e}, trying play button fallback")
        try:
            fallback = d(resourceId=spotify_ui(pkg, spotify_version, 'button_play_and_pause'))
            if fallback.exists(timeout=2):
                fallback.click()
                add_log("SUCC", udid, f"[Spotify Human] Fallback play button clicked")
        except:
            pass

    _human_delay(1.0, 2.5)
    return True


def _open_tidal_human(d, udid, link, artist_name=None, album_name=None):
    """Open Tidal, go to search tab, type artist+album, select result, play. All human-like."""
    _adb_go_home(udid)
    _human_delay(1.0, 2.0)
    _adb_shell(udid, 'monkey -p com.aspiro.tidal -c android.intent.category.LAUNCHER 1')
    _human_delay(3.0, 5.0)
    ensure_screen_on(d)

    add_log("INFO", udid, f"[Tidal Human] Navigating to Search...")

    explore_tab = (d(resourceId='com.aspiro.tidal:id/explore') or
                   d(description='Explorar') or d(description='Search'))
    if explore_tab.exists(timeout=5):
        _human_delay(0.3, 0.8)
        explore_tab.click()
        _human_delay(1.5, 3.0)
    else:
        d.press('back')
        _human_delay(0.5, 1.0)
        explore_tab = (d(resourceId='com.aspiro.tidal:id/explore') or
                       d(description='Explorar') or d(description='Search'))
        if explore_tab.exists(timeout=3):
            explore_tab.click()
            _human_delay(1.5, 3.0)

    add_log("INFO", udid, f"[Tidal Human] Clicking search bar...")
    search_field = (d(resourceId='com.aspiro.tidal:id/search_src_text') or
                    d(className='android.widget.AutoCompleteTextView') or
                    d(className='android.widget.EditText'))
    if search_field.exists(timeout=5):
        _human_delay(0.3, 0.8)
        search_field.click()
        _human_delay(0.8, 1.5)
    else:
        search_icon = d(description='Search') or d(description='Buscar')
        if search_icon.exists(timeout=3):
            search_icon.click()
            _human_delay(0.8, 1.5)
            search_field = (d(resourceId='com.aspiro.tidal:id/search_src_text') or
                            d(className='android.widget.AutoCompleteTextView') or
                            d(className='android.widget.EditText'))
            search_field.exists(timeout=3)

    search_term = f"{artist_name} {album_name}" if artist_name and album_name else ""
    if search_term:
        add_log("INFO", udid, f"[Tidal Human] Typing: {search_term}")
        _human_type(udid, search_term)
        _human_delay(1.5, 3.0)

        _adb_shell(udid, 'input keyevent 66')
        add_log("INFO", udid, f"[Tidal Human] Search submitted, waiting for results...")
        _human_delay(3.0, 5.0)

        result_clicked = False

        def _tidal_click_element(el, label):
            try:
                info = el.info
                bounds = info.get('bounds', {})
                cx = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
                cy = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
                if cx > 0 and cy > 300:
                    d.click(cx, cy)
                    add_log("INFO", udid, f"[Tidal Human] Clicked {label} at ({cx},{cy})")
                    return True
            except:
                pass
            return False

        def _tidal_find_result(name):
            results = d(resourceId='com.aspiro.tidal:id/title')
            if not results.exists(timeout=3):
                results = d(textContains=name)
                if results.exists(timeout=2):
                    info = results.info
                    bounds = info.get('bounds', {})
                    cy = bounds.get('top', 0)
                    if cy < 300:
                        return None
                    return results
                return None
            for i in range(results.count):
                node = results[i]
                try:
                    t = node.info.get('text', '')
                    if name.lower() in t.lower():
                        b = node.info.get('bounds', {})
                        if b.get('top', 0) > 300:
                            return node
                except:
                    continue
            return None

        if album_name:
            for name_part in [album_name] + ([album_name.split()[0]] if len(album_name.split()) > 1 else []):
                el = _tidal_find_result(name_part)
                if el:
                    _human_delay(0.5, 1.0)
                    if _tidal_click_element(el, f"album '{name_part}'"):
                        _human_delay(2.5, 5.0)
                        result_clicked = True
                        break

        if not result_clicked and artist_name:
            el = _tidal_find_result(artist_name)
            if el:
                _human_delay(0.5, 1.0)
                if _tidal_click_element(el, f"artist '{artist_name}'"):
                    _human_delay(2.5, 5.0)
                    result_clicked = True

        if not result_clicked:
            results = d(resourceId='com.aspiro.tidal:id/title')
            if results.exists(timeout=3) and results.count > 0:
                pick = random.randint(0, min(results.count - 1, 3))
                _human_delay(0.3, 0.8)
                if _tidal_click_element(results[pick], f"result #{pick+1}"):
                    _human_delay(2.5, 5.0)
                    result_clicked = True

        if not result_clicked:
            all_clickable = d(className='android.widget.FrameLayout', clickable=True)
            if all_clickable.exists(timeout=3):
                _human_delay(0.3, 0.8)
                info = all_clickable.info
                bounds = info.get('bounds', {})
                cx = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
                cy = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
                d.click(cx, cy)
                _human_delay(2.0, 4.0)
                result_clicked = True
                add_log("INFO", udid, f"[Tidal Human] Clicked first clickable frame at ({cx},{cy})")

    add_log("INFO", udid, f"[Tidal Human] Looking for Play button...")

    already_playing = False
    mini_check = d(resourceId='com.aspiro.tidal:id/miniPlayerPlay')
    if mini_check.exists(timeout=2):
        mdesc = str(mini_check.info.get('contentDescription', ''))
        if 'Pausar' in mdesc or 'Pause' in mdesc:
            already_playing = True
            add_log("INFO", udid, f"[Tidal Human] Already playing (mini player Pause)")

    if not already_playing:
        for attempt in range(4):
            d.swipe(540, 1400, 540, 600, duration=random.uniform(0.4, 0.7))
            _human_delay(1.0, 1.5)

            repro_btn = d(text='Reproducir')
            if repro_btn.exists(timeout=2):
                info = repro_btn.info
                bounds = info.get('bounds', {})
                cx = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
                cy = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
                parent_y = bounds.get('top', 0)
                d.click(cx, cy)
                _human_delay(1.5, 3.0)
                add_log("SUCC", udid, f"[Tidal Human] Clicked 'Reproducir' at ({cx},{cy})")
                return True

            shuffle_btn = d(text='Aleatorio')
            if shuffle_btn.exists(timeout=2):
                info = shuffle_btn.info
                bounds = info.get('bounds', {})
                cx = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
                cy = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
                d.click(cx, cy)
                _human_delay(1.5, 3.0)
                add_log("SUCC", udid, f"[Tidal Human] Clicked 'Aleatorio' at ({cx},{cy})")
                return True

            album_play = d(resourceId='com.aspiro.tidal:id/playbackControlButtonFirst')
            if album_play.exists(timeout=2):
                album_play.click()
                _human_delay(1.5, 3.0)
                add_log("SUCC", udid, f"[Tidal Human] playbackControlButtonFirst tapped")
                return True

            play_desc = d(descriptionContains='Play')
            if play_desc.exists(timeout=2):
                pinfo = play_desc.info
                pdesc = str(pinfo.get('contentDescription', ''))
                if 'Pausar' not in pdesc and 'Pause' not in pdesc:
                    pb = pinfo.get('bounds', {})
                    pcx = (pb.get('left', 0) + pb.get('right', 0)) // 2
                    pcy = (pb.get('top', 0) + pb.get('bottom', 0)) // 2
                    d.click(pcx, pcy)
                    _human_delay(1.5, 3.0)
                    add_log("SUCC", udid, f"[Tidal Human] Play desc tapped at ({pcx},{pcy})")
                    return True

            _human_delay(1.5, 2.5)

    add_log("WARN", udid, "[Tidal Human] Play button not found after all attempts")
    return False


def _open_apple_human(d, udid, link, artist_name=None, album_name=None):
    """Open Apple Music via deep link intent, find and tap play. All human-like."""
    _adb_go_home(udid)
    _human_delay(0.5, 1.0)

    link_type, slug = _parse_link_info(link)

    add_log("INFO", udid, f"[Apple Music Human] Opening {link_type} via intent...")
    _adb_shell(udid, f'am start -a android.intent.action.VIEW -d "{link}" com.apple.android.music')
    _human_delay(5.0, 7.0)
    ensure_screen_on(d)

    # For albums/playlists, scroll down a bit to show track listing
    if link_type in ('Album', 'Playlist'):
        _human_delay(0.5, 1.0)
        for _ in range(random.randint(1, 2)):
            d.swipe(540, 1400, 540, 800, duration=random.uniform(0.4, 0.7))
            _human_delay(0.8, 1.5)

    play_btn = (d(resourceId='com.apple.android.music:id/button_play') or
                d(description='Reproducir') or d(description='Play') or
                d(descriptionContains='Reproducir') or d(descriptionContains='Play'))
    if play_btn.exists(timeout=5):
        info = play_btn.info
        desc = str(info.get('contentDescription', '') or '')
        if 'Pause' in desc or 'Pausar' in desc:
            add_log("INFO", udid, f"[Apple Music Human] Already playing")
            return True
        pb = info.get('bounds', {})
        cx = (pb.get('left', 0) + pb.get('right', 0)) // 2
        cy = (pb.get('top', 0) + pb.get('bottom', 0)) // 2
        d.click(cx, cy)
        add_log("SUCC", udid, f"[Apple Music Human] Play button tapped at ({cx},{cy})")
        _human_delay(1.0, 2.0)
        return True

    mini_pause = d(descriptionContains='Pause') or d(descriptionContains='Pausar')
    if mini_pause.exists(timeout=3):
        add_log("INFO", udid, f"[Apple Music Human] Already playing (pause visible)")
        return True

    # Fallback: try mini player play button
    mini_play = d(resourceId='com.apple.android.music:id/mini_player_play')
    if mini_play.exists(timeout=3):
        bi = mini_play.info['bounds']
        cx = (bi['left'] + bi['right']) // 2
        cy = (bi['top'] + bi['bottom']) // 2
        d.click(cx, cy)
        add_log("SUCC", udid, f"[Apple Music Human] Mini player play tapped at ({cx},{cy})")
        _human_delay(1.0, 2.0)
        return True

    _adb_media_next(udid)
    _human_delay(1.0, 2.0)
    add_log("SUCC", udid, f"[Apple Music Human] {link_type} opened via intent, NEXT sent")
    return True


_MULTI_AUDIO_DEX_B64 = (
    'ZGV4CjAzNQDqUdt9kQz44m03Tr6NyoYxCHPdQBsrid0MDQAAcAAAAHhWNBIAAAAAAAAAAEgMAABF'
    'AAAAcAAAABQAAACEAQAADwAAANQBAAAEAAAAiAIAABMAAACoAgAAAQAAAEADAACsCQAAYAMAAC4H'
    'AAAyBwAAOAcAADsHAAA+BwAARgcAAHIHAACSBwAAvAcAAOgHAAADCAAAFwgAABoIAAAeCAAAIwgA'
    'ADQIAAA4CAAAVAgAAGsIAACACAAAmggAAK0IAADECAAA5wgAAPsIAAAPCQAAKgkAAD4JAABaCQAA'
    'bgkAAKAJAAC0CQAAwQkAAMcJAADNCQAA0AkAANQJAADXCQAA2wkAAO8JAAAECgAAGQoAADYKAABY'
    'CgAAbAoAAIcKAACPCgAAnAoAAKMKAACtCgAAsgoAALkKAADCCgAAzAoAANcKAADjCgAA7AoAAP8K'
    'AAALCwAAEwsAABkLAAAgCwAAJQsAAC4LAABJCwAAVgsAAGALAABnCwAAcAsAAA4AAAAQAAAAEQAA'
    'ABIAAAATAAAAFAAAABUAAAAWAAAAFwAAABgAAAAZAAAAGgAAABsAAAAcAAAAIgAAACQAAAAmAAAA'
    'JwAAACgAAAApAAAADwAAAAMAAADwBgAACwAAAAUAAAAAAAAADAAAAAUAAAD4BgAADQAAAAgAAAAA'
    'BwAACwAAAAkAAAAAAAAADAAAAAkAAAAIBwAADAAAAAkAAAAQBwAADAAAAAoAAAD4BgAADQAAAAwA'
    'AAAYBwAAIgAAAA4AAAAAAAAAIwAAAA4AAAD4BgAAIwAAAA4AAAAgBwAAJQAAAA8AAAAoBwAACwAA'
    'ABAAAAAAAAAACwAAABMAAAAAAAAAAwADACAAAAADAAUAIQAAAAsAAgAxAAAACwACAD0AAAAAAAkA'
    'BAAAAAAACwA7AAAAAgAKAD4AAAADAAAAQwAAAAUAAgAzAAAABQAIADUAAAAFAA4ANgAAAAgACQAE'
    'AAAACAABADQAAAAJAAwAMAAAAAkABABAAAAACQAFAEMAAAAKAAkABAAAAAoABwAtAAAACgAEAEEA'
    'AAAMAAQANwAAAAwADQA4AAAADAADADoAAAANAAYAQQAAAAAAAAABAAAACAAAAAAAAAAeAAAAMAwA'
    'ABYMAAAAAAAAAQABAAEAAACxBgAABAAAAHAQBwAAAA4ADwABAAMAAgC1BgAAiAEAABoOHQAaAAUA'
    'GgE/AGICAwAaAx8AbiACADIAGgIsAHEQBAACAAwCEhMjNBAAHAUJABIGTQUEBhoFOQBuMAUAUgQM'
    'AiM0EQAaBS8ATQUEBhIFbjARAFIEDAI5AgoAYg4CABoABgBuIAIADgAOAGIEAwBxEAsAAgAMByII'
    'CgBwEAwACAAaCQoAbiANAJgADAhuIA0AeAAMB24QDgAHAAwHbiACAHQAGgQqAHEQBAAEAAwEIzcQ'
    'ABoIKwBxEAQACAAMCE0IBwYaCC4AbjAFAIQHDAQjNxEATQIHBm4wEQBUBwwCOQIKAGIOAgAaAAcA'
    'biACAA4ADgBiBAMAcRALAAIADAUiBwoAcBAMAAcAGggJAG4gDQCHAAwHbiANAFcADAVuEA4ABQAM'
    'BW4gAgBUAG4QCAACAAwEbhAGAAQADAUhVxIIGgkyABoKAAAaCzwANXhHAEYMBQhuEA8ADAAMDW4Q'
    'CgANAAwNbiAJAL0ACgs5CwgAbiAJAJ0ACgk4CS4AYgkDAG4QDwAMAAwLbhAQAAwADAxxEBIADAAM'
    'DCINCgBwEAwADQBuIA0ArQAMCm4gDQC6AAwKGgsBAG4gDQC6AAwKbiANAMoADApuEA4ACgAMCm4g'
    'AgCpANgICAEotCM1EAAcBwMATQcFBm4wBQAUBQwFYgcDAG4gAgAHACM3EQBiCAAATQgHBm4wEQAl'
    'B2IFAwBuIAIA5QApAH0ADQUjNRAAYgcBAE0HBQZuMAUAFAUMAWIFAwBuIAIABQBxEAMAAwAMACMz'
    'EQBNAAMGbjARACEDYgADAG4gAgDgAChbDQ5iDgIAGgAIAG4gAgAOAG4QBgAEAAwOIeA1Bk0ARgEO'
    'Bm4QDwABAAwCbhAKAAIADAJuIAkAsgAKAzkDCABuIAkAkgAKAjgCNABiAgIAbhAPAAEADANuEBAA'
    'AQAMAXEQEgABAAwBIgQKAHAQDAAEAG4gDQCkAAwEbiANADQADAMaBAIAbiANAEMADANuIA0AEwAM'
    'ARoDAwBuIA0AMQAMAW4QDgABAAwBbiACABIA2AYGASi0DgDtAAAAHQABAA0BAAAfAAUAAgEHjAIB'
    'B60CAwAOAAUBAA7TaeG1LXgfARwRaf+ILXgfARwQS/+HwwEsC0OlWpYCEFkCcSwfpVq0YgJ4HR54'
    'lofDATILQwAAAQAAAA8AAAABAAAACQAAAAIAAAAIABEAAQAAAAgAAAABAAAAEQAAAAIAAAAJABAA'
    'AQAAABIAAAABAAAABAACICAABCAtPiAAASgAASkABjxpbml0PgAqQ2FsbGluZyBzZXRNdWx0aUF1'
    'ZGlvRm9jdXNFbmFibGVkKHRydWUpLi4uAB5FUlJPUjogYXVkaW8gc2VydmljZSBub3QgZm91bmQA'
    'KEVSUk9SOiBjb3VsZCBub3QgZ2V0IGF1ZGlvIHNlcnZpY2UgcHJveHkAKkVSUk9SOiBzZXRNdWx0'
    'aUF1ZGlvRm9jdXNFbmFibGVkIG5vdCBmb3VuZAAZR290IElBdWRpb1NlcnZpY2UgcHJveHk6IAAS'
    'R290IGF1ZGlvIGJpbmRlcjogAAFMAAJMTAADTExMAA9MU2V0TXVsdGlBdWRpbzsAAkxaABpMZGFs'
    'dmlrL2Fubm90YXRpb24vVGhyb3dzOwAVTGphdmEvaW8vUHJpbnRTdHJlYW07ABNMamF2YS9sYW5n'
    'L0Jvb2xlYW47ABhMamF2YS9sYW5nL0NoYXJTZXF1ZW5jZTsAEUxqYXZhL2xhbmcvQ2xhc3M7ABVM'
    'amF2YS9sYW5nL0V4Y2VwdGlvbjsAIUxqYXZhL2xhbmcvTm9TdWNoTWV0aG9kRXhjZXB0aW9uOwAS'
    'TGphdmEvbGFuZy9PYmplY3Q7ABJMamF2YS9sYW5nL1N0cmluZzsAGUxqYXZhL2xhbmcvU3RyaW5n'
    'QnVpbGRlcjsAEkxqYXZhL2xhbmcvU3lzdGVtOwAaTGphdmEvbGFuZy9yZWZsZWN0L01ldGhvZDsA'
    'EkxqYXZhL3V0aWwvQXJyYXlzOwAwU1VDQ0VTUyEgc2V0TXVsdGlBdWRpb0ZvY3VzRW5hYmxlZCh0'
    'cnVlKSBjYWxsZWQhABJTZXRNdWx0aUF1ZGlvLmphdmEAC1N0YXJ0aW5nLi4uAARUUlVFAARUWVBF'
    'AAFWAAJWTAABWgACWkwAEltMamF2YS9sYW5nL0NsYXNzOwATW0xqYXZhL2xhbmcvT2JqZWN0OwAT'
    'W0xqYXZhL2xhbmcvU3RyaW5nOwAbW0xqYXZhL2xhbmcvcmVmbGVjdC9NZXRob2Q7ACBhbmRyb2lk'
    'Lm1lZGlhLklBdWRpb1NlcnZpY2UkU3R1YgASYW5kcm9pZC5vcy5JQmluZGVyABlhbmRyb2lkLm9z'
    'LlNlcnZpY2VNYW5hZ2VyAAZhcHBlbmQAC2FzSW50ZXJmYWNlAAVhdWRpbwAIY29udGFpbnMAA2Vy'
    'cgAFZm9jdXMAB2Zvck5hbWUACGdldENsYXNzAAlnZXRNZXRob2QACmdldE1ldGhvZHMAB2dldE5h'
    'bWUAEWdldFBhcmFtZXRlclR5cGVzAApnZXRTZXJ2aWNlAAZpbnZva2UABG1haW4ABW11bHRpAANv'
    'dXQAB3ByaW50bG4AGXNldE11bHRpQXVkaW9Gb2N1c0VuYWJsZWQAC3RvTG93ZXJDYXNlAAh0b1N0'
    'cmluZwAFdmFsdWUAB3ZhbHVlT2YAmwF+fkQ4eyJiYWNrZW5kIjoiZGV4IiwiY29tcGlsYXRpb24t'
    'bW9kZSI6ImRlYnVnIiwiaGFzLWNoZWNrc3VtcyI6ZmFsc2UsIm1pbi1hcGkiOjEsInNoYS0xIjoi'
    'MDg0YTg5MTI2YWUwNTk2YzU5OTE0M2RmNTdhNjU0NjQ2YWYyODMxMyIsInZlcnNpb24iOiI5LjIu'
    'NC1kZXYifQACAQFCHAEYBgAAAgAAgYAE4AYBCfgGAAAAAAEAAAAODAAAJAwAAAAAAAABAAAAAAAA'
    'AAEAAAAoDAAAEAAAAAAAAAABAAAAAAAAAAEAAABFAAAAcAAAAAIAAAAUAAAAhAEAAAMAAAAPAAAA'
    '1AEAAAQAAAAEAAAAiAIAAAUAAAATAAAAqAIAAAYAAAABAAAAQAMAAAEgAAACAAAAYAMAAAMgAAAC'
    'AAAAsQYAAAEQAAAIAAAA8AYAAAIgAABFAAAALgcAAAQgAAABAAAADgwAAAAgAAABAAAAFgwAAAMQ'
    'AAACAAAAJAwAAAYgAAABAAAAMAwAAAAQAAABAAAASAwAAA=='
)


def _enable_multi_audio_focus(udid):
    """Enable Samsung Multi Audio Focus on a device via app_process reflection.
    This calls IAudioService.setMultiAudioFocusEnabled(true) directly via binder,
    bypassing the need for Sound Assistant / Knox. Requires root."""
    try:
        out = _adb_shell(udid, 'dumpsys audio')
        if 'Multi Audio Focus enabled :true' in out:
            return True
    except:
        pass

    try:
        uid_out = _adb_shell(udid, 'id')
        if 'uid=0' not in uid_out:
            subprocess.run([adb_path, '-s', udid, 'root'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
                           startupinfo=startupinfo)
            time.sleep(2)
    except:
        pass

    try:
        import base64
        dex_data = base64.b64decode(_MULTI_AUDIO_DEX_B64)
        tmp_dex = os.path.join(os.environ.get('TEMP', os.path.dirname(__file__)), '_multi_focus.dex')
        with open(tmp_dex, 'wb') as f:
            f.write(dex_data)

        subprocess.run([adb_path, '-s', udid, 'push', tmp_dex, '/data/local/tmp/_multi_focus.dex'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                       startupinfo=startupinfo)
        _adb_shell(udid, 'chmod 644 /data/local/tmp/_multi_focus.dex')
        subprocess.run([adb_path, '-s', udid, 'shell',
                        'CLASSPATH=/data/local/tmp/_multi_focus.dex app_process / SetMultiAudio'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                       startupinfo=startupinfo)

        time.sleep(1)
        out = _adb_shell(udid, 'dumpsys audio')
        if 'Multi Audio Focus enabled :true' in out:
            add_log("SUCC", udid, "[MultiApp] Multi Audio Focus ENABLED on device")
            return True
        else:
            add_log("WARN", udid, "[MultiApp] Multi Audio Focus call succeeded but state not confirmed")
            return True
    except Exception as e:
        add_log("ERR.", udid, f"[MultiApp] Failed to enable Multi Audio Focus: {e}")
        return False


def _multi_app_start_all(selected_apps_keys, udid, binded_account, binded_proxy, connection_type, account_type):
    """Launch all selected apps in RANDOM order with human-like behavior.
    Each app: go home -> open like a human -> play from its specific link type.
    Both apps keep playing audio simultaneously via Multi Audio Focus."""
    ui_lock = _get_device_ui_lock(udid)

    if len(selected_apps_keys) > 1:
        _enable_multi_audio_focus(udid)

    _ensure_volume_max(udid)
    add_log("INFO", udid, "[MultiApp] Volume set to max")

    shuffled_apps = list(selected_apps_keys)
    random.shuffle(shuffled_apps)
    add_log("INFO", udid, f"[MultiApp] Launch order: {[SUPPORTED_APPS[k]['display_name'] for k in shuffled_apps]}")

    link_info_by_app = {}

    for app_key in shuffled_apps:
        if stop_flags.get(f"{udid}_{app_key}") or stop_flags.get(udid):
            break

        app_info = SUPPORTED_APPS.get(app_key)
        if not app_info:
            continue
        pkg = app_info['package']
        display_name = app_info['display_name']

        add_log("INFO", udid, f"[MultiApp] Setting up {display_name} (human mode)...")

        ui_lock.acquire()
        try:
            d = ua.connect(udid)
            ensure_screen_on(d)
            d.set_input_ime(True)
            freeze_rotation_port(d)

            _app_generic_restart_if_crashed(d, False, pkg)
            _human_delay(1.0, 2.5)

            if pkg == 'com.aspiro.tidal':
                link = _get_random_tidal_link()
                if link:
                    link_type, slug = _parse_link_info(link)
                    songs = _songs_for_type(link_type)
                    artist_name, album_name = _scrape_link_info(link)
                    if not artist_name:
                        artist_name, album_name = slug, link_type
                    add_log("INFO", udid, f"[MultiApp] Tidal {link_type} ({songs} songs): {artist_name} - {album_name}")
                    _open_tidal_human(d, udid, link, artist_name, album_name)
                    link_info_by_app['tidal'] = {'type': link_type, 'total_songs': songs, 'remaining': songs, 'link': link}
                    add_log("SUCC", udid, f"[MultiApp] Tidal playing: {artist_name} - {album_name}")
                else:
                    add_log("ERR.", udid, "[MultiApp] No Tidal links found")

            elif pkg == 'com.apple.android.music':
                link = _get_random_apple_link()
                if link:
                    link_type, slug = _parse_link_info(link)
                    songs = _songs_for_type(link_type)
                    artist_name, album_name = _scrape_link_info(link)
                    if not artist_name:
                        artist_name, album_name = slug, link_type
                    add_log("INFO", udid, f"[MultiApp] Apple Music {link_type} ({songs} songs): {artist_name} - {album_name}")
                    _open_apple_human(d, udid, link, artist_name, album_name)
                    link_info_by_app['apple_music'] = {'type': link_type, 'total_songs': songs, 'remaining': songs, 'link': link}
                    add_log("SUCC", udid, f"[MultiApp] Apple Music playing: {artist_name} - {album_name}")
                else:
                    add_log("ERR.", udid, "[MultiApp] No Apple Music links found")

            else:
                link = get_random_link()
                if link:
                    link_type, artist_name, album_name, song_count = artist_links_function(link, None, None, None, None)
                    songs = _songs_for_type(link_type, song_count)
                    add_log("INFO", udid, f"[MultiApp] Spotify {link_type} ({songs} songs): {artist_name} - {album_name}")
                    _open_spotify_human(d, udid, link, artist_name, album_name, link_type=link_type)
                    link_info_by_app['spotify'] = {'type': link_type, 'total_songs': songs, 'remaining': songs, 'link': link}
                    add_log("SUCC", udid, f"[MultiApp] Spotify playing: {artist_name} - {album_name}")
                else:
                    add_log("ERR.", udid, "[MultiApp] No Spotify links found")

            _human_delay(2.0, 5.0)
            add_log("INFO", udid, f"[MultiApp] {display_name} playing. NOT going home.")
        except Exception as e:
            add_log("ERR.", udid, f"[MultiApp] Failed setting up {display_name}: {e}")
        finally:
            ui_lock.release()

        time.sleep(random.uniform(3.0, 8.0))

    add_log("SUCC", udid, f"[MultiApp] All apps launched on {udid}. Both playing simultaneously.")
    return link_info_by_app


def _multi_app_relink_app(d, udid, app_key, pkg, display_name):
    """Load a fresh link into an app with human-like behavior. Assumes ui_lock is held and app is in foreground."""
    link_info_by_app = getattr(_multi_app_relink_app, '_link_info', {})
    if app_key == 'tidal':
        link = _get_random_tidal_link()
        if link:
            link_type, slug = _parse_link_info(link)
            songs = _songs_for_type(link_type)
            artist_name, album_name = _scrape_link_info(link)
            if not artist_name:
                artist_name, album_name = slug, link_type
            _open_tidal_human(d, udid, link, artist_name, album_name)
            link_info_by_app[app_key] = {'type': link_type, 'total_songs': songs, 'remaining': songs, 'link': link}
            _multi_app_relink_app._link_info = link_info_by_app
            add_log("INFO", udid, f"[MultiApp] [{display_name}] New {link_type} ({songs} songs): {artist_name} - {album_name}")
            return True
        else:
            add_log("ERR.", udid, f"[MultiApp] [{display_name}] No links available")
            return False
    elif app_key == 'apple_music':
        link = _get_random_apple_link()
        if link:
            link_type, slug = _parse_link_info(link)
            songs = _songs_for_type(link_type)
            artist_name, album_name = _scrape_link_info(link)
            if not artist_name:
                artist_name, album_name = slug, link_type
            _open_apple_human(d, udid, link, artist_name, album_name)
            link_info_by_app[app_key] = {'type': link_type, 'total_songs': songs, 'remaining': songs, 'link': link}
            _multi_app_relink_app._link_info = link_info_by_app
            add_log("INFO", udid, f"[MultiApp] [{display_name}] New {link_type} ({songs} songs): {artist_name} - {album_name}")
            return True
        else:
            add_log("ERR.", udid, f"[MultiApp] [{display_name}] No links available")
            return False
    else:
        link = get_random_link()
        if link:
            link_type, artist_name, album_name, song_count = artist_links_function(link, None, None, None, None)
            songs = _songs_for_type(link_type, song_count)
            _open_spotify_human(d, udid, link, artist_name, album_name, link_type=link_type)
            link_info_by_app[app_key] = {'type': link_type, 'total_songs': songs, 'remaining': songs, 'link': link}
            _multi_app_relink_app._link_info = link_info_by_app
            add_log("INFO", udid, f"[MultiApp] [{display_name}] New {link_type} ({songs} songs): {artist_name} - {album_name}")
            return True
        else:
            add_log("ERR.", udid, f"[MultiApp] [{display_name}] No links available")
            return False


def _multi_app_next_song(udid, app_key, pkg, display_name):
    """Advance to next song with human-like behavior. Quick foreground visit then back to random app."""
    ui_lock = _get_device_ui_lock(udid)
    ui_lock.acquire()
    try:
        d = ua.connect(udid)
        _human_launch_app(d, udid, pkg)
        _human_delay(1.5, 3.5)

        next_btn = (d(description='Next') or d(description='Siguiente') or
                    d(description='Skip') or d(description='Adelante'))
        if next_btn.exists(timeout=3):
            _human_delay(0.2, 0.6)
            next_btn.click()
            add_log("INFO", udid, f"[MultiApp] [{display_name}] NEXT via UI")
        else:
            _adb_media_next(udid)
            add_log("INFO", udid, f"[MultiApp] [{display_name}] NEXT via ADB (fallback)")

        _human_delay(1.0, 2.5)
        add_log("INFO", udid, f"[MultiApp] [{display_name}] NEXT done")
    except Exception as e:
        add_log("ERR.", udid, f"[MultiApp] [{display_name}] Error sending NEXT: {e}")
    finally:
        ui_lock.release()


def _multi_app_relaunch_after_link(udid, app_key, pkg, display_name):
    """Reload a fresh link into an app with human-like behavior."""
    ui_lock = _get_device_ui_lock(udid)
    ui_lock.acquire()
    try:
        _ensure_volume_max(udid)
        d = ua.connect(udid)
        _human_launch_app(d, udid, pkg)
        _human_delay(2.0, 4.0)
        d = ua.connect(udid)
        _multi_app_relink_app(d, udid, app_key, pkg, display_name)
        _human_delay(1.0, 3.0)
        add_log("INFO", udid, f"[MultiApp] [{display_name}] Relink done")
    except Exception as e:
        add_log("ERR.", udid, f"[MultiApp] [{display_name}] Relink error: {e}")
    finally:
        ui_lock.release()


def _multi_app_try_like_follow(d, udid, app_key, pkg, display_name):
    """Randomly like or follow during a stream. Human-like: scroll, pause, tap."""
    global config_album_likes_rate, config_song_likes_rate, config_follows_rate

    try:
        if random.random() < 0.15:
            like_btn = d(description='Add to your library') or d(description='Añadir a tu biblioteca') or d(resourceId=f'{pkg}:id/like_button')
            if like_btn.exists(timeout=2):
                _human_delay(0.5, 1.5)
                like_btn.click()
                add_log("INFO", udid, f"[MultiApp] [{display_name}] Liked song (random)")
                _human_delay(1.0, 2.5)

        if random.random() < 0.05:
            follow_btn = d(text='Follow') or d(text='Seguir')
            if follow_btn.exists(timeout=2):
                _human_delay(0.5, 1.5)
                follow_btn.click()
                add_log("INFO", udid, f"[MultiApp] [{display_name}] Followed artist (random)")
                _human_delay(1.0, 2.0)
    except:
        pass


def _multi_app_monitor_all(selected_apps_keys, udid, session_time_seconds):
    """Fully randomized multi-app monitor. Both apps play simultaneously.
    Tracks per-link song counts based on link type (album/track/playlist).
    Everything is varied: timing, order, actions. No fixed patterns."""
    global worker_streams_done, worker_streams_done_spotify, worker_streams_done_tidal, worker_streams_done_apple, config_streams_to_do

    session_start = time.time()
    num_apps = len(selected_apps_keys)

    app_timers = {}
    app_stream_counts = {}
    app_relink_counters = {}
    app_total_songs_in_link = {}
    app_next_action_time = {}
    app_link_types = {}

    for app_key in selected_apps_keys:
        app_timers[app_key] = time.time()
        app_stream_counts[app_key] = 0
        initial_songs = random.randint(8, 25)
        app_relink_counters[app_key] = initial_songs
        app_total_songs_in_link[app_key] = initial_songs
        app_next_action_time[app_key] = time.time() + random.uniform(30, 120)
        app_link_types[app_key] = 'Unknown'

    link_info = getattr(_multi_app_relink_app, '_link_info', {})
    for app_key in selected_apps_keys:
        if app_key in link_info:
            info = link_info[app_key]
            app_relink_counters[app_key] = info.get('remaining', random.randint(8, 25))
            app_total_songs_in_link[app_key] = info.get('total_songs', app_relink_counters[app_key])
            app_link_types[app_key] = info.get('type', 'Unknown')

    add_log("INFO", udid, f"[MultiApp] Monitor started. {num_apps} apps, session {session_time_seconds}s. Link types: {app_link_types}")

    last_health_check = time.time()
    health_interval = random.uniform(15, 30)
    app_last_good_time = {}
    app_consecutive_bad = {}
    app_forcestop_count = {}
    app_last_forcestop_time = {}
    for app_key in selected_apps_keys:
        app_last_good_time[app_key] = time.time()
        app_consecutive_bad[app_key] = 0
        app_forcestop_count[app_key] = 0
        app_last_forcestop_time[app_key] = 0

    while (time.time() - session_start) < session_time_seconds:
        if stop_flags.get(udid):
            break

        now = time.time()

        for app_key in selected_apps_keys:
            if stop_flags.get(udid):
                break
            if stop_flags.get(f"{udid}_{app_key}"):
                continue

            app_info = SUPPORTED_APPS.get(app_key)
            if not app_info:
                continue
            pkg = app_info['package']
            display_name = app_info['display_name']

            playtime1, playtime2 = _get_playtime_for_app(app_key)
            base_playtime = playtime1 if playtime1 == playtime2 else random.randrange(playtime1, playtime2)
            actual_playtime = base_playtime * random.uniform(0.6, 1.4)
            actual_playtime = max(20, actual_playtime)

            elapsed = now - app_timers.get(app_key, session_start)

            if elapsed >= actual_playtime and now >= app_next_action_time.get(app_key, 0):
                worker_streams_done += 1
                if app_key == 'spotify':
                    worker_streams_done_spotify += 1
                elif app_key == 'tidal':
                    worker_streams_done_tidal += 1
                elif app_key == 'apple_music':
                    worker_streams_done_apple += 1
                if config_streams_to_do > 0:
                    config_streams_to_do -= 1
                app_stream_counts[app_key] = app_stream_counts.get(app_key, 0) + 1
                app_timers[app_key] = now
                app_relink_counters[app_key] = app_relink_counters.get(app_key, 15) - 1

                update_thread_status(udid, f'[MultiApp] {display_name} streaming', None, False, True, False, False, False, None)
                add_log("SUCC", udid, f"[MultiApp] [{display_name}] Stream #{app_stream_counts[app_key]} done | Link: {app_link_types.get(app_key, '?')} | Left in link: {app_relink_counters[app_key]}")

                if app_relink_counters[app_key] <= 0:
                    add_log("INFO", udid, f"[MultiApp] [{display_name}] Reloading (was {app_link_types.get(app_key, '?')} with {app_total_songs_in_link[app_key]} songs)...")
                    _multi_app_relaunch_after_link(udid, app_key, pkg, display_name)
                    link_info_new = getattr(_multi_app_relink_app, '_link_info', {})
                    if app_key in link_info_new:
                        info = link_info_new[app_key]
                        app_relink_counters[app_key] = info.get('remaining', random.randint(8, 25))
                        app_total_songs_in_link[app_key] = info.get('total_songs', app_relink_counters[app_key])
                        app_link_types[app_key] = info.get('type', 'Unknown')
                    else:
                        new_songs = random.randint(8, 25)
                        app_relink_counters[app_key] = new_songs
                        app_total_songs_in_link[app_key] = new_songs
                elif app_key == 'spotify':
                    _adb_media_next(udid)
                    add_log("INFO", udid, f"[MultiApp] [Spotify] NEXT via ADB media")
                else:
                    _multi_app_next_song(udid, app_key, pkg, display_name)

                app_next_action_time[app_key] = now + random.uniform(30, 120)

                if random.random() < 0.2:
                    ui_lock = _get_device_ui_lock(udid)
                    ui_lock.acquire()
                    try:
                        d = ua.connect(udid)
                        _human_launch_app(d, udid, pkg)
                        _human_delay(2.0, 5.0)
                        d = ua.connect(udid)
                        _multi_app_try_like_follow(d, udid, app_key, pkg, display_name)
                        _human_delay(1.0, 3.0)
                    except:
                        pass
                    finally:
                        ui_lock.release()

        time.sleep(random.uniform(2, 6))

        now2 = time.time()
        if now2 - last_health_check >= health_interval:
            last_health_check = now2
            health_interval = random.uniform(15, 30)
            status_parts = []
            for app_key in selected_apps_keys:
                pkg = SUPPORTED_APPS[app_key]['package']
                dn = SUPPORTED_APPS[app_key]['display_name']
                state, title, artist = _get_now_playing(udid, pkg)
                if state == 'PLAYING':
                    if app_forcestop_count.get(app_key, 0) > 0 and (now2 - app_last_forcestop_time.get(app_key, 0)) > 300:
                        app_forcestop_count[app_key] = 0
                    app_last_good_time[app_key] = now2
                    app_consecutive_bad[app_key] = 0
                    is_recommendation = False
                    if title:
                        combined = f"{title} {artist}".lower()
                        if any(kw in combined for kw in ['recomendaci', 'recommended', 'para ti', 'for you', 'radio', 'my mix', 'daily mix', 'discover weekly', 'release radar', 'mix de']):
                            is_recommendation = True
                        status_parts.append(f"{dn}: '{title}' by {artist}")
                    else:
                        status_parts.append(f"{dn}: PLAYING (no title)")
                    if is_recommendation:
                        add_log("WARN", udid, f"[MultiApp] [{dn}] Playing recommendations instead of link. Forcing relink...")
                        try:
                            ui_lock = _get_device_ui_lock(udid)
                            ui_lock.acquire()
                            try:
                                _multi_app_relaunch_after_link(udid, app_key, pkg, dn)
                                link_info_new = getattr(_multi_app_relink_app, '_link_info', {})
                                if app_key in link_info_new:
                                    info = link_info_new[app_key]
                                    app_relink_counters[app_key] = info.get('remaining', random.randint(8, 25))
                                    app_total_songs_in_link[app_key] = info.get('total_songs', app_relink_counters[app_key])
                                    app_link_types[app_key] = info.get('type', 'Unknown')
                                app_consecutive_bad[app_key] = 0
                                app_last_good_time[app_key] = time.time()
                                add_log("SUCC", udid, f"[MultiApp] [{dn}] Relinked from recommendations to fresh link")
                            finally:
                                ui_lock.release()
                        except Exception as e:
                            add_log("ERR.", udid, f"[MultiApp] [{dn}] Recommendation relink failed: {e}")
                elif state == 'BUFFERING':
                    seconds_stuck = now2 - app_last_good_time.get(app_key, now2)
                    if seconds_stuck > 30:
                        app_consecutive_bad[app_key] = app_consecutive_bad.get(app_key, 0) + 1
                        status_parts.append(f"{dn}: BUFFERING STUCK ({int(seconds_stuck)}s, {app_consecutive_bad[app_key]}x)")
                        if app_consecutive_bad[app_key] >= 2:
                            fs_count = app_forcestop_count.get(app_key, 0)
                            fs_last = app_last_forcestop_time.get(app_key, 0)
                            if fs_count >= 3 and (now2 - fs_last) < 300:
                                add_log("WARN", udid, f"[MultiApp] [{dn}] BUFFERING stuck but force-stop cooldown active ({fs_count}x in 5min). Skipping recovery.")
                            else:
                                add_log("WARN", udid, f"[MultiApp] [{dn}] BUFFERING stuck for {int(seconds_stuck)}s. Force-stop + relaunch...")
                                app_forcestop_count[app_key] = fs_count + 1
                                app_last_forcestop_time[app_key] = now2
                                try:
                                    ui_lock = _get_device_ui_lock(udid)
                                    ui_lock.acquire()
                                    try:
                                        _ensure_volume_max(udid)
                                        _adb_shell(udid, f'am force-stop {pkg}')
                                        time.sleep(2)
                                        _enable_multi_audio_focus(udid)
                                        _multi_app_relaunch_after_link(udid, app_key, pkg, dn)
                                        link_info_new = getattr(_multi_app_relink_app, '_link_info', {})
                                        if app_key in link_info_new:
                                            info = link_info_new[app_key]
                                            app_relink_counters[app_key] = info.get('remaining', random.randint(8, 25))
                                            app_total_songs_in_link[app_key] = info.get('total_songs', app_relink_counters[app_key])
                                            app_link_types[app_key] = info.get('type', 'Unknown')
                                        app_consecutive_bad[app_key] = 0
                                        app_last_good_time[app_key] = time.time()
                                        add_log("SUCC", udid, f"[MultiApp] [{dn}] Recovery complete after BUFFERING stuck")
                                    finally:
                                        ui_lock.release()
                                except Exception as e:
                                    add_log("ERR.", udid, f"[MultiApp] [{dn}] Recovery failed: {e}")
                        elif app_consecutive_bad[app_key] == 1:
                            add_log("WARN", udid, f"[MultiApp] [{dn}] BUFFERING stuck for {int(seconds_stuck)}s. Sending NEXT...")
                            try:
                                if app_key == 'spotify':
                                    _adb_media_next(udid)
                                else:
                                    _multi_app_next_song(udid, app_key, pkg, dn)
                            except Exception as e:
                                add_log("ERR.", udid, f"[MultiApp] [{dn}] Soft NEXT failed: {e}")
                    else:
                        status_parts.append(f"{dn}: BUFFERING ({int(seconds_stuck)}s)")
                else:
                    app_consecutive_bad[app_key] = app_consecutive_bad.get(app_key, 0) + 1
                    seconds_since_good = now2 - app_last_good_time.get(app_key, now2)
                    status_parts.append(f"{dn}: {state} ({app_consecutive_bad[app_key]}x)")
                    if app_consecutive_bad[app_key] >= 2 and seconds_since_good > 60:
                        if state in ('STOPPED', 'PAUSED', 'ERROR'):
                            fs_count = app_forcestop_count.get(app_key, 0)
                            fs_last = app_last_forcestop_time.get(app_key, 0)
                            if fs_count >= 3 and (now2 - fs_last) < 300:
                                add_log("WARN", udid, f"[MultiApp] [{dn}] {state} but force-stop cooldown active ({fs_count}x in 5min). Skipping recovery.")
                            else:
                                add_log("WARN", udid, f"[MultiApp] [{dn}] {state} for {int(seconds_since_good)}s. Full recovery...")
                                app_forcestop_count[app_key] = fs_count + 1
                                app_last_forcestop_time[app_key] = now2
                                try:
                                    ui_lock = _get_device_ui_lock(udid)
                                    ui_lock.acquire()
                                    try:
                                        _ensure_volume_max(udid)
                                        _adb_shell(udid, f'am force-stop {pkg}')
                                        time.sleep(2)
                                        _enable_multi_audio_focus(udid)
                                        _multi_app_relaunch_after_link(udid, app_key, pkg, dn)
                                        link_info_new = getattr(_multi_app_relink_app, '_link_info', {})
                                        if app_key in link_info_new:
                                            info = link_info_new[app_key]
                                            app_relink_counters[app_key] = info.get('remaining', random.randint(8, 25))
                                            app_total_songs_in_link[app_key] = info.get('total_songs', app_relink_counters[app_key])
                                            app_link_types[app_key] = info.get('type', 'Unknown')
                                        app_consecutive_bad[app_key] = 0
                                        app_last_good_time[app_key] = time.time()
                                        add_log("SUCC", udid, f"[MultiApp] [{dn}] Recovery complete, new link loaded")
                                    finally:
                                        ui_lock.release()
                                except Exception as e:
                                    add_log("ERR.", udid, f"[MultiApp] [{dn}] Recovery failed: {e}")
                        elif state == 'unknown' and app_consecutive_bad[app_key] >= 3:
                            fs_count = app_forcestop_count.get(app_key, 0)
                            fs_last = app_last_forcestop_time.get(app_key, 0)
                            if fs_count >= 3 and (now2 - fs_last) < 300:
                                add_log("WARN", udid, f"[MultiApp] [{dn}] unknown but force-stop cooldown active ({fs_count}x in 5min). Skipping recovery.")
                            else:
                                add_log("WARN", udid, f"[MultiApp] [{dn}] unknown for {int(seconds_since_good)}s. Trying force-stop + relaunch...")
                                app_forcestop_count[app_key] = fs_count + 1
                                app_last_forcestop_time[app_key] = now2
                                try:
                                    ui_lock = _get_device_ui_lock(udid)
                                    ui_lock.acquire()
                                    try:
                                        _ensure_volume_max(udid)
                                        _adb_shell(udid, f'am force-stop {pkg}')
                                        time.sleep(2)
                                        _enable_multi_audio_focus(udid)
                                        _multi_app_relaunch_after_link(udid, app_key, pkg, dn)
                                        link_info_new = getattr(_multi_app_relink_app, '_link_info', {})
                                        if app_key in link_info_new:
                                            info = link_info_new[app_key]
                                            app_relink_counters[app_key] = info.get('remaining', random.randint(8, 25))
                                            app_total_songs_in_link[app_key] = info.get('total_songs', app_relink_counters[app_key])
                                            app_link_types[app_key] = info.get('type', 'Unknown')
                                        app_consecutive_bad[app_key] = 0
                                        app_last_good_time[app_key] = time.time()
                                        add_log("SUCC", udid, f"[MultiApp] [{dn}] Recovery complete after unknown")
                                    finally:
                                        ui_lock.release()
                                except Exception as e:
                                    add_log("ERR.", udid, f"[MultiApp] [{dn}] Recovery failed: {e}")
            if status_parts:
                add_log("INFO", udid, f"[MultiApp] HEALTH: {' | '.join(status_parts)}")
            update_thread_status(udid, f'[MultiApp] Health OK', None, False, False, False, False, False, None)

    add_log("INFO", udid, "[MultiApp] Session time ended, stopping all apps...")
    for app_key in selected_apps_keys:
        app_info = SUPPORTED_APPS.get(app_key)
        if app_info:
            _stop_app_via_adb(udid, app_info['package'])


def single_clone_automation_flow(d, udid, spotify_pkgs, session_time_seconds, session_time_hours, binded_account, binded_proxy, connection_type, account_type):
    is_spotify = any('spotify' in p for p in spotify_pkgs)
    display_name = 'Spotify' if is_spotify else (spotify_pkgs[0].split('.')[-1] if spotify_pkgs else 'App')

    for pkg in spotify_pkgs:
        spotify_version = get_device_spotify_version(udid, pkg) if is_spotify else None
        add_log("INFO", udid, f"Starting session for package: {pkg} for {session_time_hours:.2f} hours.")
        if is_spotify:
            add_log("INFO", udid, f"Spotify version detected: {spotify_version or 'unknown'} (pkg: {pkg})")
        if str(config_streaming_mode_only).lower().__contains__('false'):
            if str(binded_account).lower().rstrip() == '/':
                input('No binded account provided; press Enter to continue.')
        ensure_screen_on(d)
        d.set_input_ime(True)
        freeze_rotation_port(d)
        if is_spotify:
            restart_spotify_if_crashed(d, False, pkg)
        else:
            _app_generic_restart_if_crashed(d, False, pkg)

        if str(config_streaming_mode_only).lower().__contains__('false'):
            if binded_proxy is not None:
                while True:
                    freeze_rotation_port(d)
                    if is_spotify:
                        restart_spotify_if_crashed(d, False, pkg)
                    else:
                        _app_generic_restart_if_crashed(d, False, pkg)
                    d.app_clear("io.oxylabs.proxymanager")
                    if connection_type == "TCP/IP":
                        reconnect_tcpip_device(udid)
                    freeze_rotation_port(d)
                    d.app_start("io.oxylabs.proxymanager", stop=True, use_monkey=True)
                    d.app_wait("io.oxylabs.proxymanager")
                    freeze_rotation_port(d)
                    proxy_set, msg = set_proxy_by_oxyproxymanager(d, udid, binded_proxy, connection_type)
                    if proxy_set is True:
                        add_log("INFO", udid, f"Set proxy to {binded_proxy}")
                        break
                    else:
                        add_log("ERR.", udid, msg)

        d.app_stop(pkg)
        d.app_start(pkg)
        freeze_rotation_port(d)
        d.app_wait(pkg)
        time.sleep(2)
        if is_spotify:
            disable_autoplay(d, udid, pkg)

        pkg_start_time = time.time()
        while (time.time() - pkg_start_time) < session_time_seconds and not stop_flags.get(udid):
            ppa = 9999999
            update_thread_status(udid, f'[{display_name}] Running', None, False, False, False, False, False, None)
            ensure_screen_on(d)
            d.set_input_ime(True)
            freeze_rotation_port(d)
            if is_spotify:
                restart_spotify_if_crashed(d, False, pkg)
            else:
                _app_generic_restart_if_crashed(d, False, pkg)

            if str(config_streaming_mode_only).lower().__contains__('false'):
                if binded_proxy is not None:
                    while True:
                        freeze_rotation_port(d)
                        if is_spotify:
                            restart_spotify_if_crashed(d, False, pkg)
                        else:
                            _app_generic_restart_if_crashed(d, False, pkg)
                        d.app_clear("io.oxylabs.proxymanager")
                        if connection_type == "TCP/IP":
                            reconnect_tcpip_device(udid)
                        freeze_rotation_port(d)
                        d.app_start("io.oxylabs.proxymanager", stop=True, use_monkey=True)
                        d.app_wait("io.oxylabs.proxymanager")
                        freeze_rotation_port(d)
                        proxy_set, msg = set_proxy_by_oxyproxymanager(d, udid, binded_proxy, connection_type)
                        if proxy_set is True:
                            add_log("INFO", udid, f"Set proxy to {binded_proxy}")
                            break
                        else:
                            add_log("ERR.", udid, msg)

            while not stop_flags.get(udid):
                freeze_rotation_port(d)
                if is_spotify:
                    if restart_spotify_if_crashed(d, True, pkg) is True:
                        add_log("EXC.", udid, f"{pkg} crashed, restarted it.")
                    link_loaded, songs_num, d = load_link(d, udid, account_type, pkg, spotify_version)
                    while songs_num != 0:
                        played_song, ppa, d = play_song(d, udid, account_type, ppa, songs_num, pkg, spotify_version)
                        if played_song is True:
                            songs_num -= 1
                        else:
                            if ppa == 0:
                                ppa = 9999999
                                songs_num = 0
                                break
                else:
                    if _app_generic_restart_if_crashed(d, True, pkg):
                        add_log("EXC.", udid, f"[{display_name}] {pkg} crashed, restarted it.")
                    link_loaded, songs_num, d = _app_generic_load_link(d, udid, pkg, display_name)
                    while songs_num != 0:
                        played_song, ppa, d = _app_generic_play_song(d, udid, pkg, display_name, ppa, songs_num)
                        if played_song is True:
                            songs_num -= 1
                        else:
                            if ppa == 0:
                                ppa = 9999999
                                songs_num = 0
                                break
                add_log("SUCC", udid, f"[{display_name}] Songs in link done")
                break
        add_log("INFO", udid, f"[{display_name}] Session for package {pkg} ended.")
        time.sleep(2)
    add_log("INFO", udid, f"[{display_name}] Cycle complete for device: {udid}.")
    d.app_stop(spotify_pkgs[0] if spotify_pkgs else pkg)


def thread_function(udid, binded_account, binded_proxy, connection_type, account_type, app_key='spotify'):
    thread_key = f"{udid}_{app_key}"
    app_info = SUPPORTED_APPS.get(app_key, SUPPORTED_APPS['spotify'])
    pkg = app_info['package']
    display_name = app_info['display_name']
    while True:
        if stop_flags.get(thread_key) or stop_flags.get(udid):
            break
        try:
            d = ua.connect(udid)
            if config_use_clonned_apks is True and app_key == 'spotify':
                spotify_pkgs = get_spotify_packages(d)
                if not spotify_pkgs:
                    add_log("ERR.", udid, "No Spotify packages found on device.")
                    time.sleep(60)
                    continue
                num_pkgs = len(spotify_pkgs)
            else:
                spotify_pkgs = [pkg]
                num_pkgs = 1
            session_time_hours = 24.0 / num_pkgs
            session_time_seconds = session_time_hours * 3600
            add_log("INFO", udid, f"[{display_name}] Found {num_pkgs} package(s). Session: {session_time_hours:.2f}h each.")

            single_clone_automation_flow(d, udid, spotify_pkgs, session_time_seconds, session_time_hours, binded_account, binded_proxy, connection_type, account_type)

        except Exception as e:
            update_thread_status(udid, f'Fail [{display_name}]', None, False, False, False, False, True, None)
            add_log("ERR.", udid, f"[{display_name}] Fail in thread: {str(e)}")

'''def thread_function(udid, binded_account, binded_proxy, connection_type, account_type):
    while True:
        session_time1, session_time2 = map(int, str(config_session_time).split('-'))
        thread_session_time = session_time1 if session_time1 == session_time2 else random.randrange(session_time1, session_time2)
        timeout_duration = thread_session_time * 3600
        update_thread_status(udid, 'Sleeping...', None, False, False, False, False, False, thread_session_time)
        try:
            start_time = time.time()  # Get the start time
            add_log("INFO", udid, f"Starting a new session for device: {udid}, will run for {thread_session_time} hours.")

            # Continue executing while the elapsed time is less than the session time
            while (time.time() - start_time) < timeout_duration:
                ppa = 9999999
                update_thread_status(udid, 'Starting', None, False, False, False, False, False, None)

                add_log("INFO", udid, f'Binded account: {binded_account}, Binded proxy: {binded_proxy}, PPA {ppa}')
                if str(config_streaming_mode_only).lower().__contains__('false'):
                    if str(binded_account).lower().rstrip() == '/':
                        input('no binded acc')
                d = ua.connect(udid)
                ensure_screen_on(d)
                d.set_input_ime(True)
                freeze_rotation_port(d)
                restart_spotify_if_crashed(d, False)
                if str(config_streaming_mode_only).lower().__contains__('false'):
                    if binded_proxy is not None:
                        while True:
                            freeze_rotation_port(d)
                            restart_spotify_if_crashed(d, False)
                            d.app_clear("io.oxylabs.proxymanager")
                            if connection_type == "TCP/IP":
                                reconnect_tcpip_device(udid)
                            freeze_rotation_port(d)
                            d.app_start("io.oxylabs.proxymanager", stop=True, use_monkey=True)
                            d.app_wait("io.oxylabs.proxymanager")
                            freeze_rotation_port(d)
                            proxy_set, msg = set_proxy_by_oxyproxymanager(d, udid, binded_proxy, connection_type)
                            if proxy_set is True:
                                add_log("INFO", udid, f'Set proxy to {binded_proxy}')
                                break
                            else:
                                add_log("ERR.", udid, msg)
                d.app_stop("com.spotify.music")
                d.app_start("com.spotify.music", ".MainActivity")
                freeze_rotation_port(d)
                while True:
                    freeze_rotation_port(d)
                    if restart_spotify_if_crashed(d, True) is True:
                        add_log("EXC.", udid, f'Spotify crashed, restarted it.')

                    link_loaded, songs_num = load_link(d, udid, account_type)
                    while songs_num != 0:
                        played_song, ppa = play_song(d, udid, account_type, ppa, songs_num)
                        if played_song is True:
                            songs_num -= 1
                        else:
                            if ppa == 0:
                                ppa = 9999999
                                songs_num = 0
                                break
                    add_log("SUCC", udid, "Songs in link done")

            random_sleep_minutes = random.randint(300, 480)
            random_sleep_seconds = random_sleep_minutes * 60
            add_log("INFO", udid, f"Session time for device: {udid} ended, restarting the loop in {random_sleep_minutes} minutes.")
            d.app_stop("com.spotify.music")
            update_thread_status(udid, 'Sleeping...', None, False, False, False, False, False, None)
            time.sleep(random_sleep_seconds)
            add_log("INFO", udid, f"Slept for {random_sleep_minutes} minutes, starting loop again.")
        except Exception as e:
            update_thread_status(udid, 'Fail in thread', None, False, False, False, False, True, None)
            add_log("ERR.", udid, f"Fail in thread: {str(e)}")
'''




def main_function(config_data):
    global config_selected_apps, worker_bot_running
    selected_apps = list(config_selected_apps)

    device_app_overrides = config_data.get('device_app_overrides', {})

    result = subprocess.run([adb_path, 'devices', '-l'], stdout=subprocess.PIPE, text=True, startupinfo=startupinfo)
    all_devices = []
    lines = result.stdout.strip().split('\n')[1:]

    for line in lines:
        if '\tdevice' not in line and '   device ' not in line:
            continue
        parts = line.split()
        udid = parts[0]
        model_match = next((p.split(':')[1] for p in parts if p.startswith('model:')), None)
        device_match = next((p.split(':')[1] for p in parts if p.startswith('device:')), None)
        is_tcp = udid.startswith('127.0.0.1:')
        all_devices.append((udid, model_match, device_match, is_tcp))

    model_best = {}
    for udid, model_match, device_match, is_tcp in all_devices:
        dedup_key = model_match or device_match
        if not dedup_key:
            continue
        if dedup_key not in model_best:
            model_best[dedup_key] = (udid, is_tcp)
        elif is_tcp and not model_best[dedup_key][1]:
            pass
        elif not is_tcp and model_best[dedup_key][1]:
            model_best[dedup_key] = (udid, is_tcp)

    devices = [udid for udid, _ in model_best.values()]

    if not devices:
        print("No devices connected.")
        return

    global worker_devices_connected
    worker_devices_connected = len(devices)

    for i, udid in enumerate(devices):
        connection_type = "TCP/IP" if is_tcpip_device(udid) else "USB"

        with app.app_context():
            device = Device.query.filter_by(udid=udid).first()
        if not device:
            print(f"No device found with udid: {udid}")
            continue

        binded_account = device.bindedAccount
        binded_proxy = device.bindedProxy
        accountType = device.accountType
        setProxy = True
        if str(binded_proxy).lower().rstrip() == '/':
            setProxy = False
        if str(binded_proxy).lower().rstrip() == '':
            setProxy = False
        if str(binded_proxy).lower().rstrip() == 'none':
            setProxy = False
        if setProxy is False:
            binded_proxy = None
        print(f'binded proxy before calling thread function: {binded_proxy}')

        d = ua.connect(udid)
        installed_pkgs = []
        try:
            installed_pkgs = d.app_list()
        except:
            pass

        device_apps = device_app_overrides.get(udid, selected_apps)
        add_log("INFO", udid, f"[MultiApp] App selection for {udid}: {device_apps}")

        installed_selected = []
        for app_key in device_apps:
            app_info = SUPPORTED_APPS[app_key]
            pkg = app_info['package']
            if pkg not in installed_pkgs:
                add_log("WARN", udid, f"{app_info['display_name']} ({pkg}) not installed on {udid}, skipping.")
                continue
            installed_selected.append(app_key)

        if len(installed_selected) > 1:
            add_log("INFO", udid, f"[MultiApp] {len(installed_selected)} apps installed: {installed_selected}. Using coordinated multi-app mode.")
            _st_raw = str(config_session_time).strip() or '8-8'
            _st_parts = _st_raw.split('-')
            session_time1 = int(_st_parts[0]) if _st_parts[0] else 8
            session_time2 = int(_st_parts[1]) if len(_st_parts) > 1 and _st_parts[1] else session_time1
            thread_session_time = session_time1 if session_time1 == session_time2 else random.randrange(session_time1, session_time2)
            session_time_seconds = thread_session_time * 3600

            def _multi_app_thread_wrapper(udid, apps, session_sec, binded_account, binded_proxy, conn_type, acc_type):
                while True:
                    if stop_flags.get(f"{udid}_multiapp") or stop_flags.get(udid):
                        break
                    try:
                        _multi_app_start_all(apps, udid, binded_account, binded_proxy, conn_type, acc_type)
                        _multi_app_monitor_all(apps, udid, session_sec)
                        for app_key in apps:
                            pkg = SUPPORTED_APPS[app_key]['package']
                            _stop_app_via_adb(udid, pkg)
                        add_log("INFO", udid, "[MultiApp] Session ended, restarting cycle...")
                    except Exception as e:
                        add_log("ERR.", udid, f"[MultiApp] Thread error: {e}")
                    time.sleep(5)

            thread_key = f"{udid}_multiapp"
            worker_thread = threading.Thread(
                target=_multi_app_thread_wrapper,
                args=(udid, installed_selected, session_time_seconds, binded_account, binded_proxy, connection_type, accountType),
            )
            worker_threads[thread_key] = {
                "UDID": udid,
                "app": "+".join([SUPPORTED_APPS[k]['display_name'] for k in installed_selected]),
                "app_key": "multiapp",
                "status": "Connected",
                "proxy": binded_proxy,
                "account": binded_account,
                "connection_type": connection_type,
                "streams": 0,
                "likes": 0,
                "follows": 0,
                "errors": 0,
                "session_time": thread_session_time,
                "thread": worker_thread,
            }
            stop_flags[thread_key] = False
            worker_thread.start()
        else:
            for app_key in installed_selected:
                app_info = SUPPORTED_APPS[app_key]
                pkg = app_info['package']
                if pkg not in installed_pkgs:
                    add_log("WARN", udid, f"{app_info['display_name']} ({pkg}) not installed on {udid}, skipping.")
                    continue

                thread_key = f"{udid}_{app_key}"
                worker_thread = threading.Thread(
                    target=thread_function,
                    args=(udid, binded_account, binded_proxy, connection_type, accountType, app_key),
                )
                worker_threads[thread_key] = {
                    "UDID": udid,
                    "app": app_info['display_name'],
                    "app_key": app_key,
                    "status": "Connected",
                    "proxy": binded_proxy,
                    "account": binded_account,
                    "connection_type": connection_type,
                    "streams": 0,
                    "likes": 0,
                    "follows": 0,
                    "errors": 0,
                    "session_time": 0,
                    "thread": worker_thread,
                }
                stop_flags[thread_key] = False
                worker_thread.start()
                time.sleep(1)

    while worker_bot_running:
        time.sleep(2)



@app.route('/supported_apps', methods=['GET'])
@require_token
def get_supported_apps():
    result = {}
    for key, info in SUPPORTED_APPS.items():
        result[key] = {
            'display_name': info['display_name'],
            'package': info['package'],
        }
    return jsonify(result)


@app.route('/installed_apps', methods=['GET'])
@require_token
def get_installed_apps_endpoint():
    udid = request.args.get('udid')
    if not udid:
        return jsonify({"error": "udid is required"}), 400
    try:
        d = ua.connect(udid)
        installed = d.app_list()
        result = {}
        for key, info in SUPPORTED_APPS.items():
            pkg = info['package']
            result[key] = {
                'package': pkg,
                'display_name': info['display_name'],
                'installed': pkg in installed,
            }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


INSTALL_APKS = {
    'spotify': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apk', 'Spotify_9.1.22.apk'),
    'tidal': {
        'base': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apk', 'Tidal_base.apk'),
        'splits': [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apk', 'Tidal_arm64.apk'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apk', 'Tidal_xxhdpi.apk'),
        ]
    },
    'apple_music': {
        'base': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apk', 'AppleMusic_base.apk'),
        'splits': [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apk', 'AppleMusic_split_config.arm64_v8a.apk'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apk', 'AppleMusic_split_config.xxhdpi.apk'),
        ]
    }
}

@app.route('/install_apps', methods=['POST'])
@require_token
def install_apps_endpoint():
    """Install APKs on selected devices.
    Body: { phones: [1,2,3...], apps: ['spotify','tidal','apple_music'] }
    Resolves Panda numbers to ADB serials, installs each APK."""
    data = request.json or {}
    phone_nums = data.get('phones', [])
    apps = data.get('apps', [])

    if not phone_nums or not apps:
        return jsonify({"success": False, "error": "phones and apps are required"}), 400

    import sqlite3 as sqlite3_mod
    db_path = os.path.join(os.path.expandvars('%APPDATA%'), '6WPTMA9HZO', 'device.db')
    num_to_serial = {}
    if os.path.exists(db_path):
        try:
            conn = sqlite3_mod.connect(db_path)
            rows = conn.execute(
                "SELECT onlySerial, sort, name FROM device WHERE userDelete=0"
            ).fetchall()
            conn.close()
            for serial, num, name in rows:
                try:
                    num_to_serial[int(num)] = str(serial)
                except (ValueError, TypeError):
                    continue
        except Exception as e:
            add_log("WARN", "install_apps", f"Could not read Panda db: {e}")

    result_devices = subprocess.run(
        [adb_path, 'devices'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        startupinfo=startupinfo, timeout=30
    )
    connected = set()
    for line in result_devices.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith('List of devices') or '\t' not in line:
            continue
        serial, state = line.split('\t', 1)
        if state.strip() == 'device':
            connected.add(serial.strip())

    results = []
    for phone_num in phone_nums:
        try:
            pn = int(phone_num)
        except (ValueError, TypeError):
            continue
        serial = num_to_serial.get(pn)
        if not serial:
            results.append({"device": f"Panda#{pn}", "success": False, "message": "Serial not found in Panda DB"})
            continue
        if serial not in connected:
            results.append({"device": f"Panda#{pn} ({serial})", "success": False, "message": "Device not connected"})
            continue

        for app_key in apps:
            apk_info = INSTALL_APKS.get(app_key)
            app_display = SUPPORTED_APPS.get(app_key, {}).get('display_name', app_key)
            pkg = SUPPORTED_APPS.get(app_key, {}).get('package', '')

            is_split = isinstance(apk_info, dict)
            if is_split:
                apk_path = apk_info.get('base', '')
                all_parts = [apk_path] + apk_info.get('splits', [])
                if not all(os.path.exists(p) for p in all_parts):
                    missing = [p for p in all_parts if not os.path.exists(p)]
                    results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": False, "message": f"APKs not found: {', '.join(missing)}"})
                    continue
            else:
                apk_path = apk_info
                if not apk_path or not os.path.exists(apk_path):
                    results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": False, "message": f"APK not found: {apk_path}"})
                    continue

            try:
                add_log("INFO", serial, f"Uninstalling {app_display} (if exists)...")
                subprocess.run(
                    [adb_path, '-s', serial, 'uninstall', pkg],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    startupinfo=startupinfo, timeout=60
                )

                sdk_result = subprocess.run(
                    [adb_path, '-s', serial, 'shell', 'getprop', 'ro.build.version.sdk'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    startupinfo=startupinfo, timeout=10
                )
                device_sdk = int(sdk_result.stdout.strip() or '99')
                add_log("INFO", serial, f"Device SDK: {device_sdk}")

                universal_apk = None
                min_sdk = None
                if isinstance(apk_info, dict):
                    universal_apk = apk_info.get('universal')
                    min_sdk = apk_info.get('min_sdk')

                if min_sdk is not None and device_sdk < min_sdk:
                    if universal_apk and os.path.exists(universal_apk):
                        add_log("WARN", serial, f"Device SDK {device_sdk} < min_sdk {min_sdk}. Using universal APK: {os.path.basename(universal_apk)}")
                        install_cmd = [adb_path, '-s', serial, 'install', universal_apk]
                        install_result = subprocess.run(
                            install_cmd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            startupinfo=startupinfo, timeout=300
                        )
                        output = install_result.stdout + install_result.stderr
                        if 'Success' in output:
                            add_log("SUCC", serial, f"{app_display} installed successfully via universal APK")
                            results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": True, "message": "Installed (universal)"})
                            continue
                        else:
                            msg = output.strip()[:200]
                            add_log("ERR.", serial, f"{app_display} universal install failed: {msg}")
                            results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": False, "message": msg})
                            continue
                    else:
                        msg = f"Device SDK {device_sdk} too low for {app_display} (needs {min_sdk}+). Place universal APK in apk/ folder."
                        add_log("ERR.", serial, msg)
                        results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": False, "message": msg})
                        continue

                add_log("INFO", serial, f"Installing {app_display}...")
                installed = False
                output = ""

                if is_split:
                    install_cmd = [adb_path, '-s', serial, 'install-multiple'] + all_parts
                    install_result = subprocess.run(
                        install_cmd,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        startupinfo=startupinfo, timeout=300
                    )
                    output = install_result.stdout + install_result.stderr
                    if 'Success' in output:
                        installed = True
                    elif universal_apk and os.path.exists(universal_apk):
                        add_log("WARN", serial, f"{app_display} split install failed. Falling back to universal APK...")
                        fallback_cmd = [adb_path, '-s', serial, 'install', universal_apk]
                        fallback_result = subprocess.run(
                            fallback_cmd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            startupinfo=startupinfo, timeout=300
                        )
                        output = fallback_result.stdout + fallback_result.stderr
                        if 'Success' in output:
                            installed = True
                else:
                    install_cmd = [adb_path, '-s', serial, 'install', apk_path]
                    install_result = subprocess.run(
                        install_cmd,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        startupinfo=startupinfo, timeout=300
                    )
                    output = install_result.stdout + install_result.stderr
                    if 'Success' in output:
                        installed = True
                    elif universal_apk and os.path.exists(universal_apk):
                        add_log("WARN", serial, f"{app_display} install failed. Falling back to universal APK...")
                        fallback_cmd = [adb_path, '-s', serial, 'install', universal_apk]
                        fallback_result = subprocess.run(
                            fallback_cmd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            startupinfo=startupinfo, timeout=300
                        )
                        output = fallback_result.stdout + fallback_result.stderr
                        if 'Success' in output:
                            installed = True

                if installed:
                    add_log("SUCC", serial, f"{app_display} installed successfully")
                    results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": True, "message": "Installed"})
                else:
                    msg = output.strip()[:200]
                    add_log("ERR.", serial, f"{app_display} install failed: {msg}")
                    results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": False, "message": msg})
            except subprocess.TimeoutExpired:
                results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": False, "message": "Install timed out (5min)"})
            except Exception as e:
                results.append({"device": f"Panda#{pn} ({serial})", "app": app_display, "success": False, "message": str(e)})

    return jsonify({"success": True, "results": results})


@app.route('/backend', methods=['POST'])
def backend_ready():
    if backend_state != 'Ready!':
        return jsonify({"ready": False, "message": backend_state})
    else:
        return jsonify({"ready": True, "message": "Ready to launch!"})


@app.route('/get_version', methods=['GET'])
@require_token
def get_version():
    return jsonify({"version": Bot_version, "repo": GITHUB_REPO})


@app.route('/check_update', methods=['GET'])
@require_token
def check_update():
    try:
        import urllib.request
        import urllib.error
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "Spotifix-Updater"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        remote_tag = data.get("tag_name", "").lstrip("v")
        remote_notes = data.get("body", "")
        current = tuple(int(x) for x in Bot_version.split("."))
        remote = tuple(int(x) for x in remote_tag.split(".")) if remote_tag else (0, 0, 0)
        has_update = remote > current
        return jsonify({
            "has_update": has_update,
            "current_version": Bot_version,
            "remote_version": remote_tag,
            "release_notes": remote_notes
        })
    except Exception as e:
        return jsonify({"has_update": False, "error": str(e)})


SOURCE_FILES_TO_UPDATE = [
    'api.py', 'renderer.js', 'index.html', 'login.html',
    'splash.html', 'console.html', 'vide.html',
    'main.js', 'preload.js', 'package.json',
    'SpotifyPatcher.py', 'ConsoleLogger.py', 'UtilsService.py', 'keyauth.py'
]


@app.route('/install_update', methods=['POST'])
@require_token
def install_update():
    data = request.json or {}
    remote_version = data.get("remote_version", "")
    if not remote_version:
        return jsonify({"success": False, "error": "No remote version provided"}), 400
    try:
        import urllib.request
        import urllib.error
        app_dir = os.path.dirname(os.path.abspath(__file__))
        branch = "main"
        downloaded = []
        failed = []
        for fname in SOURCE_FILES_TO_UPDATE:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{branch}/{fname}"
            dest = os.path.join(app_dir, fname)
            try:
                urllib.request.urlretrieve(raw_url, dest)
                downloaded.append(fname)
            except Exception as e:
                failed.append(f"{fname}: {e}")
        if not failed:
            add_log("SUCC", "updater", f"Updated {len(downloaded)} files to v{remote_version}. Restarting...")
            def _restart_app():
                time.sleep(2)
                try:
                    exe = sys.executable if hasattr(sys, 'executable') else None
                    if exe and os.path.exists(exe):
                        subprocess.Popen([exe] + sys.argv, shell=True)
                except Exception:
                    pass
                os._exit(0)
            threading.Thread(target=_restart_app, daemon=True).start()
            return jsonify({"success": True, "message": f"Updated to v{remote_version}. Restarting...", "downloaded": downloaded})
        else:
            return jsonify({"success": False, "error": f"Some files failed: {'; '.join(failed)}", "downloaded": downloaded, "failed": failed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    app.run(port=8999, debug=False)
