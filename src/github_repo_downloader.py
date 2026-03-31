import time
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By

DEFAULT_URL = "https://github.com/codewithsadee?page=1&tab=repositories"
WAIT_TIME = 2
WAIT_DOWN_TIME = 30
POSITION_X = 250
POSITION_Y = 0

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}


def open_option(option):
    option.add_argument('--no-sandbox')
    # option.add_argument('--headless')   # 无头模式，如果需要可以取消注释
    option.add_experimental_option('detach', True)
    return option


def open_driver(driver, url=DEFAULT_URL):
    driver.set_window_position(POSITION_X, POSITION_Y)
    driver.implicitly_wait(WAIT_DOWN_TIME * 2)
    driver.get(url)
    return driver


def open_edge(url=DEFAULT_URL):
    option = open_option(EdgeOptions())
    driver_edge = EdgeDriver(options=option)
    return open_driver(driver_edge, url)


def open_chrome(url=DEFAULT_URL):
    option = open_option(ChromeOptions())
    driver_chrome = ChromeDriver(options=option)
    return open_driver(driver_chrome, url)


def get_repo_count(url=DEFAULT_URL):
    response = requests.get(url, headers=HEADERS)
    response.encoding = response.apparent_encoding
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        repo_count_text = soup.find('span', class_='Counter')
        if repo_count_text:
            repo_count = repo_count_text.get_text(strip=True)
            print('仓库数量:', repo_count)
            try:
                return int(repo_count)
            except ValueError:
                return 0
    print('无法访问该网页, 状态码:', response.status_code)
    return 0


def download_github_repo(driver, url=DEFAULT_URL):
    count = 1
    get_count = get_repo_count(url)
    for p in range(1, int(-(-get_count // 30)) + 1 if get_count > 0 else 1):
        for i in range(1, 31):
            time.sleep(WAIT_TIME)
            try:
                repo_link = driver.find_element(By.XPATH, f'//*[@id="user-repositories-list"]/ul/li[{i}]/div[1]/div[1]/h3/a')
                repo_link.click()
                time.sleep(WAIT_TIME)
                try:
                    code_button = driver.find_element(By.XPATH, '//*[@id=":R55ab:"]')
                    code_button.click()
                except Exception:
                    try:
                        code_button = driver.find_element(By.ID, ':R55ab:')
                        code_button.click()
                    except Exception:
                        code_button = driver.find_elements(By.TAG_NAME, 'button')[23]
                        code_button.click()
                time.sleep(WAIT_TIME)
                down = driver.find_element(By.LINK_TEXT, 'Download ZIP')
                down.click()
                time.sleep(WAIT_DOWN_TIME)
                driver.back()
            except Exception as e:
                print(f'第 {count} 个仓库下载失败，错误: {e}')
            if count >= get_count:
                print('***-----下载完毕-----***')
                return
            else:
                print(f'第{count}库下载完成')
                count += 1
        try:
            next_button = driver.find_element(By.XPATH, '//*[@id="user-repositories-list"]/div/div/a')
            next_button.click()
            print(f'^^^^^第{p}页下载完成^^^^^')
            time.sleep(WAIT_TIME)
        except Exception as e:
            print('翻页失败，结束。', e)
            return


def run(url=DEFAULT_URL, browser='chrome'):
    if browser.lower() == 'edge':
        driver = open_edge(url)
    else:
        driver = open_chrome(url)

    try:
        download_github_repo(driver, url)
        time.sleep(300)
    finally:
        driver.quit()


if __name__ == '__main__':
    run()