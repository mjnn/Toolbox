import logging
import json
from datetime import datetime
import requests
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import warnings
from urllib3.exceptions import InsecureRequestWarning
from selenium.webdriver.edge.service import Service
import pandas as pd
import LiveTokenGetter


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)


def get_vehicle_info_request(token, vin, info_type):
    if info_type == 'VehicleBaseInfo':
        url = 'https://avc.csvw.com/avc-api/query/v1/vehicleInfo/queryVehicleBaseInfo'
    elif info_type == 'VehicleGuoDianInfo':
        url = 'https://avc.csvw.com/avc-api/query/v1/vehicleInfo/queryVehicleGuoDianInfo'
    elif info_type == 'VehicleBaugruppeInfo':
        url = 'https://avc.csvw.com/avc-api/query/v1/vehicleInfo/queryVehicleBaugruppeInfo'
    elif info_type == 'VehiclePrInfo':
        url = 'https://avc.csvw.com/avc-api/query/v1/vehicleInfo/queryVehiclePrInfo'
    else:
        return '查询信息类型不存在'
    body = {'vin': vin}
    headers = {
        'authorization': token,
        'content-type': 'application/json'
    }
    logging.debug('发送查询info_type请求')
    response = requests.post(url=url, json=body, headers=headers, verify=False)
    response = json.loads(response.text)
    try:
        vehicle_info_dict = response['result']
        if vehicle_info_dict == []:
            vehicle_info_dict = {'error': '未查询到任何信息！'}
    except KeyError as e:
        vehicle_info_dict = {'error': '未查询到任何信息！'}
    return vehicle_info_dict


def get_vehicle_info_from_avc(token, vin):
    logging.debug('获取AVC上的车辆信息')
    vehicle_base_info_dict = get_vehicle_info_request(token, vin, 'VehicleBaseInfo')
    if vehicle_base_info_dict != {'error': '未查询到任何信息！'}:
        vehicle_guodian_info_dict = get_vehicle_info_request(token, vin, 'VehicleGuoDianInfo')
        vehicle_baugruppe_info_dict = get_vehicle_info_request(token, vin, 'VehicleBaugruppeInfo')
        vehicle_pr_info_dict = get_vehicle_info_request(token, vin, 'VehiclePrInfo')
        vehicle_info = {
            'Basic info': vehicle_base_info_dict,
            'Check point info': vehicle_guodian_info_dict,
            'Barcode info': vehicle_baugruppe_info_dict,
            'PR list': vehicle_pr_info_dict
        }
        vehicle_info_json = json.dumps(vehicle_info, indent=4)
        logging.debug('导出AVC上的车辆信息')
        with open(f'./output/vehicle_info_{vin}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            f.write(vehicle_info_json)
            logging.debug('导出json')
        vehicle_base_df = pd.DataFrame(vehicle_base_info_dict, index=[0])
        checkpoint_status = []
        checkpoint_date = []
        checkpoint_time = []
        checkpoint_position = []
        for guodian in vehicle_guodian_info_dict:
            checkpoint_status.append(guodian['status'])
            checkpoint_date.append(guodian['mdatum'])
            checkpoint_time.append(guodian['mzeit'])
            checkpoint_position.append(guodian['fanlage'])
        vehicle_guodian_info = {'工位':checkpoint_position, '状态点':checkpoint_status, '日期':checkpoint_date, '时间':checkpoint_time}
        vehicle_guodian_df = pd.DataFrame(vehicle_guodian_info)
        baugruppenum = []
        baugruppesnrLong = []
        erfDatumZeit = []
        for baugruppe in vehicle_baugruppe_info_dict:
            baugruppenum.append(baugruppe['baugruppe'])
            baugruppesnrLong.append(baugruppe['baugruppesnrLong'])
            erfDatumZeit.append(baugruppe['erfDatumZeit'])
        baugruppe_info = {'条码号':baugruppenum, '条码内容':baugruppesnrLong, '条码录入时间':erfDatumZeit}
        baugruppe_df = pd.DataFrame(baugruppe_info)
        prnum = []
        prfam = []
        for pr in vehicle_pr_info_dict:
            prfam.append(pr['prFamily'])
            prnum.append(pr['prNum'])
        pr_info = {'PR簇': prfam, 'PR号': prnum}
        pr_df = pd.DataFrame(pr_info)

        with pd.ExcelWriter(f'output/AVC数据导出_{vin}.xlsx',engine='openpyxl') as writer:
            vehicle_base_df.to_excel(writer, sheet_name='基础信息', index=False)
            vehicle_guodian_df.to_excel(writer, sheet_name='过点记录', index=False)
            baugruppe_df.to_excel(writer, sheet_name='条码录入记录', index=False)
            pr_df.to_excel(writer, sheet_name='PR号', index=False)
            logging.debug('导出excel')
    else:
        logging.info(f'未在AVC系统查询到{vin}')


# logging.info('正在获取AVC Token')
# token = LiveTokenGetter.get_app_live_token('车辆数据服务中心(AVC)', account, pwd)['token']
# logging.info('获取并导出AVC上的车辆信息')
# for vin in vin_list:
#     logging.info(f'{vin}操作完成')
#     get_vehicle_info_from_avc(token, vin)
# input("所有导出数据均已保存到本程序同级目录output文件夹内，按任意键退出...")