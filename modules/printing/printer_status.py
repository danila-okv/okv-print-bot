# modules/printing/printer_status.py
import subprocess
import re
from typing import Dict, Optional

DEFAULT_PRINTER_IP = "192.168.31.87"
PING_COUNT = 4
PING_TIMEOUT = 1  # в секундах

def list_printers() -> Dict[str, str]:
    """
    Возвращает словарь всех принтеров CUPS и их Device URI, например:
      { "HP_LaserJet": "socket://192.168.1.50", "Office_Printer": "usb://..." }
    """
    printers: Dict[str, str] = {}
    try:
        proc = subprocess.run(
            ["lpstat", "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in proc.stdout.splitlines():
            # строка вида: device for PRINTER_NAME: URI
            if line.startswith("device for "):
                # разбиваем по ": ", первый токен — "device for PRINTER_NAME"
                before, uri = line.split(":", 1)
                name = before.replace("device for ", "").strip()
                printers[name] = uri.strip()
    except Exception:
        # молча игнорируем, вернём то, что успели найти
        pass
    return printers

def extract_ip_from_uri(uri: str) -> Optional[str]:
    """
    Пытается вытянуть IP-адрес из URI принтера.
    Работает для протоколов socket://, ipp://, http:// и т.п.
    Возвращает строку "192.168.1.50" или None.
    """
    # находим что-то вида //<хост>[:порт]
    m = re.search(r"//([^/:]+)", uri)
    if not m:
        return None
    host = m.group(1)
    # проверим, это ли IPv4
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        return host
    return None

def get_printer_ips() -> Dict[str, Optional[str]]:
    """
    Возвращает словарь {printer_name: ip_or_None}.
    """
    printers = list_printers()
    return {name: extract_ip_from_uri(uri) for name, uri in printers.items()}

def get_default_printer() -> Optional[str]:
    """
    Возвращает имя принтера по умолчанию в CUPS, или None если не задан.
    """
    try:
        proc = subprocess.run(
            ["lpstat", "-d"],
            capture_output=True,
            text=True,
            timeout=5
        )
        out = proc.stdout.strip()
        # ожидаем строку вида "system default destination: PRINTER_NAME"
        if "system default destination:" in out:
            return out.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def get_printer_status(printer: Optional[str] = None) -> str:
    """
    Возвращает один из ключевых статусов:
      - "disabled"
      - "idle"
      - "printing"
      - "unknown"
    """
    printer = printer or get_default_printer()
    if not printer:
        return "unknown: no default printer"

    try:
        proc = subprocess.run(
            ["lpstat", "-p", printer],
            capture_output=True,
            text=True,
            timeout=5
        )
        out = proc.stdout.lower()
    except Exception as e:
        return f"error: {e}"

    if "disabled" in out:
        return "disabled"
    if "idle" in out:
        return "idle"
    if "printing" in out:
        return "printing"
    return "unknown"


def get_printer_latency(
    ip: str = DEFAULT_PRINTER_IP,
    count: int = PING_COUNT,
    timeout: int = PING_TIMEOUT
) -> Optional[float]:
    """
    Пингует принтер и возвращает среднюю задержку в миллисекундах,
    или None, если пинг не удался.
    """
    try:
        proc = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), ip],
            capture_output=True,
            text=True,
            timeout=count * (timeout + 1)
        )
        out = proc.stdout
        # ищем строку формата "rtt min/avg/max/mdev = 0.123/1.234/2.345/0.456 ms"
        m = re.search(r"min/avg/max/.+? = [\d\.]+/([\d\.]+)/", out)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None


def get_printer_diagnostics() -> Dict[str, str]:
    """
    Собирает «диагностику»:
      - default_printer
      - status
      - latency
      - queue_length
      - device_uri
    """
    diag: Dict[str, str] = {}
    printer = get_default_printer()
    diag["default_printer"] = printer or "– not set –"

    # Статус
    status = get_printer_status(printer)
    diag["status"] = status

    # Пинг
    lat = get_printer_latency()
    diag["latency_ms"] = f"{lat:.1f}" if lat is not None else "timeout/fail"

    # Очередь CUPS
    try:
        proc_q = subprocess.run(
            ["lpstat", "-o"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = [ln for ln in proc_q.stdout.splitlines() if ln.strip()]
        diag["queue_length"] = str(len(lines))
    except Exception:
        diag["queue_length"] = "error"

    # Device URI
    if printer:
        try:
            proc_v = subprocess.run(
                ["lpstat", "-v", printer],
                capture_output=True,
                text=True,
                timeout=5
            )
            # строка: "device for PRINTER: uri"
            uri_line = proc_v.stdout.strip()
            diag["device_uri"] = uri_line.split(":", 1)[1].strip() if ":" in uri_line else uri_line
        except Exception:
            diag["device_uri"] = "error"
    else:
        diag["device_uri"] = "–"

    return diag