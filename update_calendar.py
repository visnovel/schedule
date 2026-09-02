import os
import re
import sys
import socket
import ssl
import urllib.parse
import urllib.request
import json
from datetime import datetime, date, time
from typing import List, Optional, Tuple, Dict
from bs4 import BeautifulSoup

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# УрГПУ настройки
USPU_DIRECT_IP = "213.189.223.67"
USPU_HOST = "uspu.ru"
GROUPS_TO_GENERATE = ["ИТмт-207"]

def _create_working_socket() -> ssl.SSLSocket:
    """Создает защищенный сокет с авто-поиском рабочего физического интерфейса"""
    dest_ip = USPU_DIRECT_IP
    dest_port = 443

    candidates = []
    try:
        hostname = socket.gethostname()
        local_ips = socket.gethostbyname_ex(hostname)[2]
        for ip in local_ips:
            if not ip.startswith('198.18.'):
                candidates.append(ip)
    except Exception:
        pass
    candidates.append(None) # Default routing

    last_err = None
    for src_ip in candidates:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(6)
            if src_ip:
                s.bind((src_ip, 0))
            try:
                s.connect((dest_ip, dest_port))
            except Exception:
                s.connect((USPU_HOST, dest_port))

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            ssock = ctx.wrap_socket(s, server_hostname=USPU_HOST)
            return ssock
        except Exception as e:
            last_err = e
            continue

    raise ConnectionError(f"Could not connect to USPU: {last_err}")

