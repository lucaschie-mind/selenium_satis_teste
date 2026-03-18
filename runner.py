import imaplib
import os
import re
import time
import traceback
from dataclasses import dataclass, field
from email import message_from_bytes, policy
from pathlib import Path
from typing import Callable, List, Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


LogFn = Callable[[str], None]


def env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {name}")
    return value or ""


@dataclass
class RunResult:
    success: bool
    logs: List[str] = field(default_factory=list)
    screenshot_path: Optional[str] = None
    current_url: Optional[str] = None
    otp_code: Optional[str] = None
    error: Optional[str] = None


class Logger:
    def __init__(self):
        self.lines: List[str] = []

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.lines.append(f"[{timestamp}] {message}")


def _extract_text(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    if not payload:
        return ""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


def get_latest_otp_from_gmail(user: str, password: str, logger: LogFn, sender: str = "noreply@mg.mindsight.com.br", timeout: int = 120, poll_interval: int = 3) -> Optional[str]:
    logger("Conectando ao Gmail via IMAP para buscar o OTP...")
    last_uid = None
    start_time = time.time()

    def connect():
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(user, password)
        imap.select("INBOX")
        return imap

    imap = connect()
    try:
        status, data = imap.search(None, f'(FROM "{sender}")')
        if status == "OK" and data and data[0]:
            ids = data[0].split()
            if ids:
                last_uid = ids[-1]
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    while time.time() - start_time <= timeout:
        time.sleep(poll_interval)
        imap = connect()
        try:
            status, data = imap.search(None, f'(FROM "{sender}")')
            if status != "OK" or not data or not data[0]:
                continue
            ids = data[0].split()
            if not ids:
                continue
            newest_uid = ids[-1]
            if newest_uid == last_uid:
                continue
            status, msg_data = imap.fetch(newest_uid, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = message_from_bytes(raw, policy=policy.default)
            body = _extract_text(msg).replace("", "")
            match = re.search(r"(\d{4,10})", body)
            if match:
                otp = match.group(1)
                logger("OTP encontrado no Gmail.")
                return otp
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    logger("Tempo esgotado aguardando o OTP no Gmail.")
    return None


def build_driver(download_dir: str, headless: bool, logger: LogFn):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,1200")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
        logger(f"Usando Chrome/Chromium em: {chrome_bin}")

    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    if chromedriver_path:
        logger(f"Usando ChromeDriver em: {chromedriver_path}")
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        logger("Usando Selenium Manager para resolver o driver automaticamente.")
        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(60)
    return driver


def wait_visible(driver, by, selector, timeout=20):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, selector)))


def wait_clickable(driver, by, selector, timeout=20):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))


def run_login_test(tenant: str, headless: bool = True) -> RunResult:
    logger = Logger()
    screenshot_path = None
    driver = None
    current_url = None
    otp_code = None
    try:
        if not tenant:
            raise RuntimeError("Informe o tenant na interface ou configure a variável TENANT no Railway.")

        mindsight_email = env("MINDSIGHT_EMAIL", required=True)
        mindsight_password = env("MINDSIGHT_PASSWORD", required=True)
        gmail_email = env("GMAIL_EMAIL", default=mindsight_email)
        gmail_app_password = env("GMAIL_APP_PASSWORD", required=True)

        base_dir = Path("/tmp/selenium_job")
        base_dir.mkdir(parents=True, exist_ok=True)
        download_dir = base_dir / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        screenshot_dir = base_dir / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        logger.log("Iniciando navegador...")
        driver = build_driver(str(download_dir), headless=headless, logger=logger.log)

        login_url = f"https://auth.mindsight.com.br/{tenant}/"
        logger.log(f"Abrindo URL: {login_url}")
        driver.get(login_url)
        current_url = driver.current_url

        if driver.current_url.rstrip("/") == login_url.rstrip("/"):
            logger.log("Sessão já autenticada para esse tenant. Nenhum login necessário.")
            screenshot_path = str(screenshot_dir / f"{tenant}_already_logged.png")
            driver.save_screenshot(screenshot_path)
            return RunResult(True, logger.lines, screenshot_path=screenshot_path, current_url=driver.current_url)

        logger.log("Preenchendo credenciais...")
        username = wait_visible(driver, By.ID, "id_username", timeout=25)
        username.clear()
        username.send_keys(mindsight_email)

        password = wait_visible(driver, By.ID, "id_password", timeout=25)
        password.clear()
        password.send_keys(mindsight_password)

        wait_clickable(driver, By.XPATH, "//button[@type='submit']", timeout=25).click()
        logger.log("Login enviado. Aguardando tela de OTP...")

        otp_url = f"https://auth.mindsight.com.br/{tenant}/accounts/login_otp/"
        WebDriverWait(driver, 30).until(lambda d: otp_url in d.current_url or "Login inválido" in d.page_source)
        current_url = driver.current_url

        if "Login inválido" in driver.page_source:
            raise RuntimeError("Login inválido na tela do auth. Revise MINDSIGHT_EMAIL e MINDSIGHT_PASSWORD.")

        otp_code = get_latest_otp_from_gmail(gmail_email, gmail_app_password, logger.log)
        if not otp_code:
            raise RuntimeError("Não foi possível capturar o OTP no Gmail dentro do tempo limite.")

        otp_input = wait_visible(driver, By.NAME, "otp_token", timeout=20)
        otp_input.clear()
        otp_input.send_keys(otp_code)
        wait_clickable(driver, By.CLASS_NAME, "submit-btn", timeout=20).click()
        logger.log("OTP enviado. Aguardando redirecionamento final...")

        WebDriverWait(driver, 30).until(lambda d: otp_url not in d.current_url)
        current_url = driver.current_url
        logger.log(f"Login concluído. URL final: {current_url}")

        screenshot_path = str(screenshot_dir / f"{tenant}_success.png")
        driver.save_screenshot(screenshot_path)
        logger.log(f"Screenshot salva em: {screenshot_path}")

        return RunResult(
            success=True,
            logs=logger.lines,
            screenshot_path=screenshot_path,
            current_url=current_url,
            otp_code=otp_code,
        )
    except TimeoutException as exc:
        error = f"Timeout durante a automação: {exc}"
        logger.log(error)
        logger.log(traceback.format_exc())
        if driver:
            current_url = driver.current_url
            screenshot_path = screenshot_path or "/tmp/selenium_job/screenshots/error_timeout.png"
            try:
                driver.save_screenshot(screenshot_path)
            except Exception:
                pass
        return RunResult(False, logger.lines, screenshot_path=screenshot_path, current_url=current_url, otp_code=otp_code, error=error)
    except Exception as exc:
        error = str(exc)
        logger.log(f"Erro: {error}")
        logger.log(traceback.format_exc())
        if driver:
            try:
                current_url = driver.current_url
            except Exception:
                pass
            screenshot_path = screenshot_path or "/tmp/selenium_job/screenshots/error_generic.png"
            try:
                driver.save_screenshot(screenshot_path)
            except Exception:
                pass
        return RunResult(False, logger.lines, screenshot_path=screenshot_path, current_url=current_url, otp_code=otp_code, error=error)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
