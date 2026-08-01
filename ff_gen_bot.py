import os
import sys
import json
import time
import random
import string
import hashlib
import threading
import subprocess
import base64
import codecs
import re
import logging
import asyncio
from datetime import datetime
from collections import deque
from flask import Flask, render_template_string, jsonify, request

# ---------- Telegram imports ----------
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import Conflict

# ---------- Install cfonts if missing ----------
try:
    from cfonts import render
    CFONTS = True
except:
    CFONTS = False
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'python-cfonts'])
    from cfonts import render

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =======================================================
#  LOGGING SETUP – capture all logs to a buffer
# =======================================================
LOG_BUFFER = deque(maxlen=1000)  # keep last 1000 lines

class ListHandler(logging.Handler):
    def emit(self, record):
        LOG_BUFFER.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {self.format(record)}")

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Console handler (Render logs)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
logger.addHandler(console)
# Buffer handler
list_handler = ListHandler()
list_handler.setFormatter(logging.Formatter('%(levelname)s | %(message)s'))
logger.addHandler(list_handler)

# =======================================================
#  GENERATOR CONFIG – REBRANDED TO POPPY
# =======================================================

ReGiOn = "IND"
NiCkNaMe = "POPPY"
PaSsWoRd = "POPPY"
ToTaL = 100
ThReAdS = 50
GhOsT = False
AuToAcT = True

aEsKeY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
aEsIv = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
cLiEnTsEcReT = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"

rEgIoNlAnG = {
    "ME": "ar", "IND": "hi", "ID": "id", "VN": "vi", "TH": "th",
    "BD": "bn", "PK": "ur", "TW": "zh", "EUROPE": "fr", "RU": "ru",
    "NA": "na", "SAC": "es", "BR": "pt", "SG": "ms", "US": "us"
}
rEgIoNlIsT = ["IND", "ID", "TH", "ME", "EUROPE", "VN", "BD", "PK", "TW", "RU", "NA", "SAC", "BR", "SG", "US"]

nIcKXoR = b'1e5898ccb8dfdd921f9bdea848768b64a201'

cOnSeCuTiVe = 0
pRiNtLoCk = threading.Lock()
iPlOcK = threading.Lock()

INDIAN_CARRIERS = [
    "Jio", "Airtel", "Vodafone Idea", "BSNL", "MTNL",
    "Reliance Jio", "Bharti Airtel", "Vi", "Idea Cellular"
]
INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Kanpur", "Nagpur", "Indore", "Bhopal", "Visakhapatnam",
    "Patna", "Vadodara", "Surat", "Rajkot", "Chandigarh"
]
INDIAN_DEVICES = [
    "Asus ASUS_AI2401_A", "Samsung SM-G998B", "OnePlus 9 Pro",
    "Xiaomi Mi 11", "Google Pixel 6", "Realme GT", "Vivo X70 Pro",
    "Oppo Find X3", "Motorola Edge 20", "Samsung SM-M515F",
    "Samsung SM-A525F", "Redmi Note 10", "OnePlus Nord 2"
]

# ---------- Tor integration with robust startup ----------
tor_process = None
IP_ROTATION_INTERVAL = 15
ACCOUNT_COUNTER_FOR_IP_ROTATION = 0
TOR_AVAILABLE = False