def fetch_schedule_html(group_name: str) -> str:
    """Получает HTML расписания с сайта УрГПУ"""
    post_data = urllib.parse.urlencode({"group_name": group_name}).encode('utf-8')

    # 1. Попытка через прямой SSL сокет с авто-биндом
    try:
        ssock = _create_working_socket()
        ssock.settimeout(10)

        req = (
            f"POST /ajax/rasp.php HTTP/1.1\r\n"
            f"Host: {USPU_HOST}\r\n"
            f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
            f"Content-Type: application/x-www-form-urlencoded; charset=UTF-8\r\n"
            f"X-Requested-With: XMLHttpRequest\r\n"
            f"Content-Length: {len(post_data)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode('utf-8') + post_data

        ssock.sendall(req)
        resp = b''
        while True:
            chunk = ssock.recv(4096)
            if not chunk:
                break
            resp += chunk
        ssock.close()

        _, _, body = resp.partition(b'\r\n\r\n')
        text = body.decode('utf-8', errors='ignore')
        if "rasp-item" in text or "rasp-para" in text or "Информационная" in text:
            return text
    except Exception as e:
        print(f"Direct socket note: {e}")

    # 2. Попытка через стандартный urllib (для облачных сред)
    try:
        req = urllib.request.Request(
            "https://uspu.ru/ajax/rasp.php",
            data=post_data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Standard urllib note: {e}")

    raise RuntimeError(f"Could not fetch schedule for {group_name}")

MONTHS_RU = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
}

def parse_time_range(time_str: str) -> tuple:
    m = re.findall(r'(\d{1,2}):(\d{2})', time_str)
    if len(m) >= 2:
        return (time(int(m[0][0]), int(m[0][1])), time(int(m[1][0]), int(m[1][1])))
    return (time(8, 30), time(10, 0))

def generate_ics_content(html: str, group_name: str, subgroup: int = 0) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    current_year = datetime.now().year

    sub_title = f" (Подгруппа {subgroup})" if subgroup and subgroup > 0 else ""
    cal_name = f"УрГПУ {group_name}{sub_title}"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//USPU GitHub Calendar Feed//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_name}",
        "X-WR-TIMEZONE:Asia/Yekaterinburg",
        "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
        "X-PUBLISHED-TTL:PT15M",
        "BEGIN:VTIMEZONE",
        "TZID:Asia/Yekaterinburg",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0500",
        "TZOFFSETTO:+0500",
        "TZNAME:+05",
        "END:STANDARD",
        "END:VTIMEZONE"
    ]

    for item in soup.find_all('div', class_='rasp-item'):
        day_el = item.find('span', class_='rasp-day')
        if not day_el:
            continue

        raw_date = day_el.get_text(strip=True).lower()
        parts = raw_date.split()
        if len(parts) < 2:
            continue

        try:
            day_num = int(parts[0])
            month_num = MONTHS_RU.get(parts[1], 1)
            target_date = date(current_year, month_num, day_num)
        except Exception:
            continue

        for para in item.find_all('div', class_='rasp-para'):
            time_el = para.find('span', class_='para-time')
            desc_el = para.find('div', class_='rasp-desc')
            if not desc_el or not time_el:
                continue

            p_tag = desc_el.find('p')
            if not p_tag:
                continue

            full_subject = ""
            for c in p_tag.contents:
                if isinstance(c, str) and c.strip():
                    full_subject = c.strip()
                    break

            lesson_type = ""
            type_m = re.search(r'\(([^)]+)\)$', full_subject)
            subject_clean = full_subject
            if type_m:
                lesson_type = type_m.group(1).strip()
                subject_clean = full_subject[:type_m.start()].strip()

            span = p_tag.find('span')
            auditorium = ""
            teacher = ""
            pair_subgroup = None

            if span:
                for line in [l.strip() for l in span.get_text('\n').split('\n') if l.strip()]:
                    if line.startswith("Преподаватель:"):
                        teacher = line.replace("Преподаватель:", "").strip()
                    elif line.startswith("(") and "подгруппа" in line.lower():
                        pair_subgroup = line.strip("() ")
                    elif not auditorium and not line.startswith("Группа:"):
                        auditorium = line

            # Фильтрация по подгруппе
            if subgroup > 0 and pair_subgroup:
                sub_low = pair_subgroup.lower()
                if f"подгруппа {subgroup}" not in sub_low and f"{subgroup} подгруппа" not in sub_low:
                    continue

            t_start, t_end = parse_time_range(time_el.get_text(strip=True))
            dt_start = datetime.combine(target_date, t_start).strftime("%Y%m%dT%H%M%S")
            dt_end = datetime.combine(target_date, t_end).strftime("%Y%m%dT%H%M%S")

            clean_sub = re.sub(r'[^a-zA-Z0-9а-яА-Я]', '', subject_clean)
            uid = f"{target_date.strftime('%Y%m%d')}-{t_start.strftime('%H%M')}-{clean_sub}-{pair_subgroup or 'all'}@uspu"

            summary = subject_clean
            if lesson_type:
                summary += f" ({lesson_type})"
            if pair_subgroup:
                summary += f" [{pair_subgroup}]"

            desc_text = f"Преподаватель: {teacher}\\nАудитория: {auditorium}\\nГруппа: {group_name}"

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART;TZID=Asia/Yekaterinburg:{dt_start}",
                f"DTEND;TZID=Asia/Yekaterinburg:{dt_end}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc_text}",
                f"LOCATION:{auditorium or 'УрГПУ'}",
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

def main():
    print(f"[{datetime.now()}] Updating calendars for groups: {GROUPS_TO_GENERATE}...")

    for group in GROUPS_TO_GENERATE:
        try:
            html = fetch_schedule_html(group)

            # 1. Полный календарь (все подгруппы)
            ics_all = generate_ics_content(html, group, subgroup=0)
            with open(f"{group}_all.ics", "w", encoding="utf-8") as f:
                f.write(ics_all)
            with open(f"{group}.ics", "w", encoding="utf-8") as f:
                f.write(ics_all)

            # 2. Подгруппа 1
            ics_sub1 = generate_ics_content(html, group, subgroup=1)
            with open(f"{group}_sub1.ics", "w", encoding="utf-8") as f:
                f.write(ics_sub1)

            # 3. Подгруппа 2
            ics_sub2 = generate_ics_content(html, group, subgroup=2)
            with open(f"{group}_sub2.ics", "w", encoding="utf-8") as f:
                f.write(ics_sub2)

            print(f"Successfully generated .ics files for {group} (all, sub1, sub2)")
        except Exception as e:
            print(f"Error updating {group}: {e}")

if __name__ == "__main__":
    main()
