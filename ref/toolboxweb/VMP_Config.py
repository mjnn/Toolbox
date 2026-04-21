import json
import logging
import time
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from credential_helper import get_account_password
from legacy_paths import static_path
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


def web_driver_get_vmp_cookies():
    username, password = get_account_password('uat_mos_portal')
    with open(static_path("config", "xpath.json"), encoding="utf-8") as f:
        xpath_json = f.read()
        xpath_dict = json.loads(xpath_json)
        oa_login_xpath_dict = xpath_dict['uat_mos_portal_login_page']
    driver = web_driver_login('https://mosop-uat.csvw.com/#/login', username, password, '', oa_login_xpath_dict)
    cea_button = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH,
                                        '//*[@id="main-app"]/div[2]/div[2]/div[2]/div[2]/div[1]/div/div/div[4]/div/div/div[2]/div[1]'))
    )
    cea_button.click()
    time.sleep(5)
    driver.get('https://e-portal.uat.cn-svw.volkswagen-cea.com/#/home')
    vmp_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/section/div[2]/div/div/div/div/h3'))
    )
    vmp_button.click()
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/section/div[2]/ul/div/li[2]/ul/a[1]/li/span'))
    )
    WebDriverWait(driver, 10).until(
        EC.title_is('车辆管理平台')
    )
    cookies_for_request = ''
    for cookie_dict in driver.get_cookies():
        cookies_for_request = cookies_for_request+cookie_dict['name']+'='+cookie_dict['value']+'; '
    print('获取到VMP 请求Cookies: ', cookies_for_request)
    return cookies_for_request


def request_to_vmp(url, cookies, method, payload=None):
    s = requests.Session()
    headers = {
        'cookie': cookies
    }
    if method == 'GET':
        response_str = s.get(url, headers=headers, verify=False).text
        print(response_str)
        return response_str
    elif method == 'POST':
        if payload == None:
            response = '请求体为空'
        else:
            response = s.post(url, json=payload, headers=headers, verify=False)
            response = response.text
        return response


def query_vehicle_info(by, value, cookies):
    if by == 'vin':
        response_json = request_to_vmp(
            f'https://vmp-portal.uat.cn-svw.volkswagen-cea.com/api/vehicle/info/vin?vin={value}',
            cookies,
            'GET'
        )
    elif by == 'iccid':
        response_json = request_to_vmp(
            f'https://vmp-portal.uat.cn-svw.volkswagen-cea.com/api/vehicle/info/iccid?iccid={value}',
            cookies,
            'GET'
        )
    elif by == 'cduid':
        response_json = request_to_vmp(
            f'https://vmp-portal.uat.cn-svw.volkswagen-cea.com/api/vehicle/info/cduid?cduId={value}',
            cookies,
            'GET'
        )
    else:
        response_json = '{"code":404,"msg":"搜索项不存在！"}'
    response_dict = json.loads(response_json)
    status_code = response_dict['code']
    if status_code == 200:
        vehicle_info_dict = response_dict['data']
        result = True, vehicle_info_dict
    else:
        error_msg = response_dict['msg']
        result = False, error_msg
    return result


def query_cdcu_info(by, value, cookies):
    if by == 'cduid':
        response_json = request_to_vmp(
            f'https://vmp-portal.uat.cn-svw.volkswagen-cea.com/api/cdu/info?query={value}&type=1',
            cookies,
            'GET'
        )
    elif by == 'iccid':
        response_json = request_to_vmp(
            f'https://vmp-portal.uat.cn-svw.volkswagen-cea.com/api/cdu/info?query={value}&type=2',
            cookies,
            'GET'
        )
    else:
        result = False, f'请求参数错误:{by}'
        return result
    response_dict = json.loads(response_json)
    status_code = response_dict['code']
    if status_code == 200:
        vehicle_info_dict = response_dict['data']
        result = True, vehicle_info_dict
    else:
        error_msg = response_dict['msg']
        result = False, error_msg
    return result


