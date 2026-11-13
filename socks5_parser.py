import os
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor

import requests

OUTPUT_FILE = "socks5.txt"
INTERVAL = 15 * 60          # 15 минут
CHECK_ALIVE = True          # быстрая TCP-проверка порта (отключи, если не нужна)
CHECK_TIMEOUT = 4           # секунд на проверку одного прокси
CHECK_THREADS = 200
REQUEST_TIMEOUT = 15

SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
]

PROXY_RE = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3}):(\d{2,5})\b")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; socks5-parser/1.0)"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def valid(ip: str, port: str) -> bool:
    return all(0 <= int(p) <= 255 for p in ip.split(".")) and 1 <= int(port) <= 65535


def fetch_source(url: str) -> set[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        log(f"  ✗ {url.split('/')[2]}: {e}")
        return set()
    found = {f"{ip}:{port}" for ip, port in PROXY_RE.findall(r.text) if valid(ip, port)}
    log(f"  ✓ {url.split('/')[2]}: {len(found)}")
    return found


def is_alive(proxy: str) -> bool:
    ip, port = proxy.split(":")
    try:
        with socket.create_connection((ip, int(port)), timeout=CHECK_TIMEOUT):
            return True
    except OSError:
        return False


def filter_alive(proxies: list[str]) -> list[str]:
    with ThreadPoolExecutor(max_workers=CHECK_THREADS) as pool:
        results = pool.map(is_alive, proxies)
    return [p for p, ok in zip(proxies, results) if ok]


def save(proxies: list[str]) -> None:
    tmp = OUTPUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(proxies))
    os.replace(tmp, OUTPUT_FILE)


def update() -> None:
    log("Обновляю список SOCKS5...")
    all_proxies: set[str] = set()
    for url in SOURCES:
        all_proxies |= fetch_source(url)

    proxies = sorted(all_proxies)
    log(f"Всего уникальных: {len(proxies)}")

    if CHECK_ALIVE and proxies:
        log("Проверяю доступность...")
        proxies = filter_alive(proxies)
        log(f"Живых: {len(proxies)}")

    if proxies:
        save(proxies)
        log(f"Сохранено в {OUTPUT_FILE}")
    else:
        log("Ничего не найдено — старый файл оставлен без изменений")


def main() -> None:
    while True:
        try:
            update()
        except Exception as e:
            log(f"Ошибка: {e}")
        log(f"Следующее обновление через {INTERVAL // 60} мин.\n")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
