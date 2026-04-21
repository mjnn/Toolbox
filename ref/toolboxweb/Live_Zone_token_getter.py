import logging
import time

import requests
from TimeStampProcessor import *
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import warnings
from urllib3.exceptions import InsecureRequestWarning
from decimal import Decimal, getcontext
import random
from selenium_chrome import chrome_driver_service, chrome_options_headless_legacy

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)


def web_driver_login(login_page, username, password, success_title, xpath_dict):
    options = chrome_options_headless_legacy()
    driver = webdriver.Chrome(service=chrome_driver_service(), options=options)
    driver.get(login_page)
    logging.debug('尝试登录:', login_page)
    login_button = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, xpath_dict['login_button']))
    )
    username_input_box = driver.find_element(
        By.XPATH, xpath_dict['username_input_box']
    )
    password_input_box = driver.find_element(
        By.XPATH, xpath_dict['password_input_box']
    )
    username_input_box.send_keys(username)
    password_input_box.send_keys(password)
    login_button.click()
    try:
        WebDriverWait(driver, 10).until(
            EC.title_is(success_title)
        )
    except selenium.common.exceptions.TimeoutException:
        logging.error('登录失败')
    except Exception as e:
        logging.error('登录失败:', e)
    logging.debug('登录成功')
    return driver


def web_driver_login_svw_oa(username, password):
    """Minimized LIVE OA bootstrap for Zone token flow.

    Keep this local to avoid importing `LiveTokenGetter` module-level deps
    (e.g. Outlook/win32com) when only Zone LIVE cookies are needed.
    """
    logging.debug('初始化Chromedriver')
    options = chrome_options_headless_legacy()
    driver = webdriver.Chrome(service=chrome_driver_service(), options=options)
    logging.debug('访问SVW OA登录页面')
    driver.get('https://portal.csvw.com')
    try:
        WebDriverWait(driver, 10).until(
            EC.title_is('上汽大众高效协同平台')
        )
    except selenium.common.exceptions.TimeoutException:
        logging.error('登录失败')
    logging.debug('登录成功')
    return driver


def web_driver_get_zone_live_token_cookies():
    driver = web_driver_login_svw_oa('18186', 'Mjnn991126$%')
    driver.get('https://mosop.csvw.com/#/login')
    live_sp_button = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="main-app"]/div[2]/div[2]/div/div[4]/button[2]'))
    )
    live_sp_button.click()
    af_dp_button = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located(
            (By.XPATH, '//*[@id="main-app"]/div[2]/div[2]/div[2]/div[2]/div[1]/div/div/div[3]/div/div/div[2]/div[1]'))
    )
    time.sleep(1)
    af_dp_button.click()
    driver.get('https://zaccount-zone.mosop.csvw.com/MyService/MyService')
    try:
        WebDriverWait(driver, 10).until(
            EC.title_is('我的服务')
        )
    except selenium.common.exceptions.TimeoutException:
        logging.error('登录Zone账号失败')
    except Exception as e:
        logging.error('登录Zone账号失败:', e)
    logging.debug('登录Zone账号成功')
    zone_token = driver.get_cookie('ACCOUNT-TOKEN')['value']
    cookies_for_request = ''
    for cookie_dict in driver.get_cookies():
        cookies_for_request = cookies_for_request+cookie_dict['name']+'='+cookie_dict['value']+'; '
    return zone_token, cookies_for_request


def post_request_to_zone_live_usap(url, payload, zone_token, cookies):
    s = requests.Session()
    headers = {
        'x-token': 'Bearer ' + zone_token.split('+')[1],
        'x-source': 'USAP',
        'x-timestamp': str(timestamp_now(TimestampType.ms)),
        'x-v': '1.0',
        'origin': 'https://usap-zone.mosop.csvw.com',
        'cookie': cookies,
        'tenantcode': 'VW'
    }
    response = s.post(url, json=payload, headers=headers, verify=False)
    return response


def get_request_to_zone_live_usap(url, zone_token, cookies):
    s = requests.Session()
    headers = {
        'x-token': 'Bearer ' + zone_token.split('+')[1],
        'x-source': 'USAP',
        'x-timestamp': str(timestamp_now(TimestampType.ms)),
        'x-v': '1.0',
        'origin': 'https://usap-zone.mosop.csvw.com',
        'cookie': cookies,
        'tenantcode': 'VW'
    }
    response = s.get(url, headers=headers, verify=False)
    return response


def generate_17_decimal_random():
    getcontext().prec = 19
    max_val_for_int = 10 ** 17 - 1
    random_integer = random.randint(0, max_val_for_int)
    decimal_integer = Decimal(str(random_integer))
    divisor = Decimal(str(10 ** 17))
    result = decimal_integer / divisor
    return f"{result:.17f}"

# #还没有改
# def post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies):
#     s = requests.Session()
#     headers = {
#         'x-token': 'Bearer ' + zone_token.split('+')[1],
#         'x-source': 'vehicleinfo_bp_sys',
#         'x-timestamp': str(timestamp_now(TimestampType.ms)),
#         'x-v': '1.0',
#         'origin': 'https://vehicleinfo-zone.mosop-uat.csvw.com',
#         'cookie': cookies,
#         'tenantcode': 'VW'
#     }
#     response = s.post(url, json=payload, headers=headers, verify=False)
#     return response
#
#
# #还没有改
# def get_request_to_zone_vehicleinfo(url, zone_token, cookies):
#     s = requests.Session()
#     headers = {
#         'x-token': 'Bearer ' + zone_token.split('+')[1],
#         'x-source': 'vehicleinfo_bp_sys',
#         'x-timestamp': str(timestamp_now(TimestampType.ms)),
#         'x-v': '1.0',
#         'origin': 'https://vehicleinfo-zone.mosop-uat.csvw.com',
#         'cookie': cookies,
#         'tenantcode': 'VW'
#     }
#     response = s.get(url, headers=headers, verify=False)
#     return response
