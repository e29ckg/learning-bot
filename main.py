import time
import json
import os, random
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------------- CONFIG ---------------- #
from config import course_url, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
cookies_file = "cookies.json"

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6700.90 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6700.90 Safari/537.36",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6700.90 Safari/537.36 Edg/129.0.6700.90"
    ]
    return random.choice(user_agents)

# ---------------- SETUP ---------------- #
options = uc.ChromeOptions()
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument(f"user-agent={get_random_user_agent()}")
options.add_argument("--disable-blink-features=AutomationControlled")

prefs = {"profile.default_content_setting_values.notifications": 2}
options.add_experimental_option("prefs", prefs)

driver = None
try:
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    # ---------------- FUNCTIONS ---------------- #
    def send_telegram_message(text: str):
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
                timeout=10
            )
        except Exception as e:
            print(f"ไม่สามารถส่งข้อความ Telegram: {e}")

    def send_telegram_photo(driver, caption=""):
        screenshot_path = "screenshot.png"
        driver.save_screenshot(screenshot_path)
        try:
            with open(screenshot_path, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                    files={"photo": f},
                    timeout=20
                )
            print(">>> ส่ง screenshot ไป Telegram แล้ว")
        except Exception as e:
            print(f"ไม่สามารถส่ง screenshot Telegram: {e}")

    def save_cookies(driver, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(driver.get_cookies(), f, ensure_ascii=False, indent=2)
        print(f"✅ บันทึก cookies ลงไฟล์ {path} แล้ว")

    def load_cookies(driver, path, url):
        if not os.path.exists(path):
            return False
        driver.get(url)
        with open(path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
            for cookie in cookies:
                cookie.pop("sameSite", None)
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"ไม่สามารถเพิ่ม cookie: {cookie.get('name')} → {e}")
        print(f"✅ โหลด cookies จาก {path} แล้ว")
        return True

    def is_logged_in(driver):
        return "login" not in driver.current_url.lower() and "challenge" not in driver.current_url.lower()

    def force_relogin(driver):
        driver.get(course_url)
        send_telegram_message("⚠️ Session หมดอายุ → กรุณา login/สแกน QR/กด Verify ใหม่")
        send_telegram_photo(driver, caption="📸 หน้าจอ Login/Verify (Session หมดอายุ)")
        time.sleep(30)
        if is_logged_in(driver):
            save_cookies(driver, cookies_file)
            send_telegram_message("✅ Login ใหม่สำเร็จ และ cookies ถูกบันทึกแล้ว")
            send_telegram_photo(driver, caption="📸 Dashboard หลัง Login ใหม่")
            return True
        else:
            send_telegram_message("❌ Login ใหม่ไม่สำเร็จ")
            send_telegram_photo(driver, caption="📸 หน้าจอ Login (Login ไม่สำเร็จ)")
            return False

    def ensure_session(driver):
        if not is_logged_in(driver):
            return force_relogin(driver)
        return True

    # ---------------- LOGIN ---------------- #
    if load_cookies(driver, cookies_file, course_url):
        driver.get(course_url)
        time.sleep(5)
        if is_logged_in(driver):
            send_telegram_message("✅ ใช้ cookies เดิม login สำเร็จ")
            send_telegram_photo(driver, caption="📸 Dashboard (cookies เดิม)")
        else:
            os.remove(cookies_file)
            if not force_relogin(driver):
                exit()
    else:
        driver.get(course_url)
        print("⚠️ ยังไม่มี cookies → กรุณา login/สแกน QR/กด Verify ด้วยตัวเอง")
        time.sleep(60)
        if is_logged_in(driver):
            save_cookies(driver, cookies_file)
            driver.get(course_url)
        else:
            exit()

    # ---------------- MAIN LOOP ---------------- #
    lesson_links = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH,
             '//a[.//span and '
             'not(.//span[starts-with(normalize-space(.), "แบบทดสอบ")]) and '
             'not(.//span[contains(., "เอกสารประกอบการสอน")]) and '
             'not(.//span[contains(., "สไลด์ประกอบการสอน")]) and '
             'not(.//span[contains(., "แบบประเมิน")])]'
             )
        )
    )
    print(f"พบทั้งหมด {len(lesson_links)} บทเรียน")

    for idx, element in enumerate(lesson_links, start=1):
        if not ensure_session(driver):
            break

        topic = element.text.strip()
        print(f"{idx}: {topic} {element.get_attribute('href')}")

        # if not topic.startswith("บทที่"):
        #     continue
        # if "แบบประเมิน" in topic:
        #     send_telegram_message("📘 พบ 'แบบประเมิน' → จบโปรแกรม")
        #     break

        element.click()
        time.sleep(2)

        wait_text = "คุณสะสมเวลาเรียนในหัวข้อนี้ครบตามที่กำหนดแล้ว"
        xpath_st = '//*[@id="root"]/div[3]/div/div[3]/div'
        send_telegram_message(f"▶️ เริ่มเรียนบทเรียน: {topic}")

        while True:
            if not ensure_session(driver):
                break
            try:
                element_st = driver.find_element(By.XPATH, xpath_st).text.strip()
            except NoSuchElementException:
                element_st = ""

            if element_st == wait_text:
                print(f"✅ Completed topic: {topic}")
                break
            else:
                print("⏳ ยังไม่ครบเวลา → รออีก 1 นาที ...")
                time.sleep(63)

    print('>>> End program')
    send_telegram_message("🏁 โปรแกรมทำงานเสร็จสิ้นแล้ว")
    send_telegram_photo(driver, caption="📸 หน้าจอสุดท้ายก่อนปิดโปรแกรม")

except Exception as e:
    print(f"Error during driver operation: {e}")
finally:
    if driver:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error while quitting driver: {e}")