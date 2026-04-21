import logging
import json
import time
from datetime import datetime
import requests
import selenium.common.exceptions
from PasswordEncrypter import encrypt_password
from selenium_chrome import chrome_driver_service, chrome_options_headless_legacy
from TimeStampProcessor import *
import re
import json
import requests
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import warnings
from urllib3.exceptions import InsecureRequestWarning
import pandas as pd
from credential_helper import get_account_password

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

_OUTLOOK_IMPORT_ERROR: Exception | None = None
try:
    from OutlookMailProcessor import get_vcode_list as _get_vcode_list
except Exception as exc:  # noqa: BLE001
    _OUTLOOK_IMPORT_ERROR = exc
    _get_vcode_list = None


def get_pubkey_info():
    s = requests.session()
    url = 'https://eidp.csvw.com/esc-sso/api/v3/auth/queryAllValid'
    parameter = {
        '_': timestamp_now(TimestampType.ms)
    }
    response = s.get(url=url, params=parameter)
    pubkey = json.loads(response.text)['data']['param']['publicKey']
    pubkey_id = json.loads(response.text)['data']['param']['publicKeyId']
    return s, pubkey, pubkey_id


def login_layer_one(username, password):
    # 获取公钥和公钥ID
    s, pubkey, pubkey_id = get_pubkey_info()
    url1 = 'https://eidp.csvw.com/ngw/context'
    payload = {
        '_': timestamp_now(TimestampType.ms)
    }
    s.get(url1, params=payload)
    url2 = 'https://eidp.csvw.com/esc-sso/api/v3/auth/queryAllValid'
    payload = {
        '_': timestamp_now(TimestampType.ms)
    }
    s.get(url2, params=payload)
    url3 = 'https://eidp.csvw.com/esc-sso/api/v3/auth/queryUserValid?username=18186&authType=webLocalAuth&_=1757057058674'
    payload = {
        'username': '18186',
        'authType': 'webLocalAuth',
        '_': timestamp_now(TimestampType.ms)
    }
    s.get(url3, params=payload)
    # 使用公钥加密密码
    encrypted_password = encrypt_password(public_key_str=pubkey, plaintext=password)
    url = 'https://eidp.csvw.com/esc-sso/api/v3/auth/doLogin'
    payload = {
        "authType": "webLocalAuth",
        "dataField": {
            "username": username,
            "password": encrypted_password,
            "vcode": "",
            "publicKeyId": pubkey_id
        },
        "redirectUri": ""
    }
    s.post(url=url, json=payload)
    payload = {
        '_': timestamp_now(TimestampType.ms)
    }
    response = s.get(url1, params=payload)
    eidp_context = json.loads(response.text)
    url4 = 'https://eidp.csvw.com/portal/rest/selfcare/findUser'
    payload = {
        '_': timestamp_now(TimestampType.ms)
    }
    response = s.get(url4, params=payload)
    user_info = json.loads(response.text)

    url5 = 'https://eidp.csvw.com/portal/rest/selfcare/passwordPolicy/remind/passwordExpired'
    payload = {
        '_': timestamp_now(TimestampType.ms)
    }
    s.get(url5, params=payload)
    return s


def get_appId_and_appurl(appname, username, password):
    s = login_layer_one(username, password)
    url = 'https://eidp.csvw.com/portal/rest/selfcare/apps'
    form_data = {
        '_': timestamp_now(TimestampType.ms)
    }
    response = s.get(url=url, params=form_data)
    applist = json.loads(response.text)['data']
    appid = ''
    appurl = ''
    # print(json.dumps(applist,indent=4))
    for app in applist:
        if app['name'] == appname:
            appid = app['key']
            appurl = app['resUrl']
        else:
            pass
    return appid, appurl


def web_driver_login_svw_oa(username, password):
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
    # login_button = WebDriverWait(driver, 120).until(
    #     EC.presence_of_element_located((By.XPATH, '//*[@id="username"]/div[2]/button'))
    # )
    # logging.debug('登录页面加载完成')
    # username_input_box = driver.find_element(
    #     By.XPATH, '//*[@id="username"]/div[1]/div[1]/div[1]/div[1]/div/input'
    # )
    # password_input_box = driver.find_element(
    #     By.XPATH, '//*[@id="username"]/div[1]/div[1]/div[2]/div[1]/div/input'
    # )
    # logging.debug('输入账密')
    # username_input_box.send_keys(username)
    # password_input_box.send_keys(password)
    # logging.debug('点击登录')
    # login_button.click()
    # try:
    #     WebDriverWait(driver, 10).until(
    #         EC.title_is('IT账号自助服务')
    #     )
    # except selenium.common.exceptions.TimeoutException:
    #     logging.error('登录失败')
    # logging.debug('登录成功')
    # return driver


def get_app_live_token(appname):
    username, password = get_account_password('oa')
    driver = web_driver_login_svw_oa(username, password)
    appid, appurl = get_appId_and_appurl(appname, username, password)
    driver.get(appurl)
    if appname=='MOS Portal':
        login_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="main-app"]/div[2]/div[2]/div/div[4]/button[2]'))
        )
        login_button.click()
    email_validation_button = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="random-module"]/div/div[2]/div/span'))
    )
    email_validation_button.click()
    send_vcode_button = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="email"]/div[1]/div[1]/div[2]/div[1]/div/div'))
    )
    send_vcode_button.click()
    if _get_vcode_list is None:
        raise RuntimeError(
            "当前环境缺少 Outlook 邮箱验证码依赖（win32com/pythoncom）。"
            "如需使用 LIVE 邮箱二次验证流程，请安装 pywin32 并确保本机可访问 Outlook。"
        ) from _OUTLOOK_IMPORT_ERROR
    vcode_list = _get_vcode_list()
    vcode = ''
    for vcode_dict in vcode_list:
        try:
            if vcode_dict['应用'] == appname:
                vcode = vcode_dict['验证码']
                break
            else:
                pass
        except KeyError as e:
            print(e)
            break
    if vcode != '':
        vcode_input_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="email"]/div[1]/div[1]/div[2]/div[1]/div/input'))
        )
        vcode_input_box.send_keys(vcode)
        login_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="email"]/div[2]/button'))
        )
        login_button.click()
        if appname == 'MOS Portal':
            login_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="main-app"]/div[2]/div[2]/div/div[4]/button[2]'))
            )
            login_button.click()
            time.sleep(2)
            tokens = WebDriverWait(driver, 10).until(
                wait_to_get_token(driver, 'sessionStorage', ['dashboard-token', 'refreshToken'])
            )
        else:
            time.sleep(2)
            tokens = WebDriverWait(driver, 10).until(
                wait_to_get_token(driver, 'localStorage', ['token'])
            )
        driver.quit()
        return tokens


def wait_to_get_token(driver, storage_type, token_names):
    def get_token(driver):
        token_dict = {}
        for token_name in token_names:
            token_value = driver.execute_script(f"return {storage_type}.getItem('{token_name}');")
            token_dict[token_name] = token_value
        return token_dict
    return get_token