def start_tor():
    global tor_process, TOR_AVAILABLE
    try:
        # Kill any existing tor
        subprocess.run(['pkill', '-9', 'tor'], capture_output=True, check=False)
        time.sleep(1)
        # Start tor
        tor_process = subprocess.Popen(
            ['tor'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # Wait up to 30 seconds for tor to be ready
        for i in range(30):
            time.sleep(1)
            # Check if process is still running
            if tor_process.poll() is not None:
                logger.warning(f"Tor process died early. Attempt {i+1}/30")
                # Try restarting
                tor_process = subprocess.Popen(
                    ['tor'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                continue
            # Test if SOCKS proxy is responsive
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect(('127.0.0.1', 9050))
                s.close()
                TOR_AVAILABLE = True
                logger.info("✅ Tor started successfully and SOCKS proxy is reachable.")
                return True
            except:
                # Still starting
                continue
        logger.warning("⚠️ Tor did not become ready within 30 seconds. Check installation.")
        TOR_AVAILABLE = False
        return False
    except Exception as e:
        logger.error(f"❌ Tor startup exception: {e}")
        TOR_AVAILABLE = False
        return False

def renew_tor_ip():
    if not TOR_AVAILABLE:
        return False
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(('127.0.0.1', 9051))
        s.send(b'AUTHENTICATE ""\r\n')
        s.send(b'SIGNAL NEWNYM\r\n')
        s.send(b'QUIT\r\n')
        s.close()
        time.sleep(1)
        logger.info("🔄 Tor IP renewed.")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Tor IP renewal failed: {e}")
        return False

def get_proxies():
    if TOR_AVAILABLE:
        return {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
    # If Tor is not available, we raise an exception to avoid using broken proxies
    raise RuntimeError("Tor is not available. Cannot create accounts without IP rotation.")

# ---------- Session pool ----------
session_pool = []
SESSION_POOL_SIZE = ThReAdS

def init_session_pool():
    global session_pool
    for _ in range(SESSION_POOL_SIZE):
        session = requests.Session()
        session.proxies.update(get_proxies())
        session.verify = False
        session.timeout = 10
        session_pool.append(session)

def get_pool_session():
    return random.choice(session_pool)

# ---------- Protobuf-like packing and encryption ----------
def FF(value):
    out = []
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)

def GayRena(field_num, value):
    if isinstance(value, int):
        tag = (field_num << 3) | 0
        return FF(tag) + FF(value)
    elif isinstance(value, str):
        data = value.encode('utf-8')
        tag = (field_num << 3) | 2
        return FF(tag) + FF(len(data)) + data
    elif isinstance(value, bytes):
        tag = (field_num << 3) | 2
        return FF(tag) + FF(len(value)) + value
    elif isinstance(value, dict):
        sub_payload = xPro(value)
        tag = (field_num << 3) | 2
        return FF(tag) + FF(len(sub_payload)) + sub_payload
    else:
        raise TypeError(f"Unsupported type for field {field_num}: {type(value)}")

def xPro(fields_dict):
    payload = b''
    for key, value in fields_dict.items():
        field_num = int(key)
        if isinstance(value, list):
            if value and all(isinstance(v, int) for v in value):
                packed = b''.join(FF(v) for v in value)
                tag = (field_num << 3) | 2
                payload += FF(tag) + FF(len(packed)) + packed
            else:
                for elem in value:
                    payload += GayRena(field_num, elem)
        else:
            payload += GayRena(field_num, value)
    return payload

def Noob(packet):
    cipher = AES.new(aEsKeY, AES.MODE_CBC, aEsIv)
    pad_len = 16 - (len(packet) % 16)
    if pad_len == 0:
        pad_len = 16
    plaintext_padded = packet + bytes([pad_len]) * pad_len
    return cipher.encrypt(plaintext_padded)

def Pro(data):
    from google.protobuf.internal.decoder import _DecodeVarint, _DecodeVarint32
    pos = 0
    length = len(data)
    fields = {}
    while pos < length:
        key, pos = _DecodeVarint(data, pos)
        field_num = key >> 3
        wire_type = key & 7
        if wire_type == 0:
            value, pos = _DecodeVarint(data, pos)
        elif wire_type == 2:
            size, pos = _DecodeVarint32(data, pos)
            raw = data[pos:pos+size]
            pos += size
            try:
                value = Pro(raw)
            except:
                try:
                    value = raw.decode('utf-8')
                except:
                    value = raw.hex()
        elif wire_type == 5:
            value = int.from_bytes(data[pos:pos+4], "little")
            pos += 4
        elif wire_type == 1:
            value = int.from_bytes(data[pos:pos+8], "little")
            pos += 8
        else:
            raise Exception(f"Unsupported wire type: {wire_type}")
        if field_num in fields:
            if not isinstance(fields[field_num], list):
                fields[field_num] = [fields[field_num]]
            fields[field_num].append(value)
        else:
            fields[field_num] = value
    return fields

# ---------- Garena API calls ----------
def RoFl(session, password):
    url = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
    payload = {"app_id": 100067, "client_type": 2, "password": password, "source": 2}
    json_body = json.dumps(payload, separators=(',', ':'))
    data_to_sign = cLiEnTsEcReT + json_body
    signature = hashlib.sha256(data_to_sign.encode()).hexdigest()
    headers = {
        "User-Agent": "GarenaMSDK/4.0.39(FRL-AN00a ;Android 10;nu;HK;)",
        "Authorization": f"Signature {signature}",
        "Content-Type": "application/json; charset=utf-8"
    }
    resp = session.post(url, data=json_body, headers=headers, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("code") == 0:
            return str(data["data"]["uid"])
        else:
            raise Exception(f"Register failed: {data}")
    else:
        resp.raise_for_status()
        raise Exception(f"Unexpected response: {resp.text}")

def yEet(length=6, chars=string.ascii_uppercase + string.digits + "-_."):
    return ''.join(random.choice(chars) for _ in range(length))

def pWe():
    try:
        return requests.get('https://api.ipify.org', timeout=3).text
    except:
        return "0.0.0.0"

def sUs():
    return "GarenaMSDK/4.0.39(FRL-AN00a ;Android 10;nu;HK;)"

def bRuH():
    return "okhttp/3.12.1"

def fInE(original):
    keystream = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
                 0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    encoded = ""
    for i in range(len(original)):
        orig_byte = ord(original[i])
        key_byte = keystream[i % len(keystream)]
        result_byte = orig_byte ^ key_byte
        encoded += chr(result_byte)
    return encoded

def yAy(s):
    return ''.join(c if 32 <= ord(c) <= 126 else f'\\u{ord(c):04x}' for c in s)

def nOp(nick_b64):
    if not nick_b64:
        return ""
    try:
        decoded_bytes = base64.b64decode(nick_b64)
        key_len = len(nIcKXoR)
        xored = bytes([decoded_bytes[i] ^ nIcKXoR[i % key_len] for i in range(len(decoded_bytes))])
        return xored.decode('utf-8', errors='ignore')
    except:
        return nick_b64

def wOw(func, session, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(session, *args, **kwargs)
        except:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.5)
    return None

def hAhA(session, password):
    return RoFl(session, password)

def lMaO(session, uid, password):
    url = "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant"
    payload = {
        "client_id":100067, "client_secret":cLiEnTsEcReT, "client_type":2,
        "password":password, "response_type":"token", "uid":uid
    }
    headers = {"User-Agent": sUs(), "Content-Type": "application/json"}
    resp = session.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"Token grant failed: {data}")
    return data["data"]["access_token"], data["data"]["open_id"]

def gG(session, name, access_token, open_id, region, is_ghost=False):
    global cOnSeCuTiVe
    url = "https://loginbp.ggpolarbear.com/MajorRegister"
    host = "loginbp.ggpolarbear.com"
    exp_digits = {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹'}
    num = random.randint(1,99999)
    exp = ''.join(exp_digits[d] for d in f"{num:05d}")
    name = name[:7] + exp
    lang_code = "pt" if is_ghost else rEgIoNlAnG.get(region.upper(), "en")
    encoded_result = fInE(open_id)
    field_unicode = yAy(encoded_result)
    field_bytes = codecs.decode(field_unicode, 'unicode_escape').encode('latin1')
    fields_dict = {
        "1": name, "2": access_token, "3": open_id,
        "5": 102000007, "6": 4, "7": 1, "13": 1,
        "14": field_bytes, "15": lang_code, "16": 2
    }
    plaintext = xPro(fields_dict)
    encrypted_payload = Noob(plaintext)
    headers = {
        "Accept-Encoding": "gzip", "Authorization": "Bearer", "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded", "Expect": "100-continue",
        "Host": host, "ReleaseVersion": "OB54",
        "User-Agent": bRuH(), "X-GA": "v1 1", "X-Unity-Version": "2018.4."
    }
    try:
        resp = session.post(url, headers=headers, data=encrypted_payload, timeout=15)
        resp.raise_for_status()
        with iPlOcK:
            cOnSeCuTiVe = 0
        return Pro(resp.content)
    except Exception as e:
        with iPlOcK:
            cOnSeCuTiVe += 1
            if cOnSeCuTiVe >= 10:
                renew_tor_ip()
                time.sleep(1)
                cOnSeCuTiVe = 0
        raise

def nIcE(session, access_token, open_id, region, lang_code):
    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = pWe()
    if region.upper() == "IND":
        device_model = random.choice(INDIAN_DEVICES)
        carrier = random.choice(INDIAN_CARRIERS)
        city = random.choice(INDIAN_CITIES)
    else:
        device_model = "Asus ASUS_AI2401_A"
        carrier = "GrameenPhone"
        city = "Dhaka"
    gpu = "Adreno (TM) 640"
    
    def qT(n):
        out = []
        while True:
            b = n & 0x7F
            n >>= 7
            if n: b |= 0x80
            out.append(b)
            if not n: break
        return bytes(out)
    
    def zZ(f, v):
        return qT((f << 3) | 0) + qT(v)
    
    def xX(f, v):
        data = v.encode() if isinstance(v, str) else v
        return qT((f << 3) | 2) + qT(len(data)) + data
    
    fields = {
        3: now_str,
        4: "free fire",
        5: 1,
        7: "1.126.5",
        8: "Android OS 5.1.1 / API-22 (LMY48Z/rel.se.infra.20220128.171448)",
        9: "Handheld",
        10: carrier,
        11: "WIFI",
        17: gpu,
        18: "OpenGL ES 3.0",
        19: "Google|4645e530-e790-4be2-ae7c-6f64d1259603",
        20: ip,
        21: lang_code,
        22: open_id,
        23: 4,
        24: "Handheld",
        25: device_model,
        26: region.upper(),
        29: access_token,
        33: carrier,
        34: "WIFI",
        37: "7428b253defc164018c604a1ebbfebdf",
        73: "/data/app/com.dts.freefireth-1/lib/arm",
        75: "H4c322aeb56444feaa151d1ea91a8f7f2|/data/app/com.dts.freefireth-1/base.apk",
        76: 2,
        78: 2,
        79: 2,
        83: "OpenGLES2",
        85: city,
        87: "android",
        88: "KqsHTywQqGHMgPbDY9P2mhkxXj/beObk/TFNpmgaucQwxyLu9hA478WEQCV0Mgaz9UivYUPpKNwPzgZhvDhSsUDMAFY=",
        90: '{"cur_rate":null,"support_etc2":false}',
        97: 1,
        98: 1,
        99: "4",
        100: "4"
    }
    
    packet = b''
    for f, v in fields.items():
        if isinstance(v, int): 
            packet += zZ(f, v)
        elif isinstance(v, str): 
            packet += xX(f, v)
        elif isinstance(v, bytes): 
            packet += xX(f, v)
    
    encrypted = Noob(packet)
    headers = {
        "Accept-Encoding": "gzip", 
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded", 
        "Expect": "100-continue",
        "ReleaseVersion": "OB54", 
        "User-Agent": bRuH(),
        "X-GA": "v1 1", 
        "X-Unity-Version": "2018.4."
    }
    resp = session.post(url, headers=headers, data=encrypted, timeout=15)
    resp.raise_for_status()
    decoded = Pro(resp.content)
    jwt_token = decoded.get(8)
    if isinstance(jwt_token, list):
        jwt_token = jwt_token[0] if jwt_token else None
    return decoded, jwt_token

def dUdE(session, region_code, jwt_token):
    url = "https://loginbp.ggpolarbear.com/ChooseRegion"
    if region_code.upper() == "CIS":
        region_code = "ru"
    else:
        region_code = region_code.upper()
    fields_dict = {"1": region_code}
    plaintext = xPro(fields_dict)
    encrypted_payload = Noob(plaintext)
    headers = {
        "Accept-Encoding": "gzip", "Authorization": f"Bearer {jwt_token}",
        "Connection": "Keep-Alive", "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue", "ReleaseVersion": "OB54",
        "User-Agent": bRuH(), "X-GA": "v1 1", "X-Unity-Version": "2018.4."
    }
    resp = session.post(url, headers=headers, data=encrypted_payload, timeout=10)
    return resp.status_code == 200

def bYe(session, jwt_token, client_url):
    url = f"https://{client_url}/GetLoginData"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = pWe()
    device_model = random.choice(INDIAN_DEVICES)
    carrier = random.choice(INDIAN_CARRIERS)
    city = random.choice(INDIAN_CITIES)
    gpu = "Adreno (TM) 640"
    open_id = "24adf2d6806cf61bd95d4cd3b57a0bd9"
    
    def qT(n):
        out = []
        while True:
            b = n & 0x7F
            n >>= 7
            if n: b |= 0x80
            out.append(b)
            if not n: break
        return bytes(out)
    
    def zZ(f, v):
        return qT((f << 3) | 0) + qT(v)
    
    def xX(f, v):
        data = v.encode() if isinstance(v, str) else v
        return qT((f << 3) | 2) + qT(len(data)) + data
    
    fields = {
        3: now_str,
        4: "free fire",
        5: 1,
        7: "1.126.5",
        8: "Android OS 5.1.1 / API-22 (LMY48Z/rel.se.infra.20220128.171448)",
        9: "Handheld",
        10: carrier,
        11: "WIFI",
        17: gpu,
        18: "OpenGL ES 3.0",
        19: "Google|4645e530-e790-4be2-ae7c-6f64d1259603",
        20: ip,
        21: "en",
        22: open_id,
        23: 4,
        24: "Handheld",
        25: device_model,
        26: "IND",
        29: jwt_token,
        33: carrier,
        34: "WIFI",
        37: "7428b253defc164018c604a1ebbfebdf",
        73: "/data/app/com.dts.freefireth-1/lib/arm",
        75: "H4c322aeb56444feaa151d1ea91a8f7f2|/data/app/com.dts.freefireth-1/base.apk",
        83: "OpenGLES2",
        85: city,
        87: "android",
        88: "KqsHT8nWdkA7u/m7k8vg2H5FgrCGa4lfww3nHBGRHRPwDFV4LyCj8sT23O/P6K06qC3MOLZRThwWwul+g2goHwtQJy8=",
        90: '{"cur_rate":null,"support_etc2":false}'
    }
    
    packet = b''
    for f, v in fields.items():
        if isinstance(v, int): 
            packet += zZ(f, v)
        elif isinstance(v, str): 
            packet += xX(f, v)
        elif isinstance(v, bytes): 
            packet += xX(f, v)
    
    encrypted_payload = Noob(packet)
    
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 12)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded",
        'Authorization': f"Bearer {jwt_token}",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB54"
    }
    
    try:
        resp = session.post(url, headers=headers, data=encrypted_payload, timeout=10)
        return resp.status_code == 200
    except:
        return False

def hElLo(jwt_token):
    try:
        parts = jwt_token.split('.')
        if len(parts) != 3:
            return None, None
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        data = json.loads(base64.b64decode(payload))
        lock_region = data.get("lock_region") or data.get("noti_region")
        raw_nick = data.get("nickname")
        if raw_nick:
            nickname = nOp(raw_nick)
        else:
            nickname = ""
        return lock_region, nickname
    except:
        return None, None

# ---------- Account generator class ----------
class AcCoUnTcReAtOr:
    def __init__(self, region, nickname_prefix, password_prefix, password_mode, auto_activate, total_target, ghost=False):
        self.region = region
        self.nickname_prefix = nickname_prefix[:7]
        self.password_prefix = password_prefix.upper()
        self.password_mode = password_mode
        self.auto_activate = auto_activate
        self.total_target = total_target
        self.ghost = ghost
        self.results = []
        self.lock = threading.Lock()
        self.created_count = 0
        self.fail_counter = 0
        self.ip_blocked = False
        self.stop = False
        self.results_lock = threading.Lock()
        self.saved_uids = set()
        self.file_lock = threading.Lock()
        self.output_lines = []

    def load_existing_uids(self):
        if self.ghost:
            folder = "GEN/GHOST"
        else:
            folder = f"GEN/{self.region}"
        txt_path = os.path.join(folder, f"Accounts-{self.region}.txt")
        try:
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        match = re.search(r'UiD = (\d+)', line)
                        if match:
                            self.saved_uids.add(match.group(1))
        except:
            pass

    def gEnPaSs(self):
        r1 = yEet(6)
        r2 = yEet(6)
        plain = f"{self.password_prefix}_{r1}-POPPY{r2}"
        return plain, plain

    def save_single_account(self, acc):
        if self.ghost:
            folder = "GEN/GHOST"
        else:
            folder = f"GEN/{self.region}"
        try:
            os.makedirs(folder, exist_ok=True)
        except:
            folder = "."
        txt_path = os.path.join(folder, f"Accounts-{self.region}.txt")
        
        with self.file_lock:
            try:
                uid = acc.get('uid', '')
                existing_uids = set()
                if os.path.exists(txt_path):
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            match = re.search(r'UiD = (\d+)', line)
                            if match:
                                existing_uids.add(match.group(1))
                
                if uid not in existing_uids:
                    line = f"BOT = {acc.get('game_uid', '')} | UiD = {uid} | PassWord = {acc.get('password', '')} | NamE = {acc.get('nickname', '')} | ReGioN = {acc.get('region', '')}\n"
                    with open(txt_path, 'a', encoding='utf-8') as f:
                        f.write(line)
                    with self.results_lock:
                        self.saved_uids.add(uid)
                        self.output_lines.append(line.strip())
                    return True
            except:
                pass
        return False

    def cReAtE(self, thread_id):
        if self.stop or self.ip_blocked:
            return None
        session = get_pool_session()
        try:
            store_pass, api_pass = self.gEnPaSs()
            uid = wOw(hAhA, session, api_pass)
            
            with self.results_lock:
                if uid in self.saved_uids:
                    return None
            
            access_token, open_id = wOw(lMaO, session, uid, api_pass)
            reg_resp = wOw(gG, session, self.nickname_prefix, access_token, open_id, self.region, self.ghost)
            account_id = reg_resp.get(3)
            if not account_id:
                raise Exception("No account_id")
            account_id = str(account_id)
            lang_code = rEgIoNlAnG.get(self.region, "en") if not self.ghost else "pt"
            login_resp, jwt_token = wOw(nIcE, session, access_token, open_id, self.region, lang_code)
            if not jwt_token:
                raise Exception("No JWT")
            lock_region, nickname = hElLo(jwt_token)
            if not nickname:
                nickname = self.nickname_prefix
            need_lock = False
            final_jwt = jwt_token
            client_url = None
            if not self.ghost:
                if lock_region and lock_region not in (None, 'None', '..', ''):
                    if lock_region != self.region.upper():
                        need_lock = True
                else:
                    need_lock = True
                if need_lock:
                    dUdE(session, self.region, jwt_token)
                    login_resp2, jwt_token2 = wOw(nIcE, session, access_token, open_id, self.region, lang_code)
                    if jwt_token2:
                        final_jwt = jwt_token2
                        lock_region2, nickname2 = hElLo(jwt_token2)
                        if nickname2:
                            nickname = nickname2
                        lock_region = lock_region2
                    else:
                        lock_region = None
                last_resp = login_resp2 if need_lock and 'login_resp2' in locals() else login_resp
                client_url_raw = last_resp.get(10)
                if isinstance(client_url_raw, str):
                    client_url = client_url_raw
                elif isinstance(client_url_raw, list):
                    client_url = client_url_raw[0] if client_url_raw else None
                if client_url and client_url.startswith("https://"):
                    client_url = client_url[8:]
                if not client_url:
                    if self.region.upper() == "IND":
                        client_url = "client.ind.freefiremobile.com"
                    elif self.region.upper() in ["BR","US","NA","SAC"]:
                        client_url = "client.us.freefiremobile.com"
                    else:
                        client_url = "clientbp.ggpolarbear.com"
            else:
                client_url = "clientbp.ggpolarbear.com"
                lock_region = "GHOST"
            activated = False
            if self.auto_activate and final_jwt and client_url and not self.ghost:
                activated = wOw(bYe, session, final_jwt, client_url)
            final_region = lock_region if lock_region and not self.ghost else "GHOST"
            stored_password = store_pass
            
            acc = {
                "nickname": nickname,
                "game_uid": account_id,
                "region": final_region,
                "uid": str(uid),
                "password": stored_password,
                "activated": activated
            }
            
            with self.results_lock:
                self.saved_uids.add(uid)
            
            return acc
        except Exception as e:
            logger.error(f"[Thread-{thread_id}] Account creation error: {e}")
            return None

    def wOrKeR(self, thread_id):
        global ACCOUNT_COUNTER_FOR_IP_ROTATION
        threading.current_thread().name = f"T{thread_id}"
        while not self.stop:
            if self.created_count >= self.total_target:
                break
            with iPlOcK:
                ACCOUNT_COUNTER_FOR_IP_ROTATION += 1
                if ACCOUNT_COUNTER_FOR_IP_ROTATION >= IP_ROTATION_INTERVAL:
                    ACCOUNT_COUNTER_FOR_IP_ROTATION = 0
                    renew_tor_ip()
                    time.sleep(0.5)
            acc = self.cReAtE(thread_id)
            if acc:
                with self.lock:
                    self.created_count += 1
                self.save_single_account(acc)
                logger.info(f"[Thread-{thread_id}] Account created: {acc['uid']}")
            else:
                time.sleep(0.1)
        if self.created_count >= self.total_target:
            self.stop = True

    def rUn(self, callback=None):
        self.load_existing_uids()
        start_tor()
        time.sleep(1)
        init_session_pool()
        
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=ThReAdS) as executor:
            futures = []
            for i in range(ThReAdS):
                futures.append(executor.submit(self.wOrKeR, i+1))
            
            while self.created_count < self.total_target and not self.stop:
                time.sleep(0.5)
                if callback:
                    callback(self.created_count, self.total_target)
            
            self.stop = True
            for future in futures:
                try:
                    future.cancel()
                except:
                    pass

# =======================================================
#  TELEGRAM BOT INTEGRATION
# =======================================================

user_jobs = {}

def banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\n" * 1)
    print(render('POPPY', colors=['red', 'yellow'], align='center'))
    print("FF Generator Bot - Running on Telegram")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *Free Fire Guest Account Generator Bot*\n\n"
        "Commands:\n"
        "/gen <region> <total> <threads> – start generation\n"
        "   e.g. /gen IND 10 5\n"
        "/status – check current job progress\n"
        "/stop – cancel running job\n"
        "/download – download the generated accounts file\n\n"
        "Regions: IND, ID, TH, ME, EUROPE, VN, BD, PK, TW, RU, NA, SAC, BR, SG, US",
        parse_mode='Markdown'
    )

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_jobs and not user_jobs[user_id].get('done', True):
        await update.message.reply_text("⚠️ You already have a generation running. Use /status to check or /stop to cancel.")
        return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("❌ Usage: /gen <region> <total> <threads>\nExample: /gen IND 10 5")
        return
    
    region = args[0].upper()
    try:
        total = int(args[1])
        threads = int(args[2])
    except ValueError:
        await update.message.reply_text("❌ Total and threads must be numbers.")
        return
    
    if region not in rEgIoNlIsT:
        await update.message.reply_text(f"❌ Invalid region. Choose from: {', '.join(rEgIoNlIsT)}")
        return
    if total < 1 or total > 500:
        await update.message.reply_text("❌ Total must be between 1 and 500.")
        return
    if threads < 1 or threads > 50:
        await update.message.reply_text("❌ Threads must be between 1 and 50.")
        return
    
    global ThReAdS
    ThReAdS = threads
    
    await update.message.reply_text(f"🚀 Starting generation for {region} – {total} accounts with {threads} threads...\nUse /status to track progress.")
    
    gen = AcCoUnTcReAtOr(region, NiCkNaMe, PaSsWoRd, "plain", AuToAcT, total, GhOsT)
    
    def run_gen():
        gen.rUn()
        user_jobs[user_id]['done'] = True
        folder = "GEN/GHOST" if GhOsT else f"GEN/{region}"
        file_path = os.path.join(folder, f"Accounts-{region}.txt")
        user_jobs[user_id]['file_path'] = file_path
    
    user_jobs[user_id] = {
        'thread': threading.Thread(target=run_gen),
        'generator': gen,
        'done': False,
        'file_path': None,
        'region': region,
        'total': total
    }
    
    user_jobs[user_id]['thread'].start()

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_jobs:
        await update.message.reply_text("❌ No active or completed job.")
        return
    
    job = user_jobs[user_id]
    if job.get('done', False):
        await update.message.reply_text(f"✅ Generation completed. Use /download to get the file.")
        return
    
    gen = job['generator']
    progress = gen.created_count if gen else 0
    total = job['total']
    await update.message.reply_text(f"⏳ Progress: {progress}/{total} accounts created. (still running)")

async def stop_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_jobs:
        await update.message.reply_text("❌ No active job.")
        return
    
    job = user_jobs[user_id]
    if job.get('done', False):
        await update.message.reply_text("ℹ️ Job already finished.")
        return
    
    gen = job['generator']
    gen.stop = True
    job['done'] = True
    await update.message.reply_text("🛑 Generation stopped by user. You can start a new one with /gen.")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_jobs:
        await update.message.reply_text("❌ No job found. Generate accounts first with /gen.")
        return
    
    job = user_jobs[user_id]
    if not job.get('done', False):
        await update.message.reply_text("⏳ Generation is still running. Use /status or wait until it finishes.")
        return
    
    file_path = job.get('file_path')
    if not file_path or not os.path.exists(file_path):
        await update.message.reply_text("❌ Account file not found. Try generating again.")
        return
    
    with open(file_path, 'rb') as f:
        await update.message.reply_document(document=f, filename=os.path.basename(file_path))

# =======================================================
#  FLASK WEB DASHBOARD – Enhanced with Settings & Logs
# =======================================================

app = Flask(__name__)

stats = {
    'total_accounts': 0,
    'active_users': 0,
    'success_rate': 0,
    'uptime': 0,
    'start_time': datetime.now()
}

web_jobs = {}

# In‑memory settings (will be overridden by user updates)
current_settings = {
    'token': os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    'nickname': NiCkNaMe,
    'password': PaSsWoRd,
    'region': ReGiOn
}

# ==================== HTML Template ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POPPY Generator</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #0a0a0f;
            color: #e8e8f0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            background-image: radial-gradient(ellipse at 50% 0%, #1a1a2e 0%, #0a0a0f 70%);
        }
        .container {
            max-width: 1200px;
            width: 100%;
            background: rgba(20, 20, 35, 0.8);
            backdrop-filter: blur(20px);
            border-radius: 32px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            box-shadow: 0 25px 60px rgba(0,0,0,0.8);
            position: relative;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            flex-wrap: wrap;
            gap: 20px;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .logo-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 22px;
            color: white;
            box-shadow: 0 8px 25px rgba(238, 90, 36, 0.3);
        }
        .logo h1 {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff, #a0a0c0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .icon-btn {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 10px 16px;
            color: #c0c0e0;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: 'Inter', sans-serif;
        }
        .icon-btn:hover {
            background: rgba(255,255,255,0.12);
            transform: scale(1.02);
        }
        .icon-btn .badge {
            background: #ee5a24;
            color: white;
            font-size: 10px;
            border-radius: 50%;
            padding: 2px 8px;
            margin-left: 4px;
        }
        .status-badge {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(0, 255, 150, 0.1);
            padding: 8px 20px;
            border-radius: 100px;
            border: 1px solid rgba(0, 255, 150, 0.2);
        }
        .status-dot {
            width: 10px;
            height: 10px;
            background: #00ff96;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
            100% { opacity: 1; transform: scale(1); }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 20px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s;
        }
        .stat-card:hover {
            background: rgba(255, 255, 255, 0.06);
            transform: translateY(-2px);
        }
        .stat-card .label {
            font-size: 13px;
            font-weight: 500;
            color: #8888aa;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stat-card .value {
            font-size: 36px;
            font-weight: 700;
            margin-top: 8px;
            background: linear-gradient(135deg, #ffffff, #8888bb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #c0c0e0;
        }
        .controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            background: rgba(255, 255, 255, 0.02);
            padding: 24px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 30px;
        }
        .controls select, .controls input {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 14px 16px;
            color: #e8e8f0;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
            outline: none;
            transition: all 0.3s;
        }
        .controls select:focus, .controls input:focus {
            border-color: rgba(238, 90, 36, 0.5);
            background: rgba(255, 255, 255, 0.08);
        }
        .controls select option { background: #1a1a2e; }
        .btn {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            border: none;
            border-radius: 12px;
            padding: 14px 24px;
            color: white;
            font-weight: 600;
            font-size: 15px;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'Inter', sans-serif;
        }
        .btn:hover {
            transform: scale(1.02);
            box-shadow: 0 8px 30px rgba(238, 90, 36, 0.3);
        }
        .btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
            transform: none;
        }
        .logs {
            background: rgba(0, 0, 0, 0.4);
            border-radius: 16px;
            padding: 20px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            border: 1px solid rgba(255, 255, 255, 0.04);
        }
        .logs::-webkit-scrollbar { width: 6px; }
        .logs::-webkit-scrollbar-track { background: transparent; }
        .logs::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        .log-entry { padding: 4px 0; color: #8888bb; border-bottom: 1px solid rgba(255,255,255,0.02); }
        .log-entry .time { color: #555577; margin-right: 12px; }
        .log-entry .highlight { color: #ff6b6b; }
        .footer {
            margin-top: 30px;
            text-align: center;
            font-size: 13px;
            color: #444466;
        }

        /* Modal Styles */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(10px);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.active {
            display: flex;
        }
        .modal {
            background: #1a1a2e;
            border-radius: 24px;
            max-width: 800px;
            width: 90%;
            max-height: 85vh;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 30px 60px rgba(0,0,0,0.8);
            display: flex;
            flex-direction: column;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-header h2 {
            font-weight: 600;
            font-size: 22px;
        }
        .modal-close {
            background: none;
            border: none;
            color: #8888aa;
            font-size: 28px;
            cursor: pointer;
        }
        .modal-close:hover { color: #fff; }
        .modal-body {
            overflow-y: auto;
            flex: 1;
        }
        .modal-body .form-group {
            margin-bottom: 16px;
        }
        .modal-body label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #aaaacc;
            margin-bottom: 4px;
        }
        .modal-body input, .modal-body select {
            width: 100%;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 12px 14px;
            color: #e8e8f0;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
        }
        .modal-body input:focus, .modal-body select:focus {
            border-color: #ee5a24;
        }
        .modal-body .btn-save {
            background: linear-gradient(135deg, #00d2ff, #3a7bd5);
            border: none;
            padding: 12px 20px;
            border-radius: 10px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: 0.3s;
            width: 100%;
            font-size: 16px;
        }
        .modal-body .btn-save:hover {
            transform: scale(1.02);
            box-shadow: 0 8px 25px rgba(58, 123, 213, 0.4);
        }
        .log-viewer {
            background: #0a0a0f;
            border-radius: 12px;
            padding: 16px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 60vh;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
            color: #b0b0d0;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .log-viewer .log-line {
            padding: 2px 0;
            border-bottom: 1px solid rgba(255,255,255,0.03);
        }
        .log-viewer .log-line .ts {
            color: #555577;
            margin-right: 12px;
        }
        .log-viewer .log-line .level-info { color: #4fc3f7; }
        .log-viewer .log-line .level-warning { color: #ffb74d; }
        .log-viewer .log-line .level-error { color: #ef5350; }
        .log-viewer .log-line .level-success { color: #66bb6a; }
        @media (max-width: 600px) {
            .container { padding: 20px; }
            .logo h1 { font-size: 20px; }
            .stat-card .value { font-size: 28px; }
            .header-actions .icon-btn span { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                <div class="logo-icon">P</div>
                <h1>POPPY Generator</h1>
            </div>
            <div class="header-actions">
                <button class="icon-btn" onclick="openLogs()">
                    📜 <span>Logs</span>
                </button>
                <button class="icon-btn" onclick="openSettings()">
                    ⚙️ <span>Settings</span>
                </button>
                <div class="status-badge">
                    <div class="status-dot"></div>
                    <span>Online</span>
                </div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Accounts Generated</div>
                <div class="value" id="totalAccounts">{{ stats.total_accounts }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Active Users</div>
                <div class="value" id="activeUsers">{{ stats.active_users }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Success Rate</div>
                <div class="value" id="successRate">{{ stats.success_rate }}%</div>
            </div>
            <div class="stat-card">
                <div class="label">Uptime</div>
                <div class="value" id="uptime">{{ stats.uptime }}</div>
            </div>
        </div>

        <div class="section-title">⚡ Quick Generate</div>
        <div class="controls">
            <select id="region">
                {% for r in regions %}
                <option value="{{ r }}" {% if r == 'IND' %}selected{% endif %}>{{ r }}</option>
                {% endfor %}
            </select>
            <input type="number" id="total" placeholder="Total" value="10" min="1" max="500">
            <input type="number" id="threads" placeholder="Threads" value="5" min="1" max="50">
            <button class="btn" id="genBtn" onclick="startGeneration()">▶ Generate</button>
        </div>

        <div class="section-title">📋 Live Logs</div>
        <div class="logs" id="logContainer">
            <div class="log-entry"><span class="time">[System]</span> Bot ready. Waiting for commands...</div>
        </div>

        <div class="footer">POPPY Generator v2.0 • 24/7 on Render</div>
    </div>

    <!-- Settings Modal -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal">
            <div class="modal-header">
                <h2>⚙️ Settings</h2>
                <button class="modal-close" onclick="closeModal('settingsModal')">&times;</button>
            </div>
            <div class="modal-body">
                <form id="settingsForm" onsubmit="saveSettings(event)">
                    <div class="form-group">
                        <label>Bot Token</label>
                        <input type="text" id="botToken" placeholder="Enter new token" value="{{ current_settings.token }}">
                    </div>
                    <div class="form-group">
                        <label>Nickname Prefix</label>
                        <input type="text" id="nickname" placeholder="e.g. POPPY" value="{{ current_settings.nickname }}">
                    </div>
                    <div class="form-group">
                        <label>Password Prefix</label>
                        <input type="text" id="password" placeholder="e.g. POPPY" value="{{ current_settings.password }}">
                    </div>
                    <div class="form-group">
                        <label>Default Region</label>
                        <select id="defaultRegion">
                            {% for r in regions %}
                            <option value="{{ r }}" {% if r == current_settings.region %}selected{% endif %}>{{ r }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" class="btn-save">💾 Save & Restart Bot</button>
                </form>
                <div id="settingsStatus" style="margin-top:12px;color:#66bb6a;"></div>
            </div>
        </div>
    </div>

    <!-- Logs Modal -->
    <div class="modal-overlay" id="logsModal">
        <div class="modal">
            <div class="modal-header">
                <h2>📜 Full Logs</h2>
                <button class="modal-close" onclick="closeModal('logsModal')">&times;</button>
            </div>
            <div class="modal-body">
                <div class="log-viewer" id="fullLogViewer">Loading logs...</div>
                <div style="margin-top:12px;text-align:right;">
                    <button class="btn" onclick="fetchLogs()" style="padding:8px 16px;font-size:13px;">🔄 Refresh</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // --- Logs ---
        let logInterval = null;

        function openLogs() {
            document.getElementById('logsModal').classList.add('active');
            fetchLogs();
            if (logInterval) clearInterval(logInterval);
            logInterval = setInterval(fetchLogs, 2000);
        }

        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
            if (id === 'logsModal' && logInterval) {
                clearInterval(logInterval);
                logInterval = null;
            }
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                const viewer = document.getElementById('fullLogViewer');
                if (data.logs && data.logs.length) {
                    viewer.innerHTML = data.logs.map(line => `<div class="log-line">${line}</div>`).join('');
                } else {
                    viewer.innerHTML = '<div class="log-line">No logs yet.</div>';
                }
                viewer.scrollTop = viewer.scrollHeight;
            } catch (e) {
                document.getElementById('fullLogViewer').innerHTML = '❌ Failed to load logs.';
            }
        }

        // --- Settings ---
        function openSettings() {
            document.getElementById('settingsModal').classList.add('active');
            document.getElementById('settingsStatus').textContent = '';
        }

        async function saveSettings(e) {
            e.preventDefault();
            const token = document.getElementById('botToken').value.trim();
            const nickname = document.getElementById('nickname').value.trim();
            const password = document.getElementById('password').value.trim();
            const region = document.getElementById('defaultRegion').value;

            if (!token) {
                document.getElementById('settingsStatus').textContent = '❌ Token cannot be empty.';
                document.getElementById('settingsStatus').style.color = '#ef5350';
                return;
            }

            const payload = { token, nickname, password, region };
            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('settingsStatus').textContent = '✅ Settings saved! Bot will restart with new token.';
                    document.getElementById('settingsStatus').style.color = '#66bb6a';
                    setTimeout(() => location.reload(), 3000);
                } else {
                    document.getElementById('settingsStatus').textContent = '❌ Error: ' + data.error;
                    document.getElementById('settingsStatus').style.color = '#ef5350';
                }
            } catch (e) {
                document.getElementById('settingsStatus').textContent = '❌ Network error.';
                document.getElementById('settingsStatus').style.color = '#ef5350';
            }
        }

        // --- Existing dashboard logic ---
        const logContainer = document.getElementById('logContainer');
        const genBtn = document.getElementById('genBtn');

        function addLog(message, highlight = false) {
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            const time = new Date().toLocaleTimeString();
            entry.innerHTML = `<span class="time">[${time}]</span> ${highlight ? '<span class="highlight">' + message + '</span>' : message}`;
            logContainer.appendChild(entry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        async function startGeneration() {
            const region = document.getElementById('region').value;
            const total = document.getElementById('total').value;
            const threads = document.getElementById('threads').value;

            if (!total || total < 1 || total > 500) {
                addLog('❌ Invalid total. Must be 1-500.', true);
                return;
            }
            if (!threads || threads < 1 || threads > 50) {
                addLog('❌ Invalid threads. Must be 1-50.', true);
                return;
            }

            genBtn.disabled = true;
            genBtn.textContent = '⏳ Generating...';
            addLog(`🚀 Starting generation: ${region} | ${total} accounts | ${threads} threads`);

            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ region, total: parseInt(total), threads: parseInt(threads) })
                });
                const data = await response.json();
                if (data.success) {
                    addLog(`✅ Generation started! Job ID: ${data.job_id}`, true);
                    pollProgress(data.job_id);
                } else {
                    addLog(`❌ Error: ${data.error}`, true);
                    genBtn.disabled = false;
                    genBtn.textContent = '▶ Generate';
                }
            } catch (e) {
                addLog(`❌ Network error: ${e.message}`, true);
                genBtn.disabled = false;
                genBtn.textContent = '▶ Generate';
            }
        }

        async function pollProgress(jobId) {
            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/progress/${jobId}`);
                    const data = await res.json();
                    if (data.done) {
                        addLog(`✅ Completed! ${data.total} accounts generated.`, true);
                        clearInterval(interval);
                        genBtn.disabled = false;
                        genBtn.textContent = '▶ Generate';
                        document.getElementById('totalAccounts').textContent = data.total;
                    } else {
                        addLog(`⏳ Progress: ${data.progress}/${data.total} accounts`);
                    }
                } catch (e) {
                    // silent
                }
            }, 3000);
        }

        // Update stats periodically
        setInterval(async () => {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('totalAccounts').textContent = data.total_accounts;
                document.getElementById('activeUsers').textContent = data.active_users;
                document.getElementById('successRate').textContent = data.success_rate + '%';
                document.getElementById('uptime').textContent = data.uptime;
            } catch (e) {}
        }, 5000);

        // Close modal on overlay click
        document.querySelectorAll('.modal-overlay').forEach(el => {
            el.addEventListener('click', function(e) {
                if (e.target === this) this.classList.remove('active');
            });
        });
    </script>
</body>
</html>
"""

# ==================== Flask Routes ====================
@app.route('/')
def index():
    uptime_seconds = int((datetime.now() - stats['start_time']).total_seconds())
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    stats['uptime'] = f"{hours}h {minutes}m"
    return render_template_string(
        HTML_TEMPLATE,
        stats=stats,
        regions=rEgIoNlIsT,
        current_settings=current_settings
    )

@app.route('/api/stats')
def api_stats():
    uptime_seconds = int((datetime.now() - stats['start_time']).total_seconds())
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    return jsonify({
        'total_accounts': stats['total_accounts'],
        'active_users': stats['active_users'],
        'success_rate': stats['success_rate'],
        'uptime': f"{hours}h {minutes}m"
    })

@app.route('/api/logs')
def api_logs():
    # Return the last 1000 lines from the buffer
    return jsonify({'logs': list(LOG_BUFFER)})

@app.route('/api/settings', methods=['POST'])
def api_settings():
    data = request.json
    new_token = data.get('token', '').strip()
    new_nickname = data.get('nickname', '').strip()
    new_password = data.get('password', '').strip()
    new_region = data.get('region', '').upper()

    if not new_token:
        return jsonify({'success': False, 'error': 'Token is required'})

    # Update in‑memory settings (will be used on next bot restart)
    current_settings['token'] = new_token
    current_settings['nickname'] = new_nickname or "POPPY"
    current_settings['password'] = new_password or "POPPY"
    current_settings['region'] = new_region if new_region in rEgIoNlIsT else "IND"

    # Update global variables used by the generator
    global NiCkNaMe, PaSsWoRd, ReGiOn
    NiCkNaMe = current_settings['nickname']
    PaSsWoRd = current_settings['password']
    ReGiOn = current_settings['region']

    # Signal the bot to restart with the new token
    global bot_restart_flag
    bot_restart_flag = True

    logger.info(f"Settings updated: token={new_token[:10]}..., nickname={NiCkNaMe}, region={ReGiOn}")
    return jsonify({'success': True, 'message': 'Settings saved. Bot will restart with new token.'})

@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json
    region = data.get('region', 'IND')
    total = data.get('total', 10)
    threads = data.get('threads', 5)
    
    if region not in rEgIoNlIsT:
        return jsonify({'success': False, 'error': 'Invalid region'})
    if total < 1 or total > 500:
        return jsonify({'success': False, 'error': 'Total must be 1-500'})
    if threads < 1 or threads > 50:
        return jsonify({'success': False, 'error': 'Threads must be 1-50'})
    
    job_id = f"web_{int(time.time())}"
    stats['active_users'] += 1
    
    def run_web_gen():
        global ThReAdS
        ThReAdS = threads
        gen = AcCoUnTcReAtOr(region, NiCkNaMe, PaSsWoRd, "plain", AuToAcT, total, GhOsT)
        gen.rUn()
        stats['total_accounts'] += total
        stats['active_users'] = max(0, stats['active_users'] - 1)
        web_jobs[job_id] = {'done': True, 'total': total, 'progress': total}
    
    web_jobs[job_id] = {'done': False, 'total': total, 'progress': 0}
    threading.Thread(target=run_web_gen).start()
    
    return jsonify({'success': True, 'job_id': job_id})

@app.route('/api/progress/<job_id>')
def api_progress(job_id):
    job = web_jobs.get(job_id)
    if not job:
        return jsonify({'done': True, 'total': 0, 'progress': 0})
    return jsonify({
        'done': job.get('done', False),
        'total': job.get('total', 0),
        'progress': job.get('progress', 0)
    })

web_jobs = {}

# =======================================================
#  BOT ENGINE – with fresh event loop on each restart
# =======================================================

bot_restart_flag = False
bot_application = None

def run_bot_once(token):
    """Run the bot once with a fresh event loop. Returns True if it should restart."""
    global bot_restart_flag, bot_application
    
    # Check if we need to restart before even starting
    if bot_restart_flag:
        bot_restart_flag = False
        return True  # signal restart
    
    try:
        logger.info("🔄 Starting bot polling...")
        
        # Create a NEW event loop for this run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Build the application
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("gen", generate))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("stop", stop_generation))
        app.add_handler(CommandHandler("download", download))
        
        # Validate token (run in the new loop)
        me = loop.run_until_complete(app.bot.get_me())
        logger.info(f"✅ Bot connected: @{me.username}")
        
        bot_application = app
        
        # Run polling with close_loop=False so we control the loop lifecycle
        loop.run_until_complete(app.initialize())
        loop.run_until_complete(app.start())
        loop.run_until_complete(app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        ))
        
        # Keep the loop running until stopped
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            # Clean shutdown
            loop.run_until_complete(app.updater.stop())
            loop.run_until_complete(app.stop())
            loop.run_until_complete(app.shutdown())
            loop.close()
        
        # If we get here, polling stopped normally
        logger.info("Bot polling stopped normally.")
        return False  # don't restart
        
    except Conflict as e:
        logger.warning(f"⚠️ Conflict: {e}. Will retry...")
        return True  # restart
    except Exception as e:
        logger.error(f"❌ Polling error: {e}. Will retry...")
        return True  # restart
    finally:
        # Ensure the loop is closed if it wasn't already
        try:
            if not loop.is_closed():
                loop.close()
        except:
            pass

def bot_worker():
    """Main bot loop – keeps retrying with fresh event loops."""
    while True:
        token = current_settings.get('token', os.environ.get("TELEGRAM_BOT_TOKEN", ""))
        if not token:
            logger.error("❌ No bot token provided. Bot will not run.")
            time.sleep(60)
            continue
        
        # Run the bot once – returns True if we should restart
        should_restart = run_bot_once(token)
        
        if should_restart:
            logger.info("🔄 Restarting bot with fresh event loop...")
            # Small delay before restart
            time.sleep(2)
            continue
        
        # If polling stopped without requesting restart, wait and retry
        logger.info("Bot polling stopped. Restarting in 5s...")
        time.sleep(5)

# =======================================================
#  MAIN – Flask in background, bot in main thread
# =======================================================

def main():
    # Start Flask in a background thread
    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"✅ Web dashboard running on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False, threaded=False, processes=1)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Run the bot in the main thread
    bot_worker()

if __name__ == "__main__":
    main()
