import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By

url = "https://github.com/codewithsadee?page=1&tab=repositories"  # 目标GitHub用户仓库页面
waitTime = 2  # 普通操作等待时间(秒)
waitDownTime = 30  # 下载等待时间(秒)
positionX = 250  # 浏览器窗口X坐标
positionY = 0  # 浏览器窗口Y坐标

# 定义请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# option
def open_option(option):
    option.add_argument('--no-sandbox')
    # option.add_argument('--headless')   # “无头模式”
    option.add_experimental_option("detach", True)
    return option


# 设置 driver
def open_driver(driver):
    driver.set_window_position(positionX, positionY)
    driver.implicitly_wait(waitDownTime*2)
    driver.get(url)
    return driver

# 设置 edge
def open_edge():
    option = open_option(EdgeOptions())
    driver_Edge = webdriver.Edge(service=EdgeService('./drivers/msedgedriver.exe'), options=option)
    driver= open_driver(driver_Edge)
    return driver

# 设置 chrome
def open_chrome():
    option = open_option(ChromeOptions())
    driver_Chrome = webdriver.Chrome(service=ChromeService('./drivers/chromedriver.exe'), options=option)
    driver= open_driver(driver_Chrome)
    return driver

# 自动下载 GitHub 仓库的代码
def download_github_repo(driver):
    count = 1
    getCount = get_repo_count()
    for p in range(1,int(-(-143 // 30))+1):
        for i in range(1, 31):  # 修改范围以下载更多页面的仓库
            time.sleep(waitTime)
            a = driver.find_element(By.XPATH, f'//*[@id="user-repositories-list"]/ul/li[{i}]/div[1]/div[1]/h3/a')
            a.click()
            time.sleep(waitTime)
            try:
                codeButton = driver.find_element(By.XPATH, '//*[@id=":R55ab:"]')
                codeButton.click()
            except Exception as e1:
                try:
                    codeButton = driver.find_element(By.ID,':R55ab:')
                    codeButton.click()
                except Exception as e2:
                    codeButton = driver.find_elements(By.TAG_NAME, 'button')[23]
                    codeButton.click()
            time.sleep(waitTime)
            Down = driver.find_element(By.LINK_TEXT, "Download ZIP")
            Down.click()
            time.sleep(waitDownTime)
            driver.back()
            if count >= getCount:
                print("***-----下载完毕-----***")
                break
            else:
                print(f'第{count}库下载完成')
                count += 1
        next = driver.find_element(By.XPATH, '//*[@id="user-repositories-list"]/div/div/a')
        next.click()
        print(f'^^^^^第{p}页下载完成^^^^^')
        time.sleep(waitTime)


# 获取仓库数量
def get_repo_count():
    response = requests.get(url, headers=headers)
    response.encoding = response.apparent_encoding
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        repo_count = soup.find('span', class_='Counter').get_text(strip=True)
        print("仓库数量:",repo_count)
        return int(repo_count)
    else:
        print("无法访问该网页, 状态码: ", response.status_code)
        return 0

if __name__ == "__main__":
    # driver = open_chrome()
    # download_github_repo(driver)
    #
    # time.sleep(300)
    # driver.quit()
    for p in range(1, int(-(-143 // 30))):
        print(p)