def get_vmp_data_status(by, value, cookies):
    vmp_get_result = {}
    status_vehicle, result_vehicle = query_vehicle_info(by, value, cookies)
    if not status_vehicle:
        # VIN查询失败
        if result_vehicle == '未在车辆管理平台登记,请联系管理员' and (by == 'cduid' or by == 'iccid'):
            # 用CDCU信息查VIN查不到
            status_cdcu, result_cdcu = query_cdcu_info(by, value, cookies)
            if not status_cdcu:
                # CDCU查询失败
                if result_cdcu == '未在车辆管理平台登记,请联系管理员':
                    # CDCU查不到
                    vmp_get_result['VIN数据维护状态'] = f'{by}为{value}的CDCU没有在VMP维护过！,无法通过CDCU信息查询VIN'
                    vmp_get_result['CDCU数据维护状态'] = f'{by}为{value}的CDCU没有在VMP维护过！'
                    vmp_get_result['CDCU绑定VIN状态'] = f'{by}为{value}的CDCU没有在VMP维护过！'

                else:
                    # 其他CDCU查询失败原因
                    vmp_get_result = f'后台状态异常:{result_cdcu}'
            else:
                # 用CDCU信息查VIN查不到，CDCU查询成功
                cdcu_data = result_cdcu
                vmp_get_result['VIN数据维护状态'] = f'{by}为{value}的CDCU在VMP没有和任何VIN绑定,无法通过CDCU信息查询VIN'
                vmp_get_result['CDCU数据维护状态'] = cdcu_data
                vmp_get_result['CDCU绑定VIN状态'] = f'{by}为{value}的CDCU在VMP没有和任何VIN绑定'
                vmp_get_result['CDCU数据维护状态']['updateTime'] = vmp_get_result['CDCU数据维护状态']['recordList'][0]['updateTime']
                del vmp_get_result['CDCU数据维护状态']['recordList']


        elif result_vehicle == '未在车辆管理平台登记,请联系管理员' and by == 'vin':
            # 用VIN信息查VIN查不到
            vmp_get_result['VIN数据维护状态'] = f'{by}为{value}的车辆没有在VMP维护过！'
            vmp_get_result['CDCU数据维护状态'] = f'{by}为{value}的车辆没有在VMP维护过！,无法通过VIN信息查询CDCU'
            vmp_get_result['CDCU绑定VIN状态'] = f'{by}为{value}的车辆没有在VMP维护过！'

        else:
            # VIN查询失败但反馈不是查不到
            vmp_get_result = f'后台状态异常:{result_vehicle}'
    else:
        # VIN能查到
        if by == 'cduid' or by == 'iccid':
            # 用cduid和iccid查的VIN，说明CDCU肯定存在，但是有可能因为网络问题查不到
            status_cdcu, result_cdcu = query_cdcu_info(by, value, cookies)
            if status_cdcu:
                # 后台正常能查到cdcu
                cdcu_data = result_cdcu
                vehicle_data = result_vehicle
                vin = result_vehicle['vin']
                vmp_get_result['VIN数据维护状态'] = vehicle_data
                vmp_get_result['CDCU数据维护状态'] = cdcu_data
                vmp_get_result['CDCU绑定VIN状态'] = f'VIN为{vin}的车辆绑定了{by}为{value}的CDCU'
                vmp_get_result['CDCU数据维护状态']['updateTime'] = vmp_get_result['CDCU数据维护状态']['recordList'][0]['updateTime']
                del vmp_get_result['CDCU数据维护状态']['recordList']
                del vmp_get_result['VIN数据维护状态']['maintainData']
            else:
                # 后台异常查不到cdcu
                vmp_get_result = f'后台状态异常:{result_vehicle}'
        elif by == 'vin':
            # 用vin查vin
            vehicle_data = result_vehicle
            vin = vehicle_data['vin']
            cduid = vehicle_data['cduId']
            iccid = result_vehicle['iccid']
            status_cdcu, result_cdcu = query_cdcu_info('cduid', cduid, cookies)
            if status_cdcu:
                cdcu_data = result_cdcu
                vmp_get_result['VIN数据维护状态'] = vehicle_data
                vmp_get_result['CDCU数据维护状态'] = cdcu_data
                vmp_get_result['CDCU绑定VIN状态'] = f'VIN为{vin}的车辆绑定了cduid为{cduid}的CDCU'
                vmp_get_result['CDCU数据维护状态']['updateTime'] = vmp_get_result['CDCU数据维护状态']['recordList'][0]['updateTime']
                del vmp_get_result['CDCU数据维护状态']['recordList']
                del vmp_get_result['VIN数据维护状态']['maintainData']

    return vmp_get_result


def set_vmp_data(vehicle_data_dict, cookies):
    cduid = vehicle_data_dict['HU Fazit ID']
    iccid = vehicle_data_dict['OCU ICCID']
    vin = vehicle_data_dict['车辆VIN码']
    add_cdu_url = 'https://vmp-portal.uat.cn-svw.volkswagen-cea.com/api/cdu/add'
    add_cdu_response = request_to_vmp(
        add_cdu_url,
        cookies,
        'POST',
        payload={
            'cduId': cduid,
            'iccid': iccid
        }
    )
    add_vehicle_url = 'https://vmp-portal.uat.cn-svw.volkswagen-cea.com/api/vehicle/add'
    add_vehicle_response = request_to_vmp(
        add_vehicle_url,
        cookies,
        'POST',
        payload={
            'vin': vin,
            'cduId': cduid,
            'iccid': iccid,
            'vehicleTypeCode': 'EK2',
            'vehicleMaterielId': '',
            'proclamationCode': '',
            'actColorCode': ''
        }
    )
    result = {
        'CDCU维护结果':add_cdu_response,
        '车辆维护结果': add_vehicle_response
    }
    print(result)
    return result

#
# cookies = web_driver_get_vmp_cookies()
# set_vmp_data =set_vmp_data(
#     'LSVUBAEK9S2010090',
#     'VWCEA0010019919000000105',
#     '89860325322005401721',
#     cookies
# )

# vmp_data_status = get_vmp_data_status('iccid', '89860345678919991126', cookies)
# vmp_data_status = json.dumps(vmp_data_status, indent=4, ensure_ascii=False)
# print(vmp_data_status)