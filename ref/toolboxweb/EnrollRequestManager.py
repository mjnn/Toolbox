import numpy as np
import requests
import json
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning
import pandas as pd
import shutil
import os
import io
from werkzeug.datastructures import FileStorage
from io import BytesIO
import re
from vehicle_project_rule import *
from credential_helper import get_account_password
from legacy_paths import ensure_temporary_dir, static_path

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

valid_prnr = [
    "~28AR~27T3",
    "~28DJ~1RUF~2NZ4~3",
    "~28DK~27UY~2EL8~28A5~2JH1~2QK4",
    "~28DK~27UY~2EL8~28A5~2JH1~2QK5~22V8",
    "~28YZ~27Q4~2EL7",
    "~28AS~2KS3~29DD",
    "~28DC~24N3~29DD~28A5",
    "~2I8Z~2IV3",
    "~2I8Z~2EL5",
    "~2ER6~2KS3~2IU3",
    "~PB0~KS1~U5N~U8B~U4M",
    "~2ED6~2JH1",
    "~200X~28DL~2EL6~2KS1"
]


class SPTool:
    def __init__(self):
        url = 'https://mosop-uat.csvw.com/dashboard-api/acct-node-api/login'
        username, password = get_account_password('uat_mos_portal')
        payload = {"username": username, "password": password}
        response = requests.post(url, json=payload, verify=False)
        response_dict = json.loads(response.text)
        if response_dict is not None:
            self.access_token = response_dict['data']['accessToken']

    @staticmethod
    def time_now_to_timestamp():
        timestamp = datetime.now().timestamp() * 1000
        return int(timestamp)

    # def vehicle_data_filter(self, file):
    #     try:
    #         file.seek(0)
    #     except Exception as e:
    #         return False, f'seek file error: {e}'
    #     try:
    #         if file.filename.endswith(('.xls', '.xlsx')):
    #             sheet_name_list = pd.ExcelFile(file).sheet_names
    #             sheet_name = sheet_name_list[1]
    #             df = pd.read_excel(file, sheet_name=sheet_name)
    #             vehicles_df = df.drop(columns=df.columns[1:3])
    #             print(vehicles_df.head(33))
    #             return True, file
    #         else:
    #             return False, f'file is not excel'
    #     except Exception as e:
    #         return False, f'some thing wrong: {e}'

    def vehicle_test_data_file_processor(self, brand, vehicle_test_data_dict):
        template = static_path("绑车信息模版(代码用).xlsx")
        tmp_dir = ensure_temporary_dir()
        tmp_xlsx = tmp_dir / "绑车信息模版(代码用).xlsx"
        df = pd.read_excel(template, sheet_name='实车台架申请 ')
        df['车辆信息1'] = np.nan
        for index_df, item_df in df['字段'].items():
            for item_dict in list(vehicle_test_data_dict.keys()):
                if item_df == item_dict:
                    df.loc[index_df, '车辆信息1'] = vehicle_test_data_dict[item_dict]
        shutil.copy(template, tmp_xlsx)
        with pd.ExcelWriter(tmp_xlsx, mode='a', engine='openpyxl', if_sheet_exists='replace') as writter:
            df.to_excel(writter, sheet_name='实车台架申请 ', index=False)
        with open(tmp_xlsx, 'rb') as file:
            code, response = self.import_vehicle_data(brand, file)
        # os.remove('./temporary/绑车信息模版(代码用).xlsx')
        return response

    def import_vehicle_data(self, brand, file):
        # status, result = self.vehicle_data_filter(file)
        # if not status:
        #     return 0, result
        # else:
        #     file = result
        try:
            file.seek(0)
        except Exception as e:
            return False, f'seek file error: {e}'
        if isinstance(file, FileStorage):
            filename = file.filename
            content_type = file.content_type
        elif isinstance(file, io.BufferedReader):
            filename = file.name
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            filename = ''
            content_type = ''
        try:
            url = f"https://mosop-uat.csvw.com/dashboard-api/vesp-gvs-maintainer/api/v1?brand={brand}"
            payload = {
                'file': (
                    filename,
                    file,
                    content_type
                    )
            }
            headers = {
                'token': self.access_token
            }
            response = requests.post(url, files=payload, verify=False, headers=headers)
            print('绑车响应：', response)
            response_dict = json.loads(response.text)
            response = response_dict['data']
            return 1, response
        except Exception as e:
            print(e)
            return 2, e

    def unbind_puser(self, vin, brand):
        try:
            app_user_id = self.get_puser_info(vin, brand)['userId']
            user_account = self.get_puser_info(vin, brand)['mobile']
            url = f'https://mosop-uat.csvw.com/dashboard-api/mos-admin-core/mos-admin-core/specialv/forSCO/unbindVehicle/{app_user_id}/{vin}?operMan=18186&brand={brand}'
            payload = {
                'brand': brand,
            }
            headers = {
                'token': self.access_token
            }
            response = requests.post(url, json=payload, verify=False, headers=headers)
            response_dict = json.loads(response.text)
            if response_dict['description'] != 'SUCCESS':
                return 2, '解绑失败，请联系Enrollment操作！'
            else:
                return 1, f'账户：{user_account}和车：{vin}的人车关系解绑成功！'
        except KeyError as e:
            return 0, '该VIN没有绑定主账号，请检查！'

    def bind_puser(self, account, vin, brand):
        url = f'https://mosop-uat.csvw.com/dashboard-api/mos-admin-core/mos-admin-core/' \
              f'specialv/forUser/getIdInfo?portalUserId=65a09989ee11fc0031cf6b75&phone={account}&brand={brand}'
        headers = {
            'token': self.access_token,
            'host': 'mosop-uat.csvw.com'
        }
        response = requests.get(url, verify=False, headers=headers)
        response_dict = json.loads(response.text)
        try:
            if response_dict == {"code": "000000", "description": "SUCCESS"}:
                code = '310102199512151245'
                name = '测试员'
                validtime = '2020.01.01-2040.01.01'
            else:
                id_info = response_dict['data']
                if id_info == {}:
                    code = '310102199512151245'
                    name = '测试员'
                    validtime = '2020.01.01-2040.01.01'
                else:
                    code = id_info['code']
                    name = id_info['name']
                    validtime = id_info['validtime']

            id_info = '{\"code\":\"%s\",\"name\":\"%s\",\"validtime\":\"%s\"}' % (code, name, validtime)

            url = f'https://mosop-uat.csvw.com/dashboard-api/mos-admin-core/' \
                  f'mos-admin-core/specialv/forUser/bindVehicle?operMan=18186&brand={brand}'

            payload = {
                'startTime': f'{datetime.now().date()} 00:00:00',
                'endTime': f'2029-12-31 23:59:59',
                'idInfo': id_info,
                'specialFlag': 2,
                'vehicleApplyPhase': 1,
                'vehicleUse': 1,
                'vin': vin,
                'applySector': 'ECC-1',
                'phoneNo': account,
                'portalUserId': "65a09989ee11fc0031cf6b75",
                'brand': brand
            }
            payload = json.dumps(payload, indent=4, ensure_ascii=False)
            headers = {
                'token': self.access_token,
                'host': 'mosop-uat.csvw.com',
                'Content-Type': 'application/json;charset=UTF-8'
            }
            response = requests.post(url, data=payload, verify=False, headers=headers)
            response_dict = json.loads(response.text)
            if response_dict['description'] == 'SUCCESS':
                return 1, f'账户：{account}和车：{vin}的人车关系绑定成功！'
            else:
                return 2, f'账户：{account}和车：{vin}的人车关系绑定失败：{response_dict["description"]}'
        except KeyError:
            return 0, f'账户：{account}和车：{vin}的人车关系绑定失败：{response_dict["description"]}'

    def change_hu(self, vin, brand, sn):
        url = f'https://mosop-uat.csvw.com/dashboard-api/mos-gvs-core-vehicle/admin/vesp-gvs-vehicle/api/v2/vehicles/{vin}/devices?brand={brand}'
        payload = {
            "sn": sn,
            "imei": "",
            "firmwareVersion": "",
            "deviceType": "headunit",
            "manufacturer": "",
            "manufactureTime": "",
            "createBy": "18186",
            "createTime": f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            "vin": vin,
            "softwareVersion":"",
            "brand": brand
        }
        headers = {
            'token': self.access_token,
            'host': 'mosop-uat.csvw.com'
        }
        response = requests.post(url, json=payload, verify=False, headers=headers)
        response_dict = json.loads(response.text)
        return response_dict['description']

    def get_vehicle_info(self, vin, brand):
        url = 'https://mosop-uat.csvw.com/dashboard-api/mos-gvs-core-vehicle/admin/vesp-gvs-vehicle/api/v2/vehicles'
        payload = {
            'specification.vin': vin,
            'desensitized': 'false',
            'paged': 'false',
            'specification.searchMore': 'tags,devices',
            'brand': brand
        }
        headers = {
            'token': self.access_token,
            'host': 'mosop-uat.csvw.com',
            'accept': 'application/json, text/plain, */*'
        }
        response = requests.get(url, params=payload, verify=False, headers=headers)
        response_dict = json.loads(response.text)
        # if vehicle_info_dict = response_dict['data']['records'] == []:
        #
        vehicle_info_dict = {}
        if response_dict['data']['records']:
            vehicle_info_dict = response_dict['data']['records'][0]
            for key in list(vehicle_info_dict.keys()):
                if key not in vehicle_info_dict:
                    vehicle_info_dict[key] = None
                else:
                    continue
            status, vehicle_info_dict['prnr'], vehicle_info_dict['huType'], vehicle_info_dict['ocuType'] = self.get_prnr(vin)
            if status:
                return status, vehicle_info_dict
            else:
                return status, vehicle_info_dict['prnr']
        else:
            return False, f'UAT后台未找到{vin}!'

    def get_sim_info(self, vin, brand):
        url = f'https://mosop-uat.csvw.com/dashboard-api/mos-gvs-core-vehicle/admin/vesp-gvs-vehicle/api/v2/vehicles/{vin}/devices/ocus/sims'
        payload = {
            'vin': vin,
            'brand': brand
        }
        headers = {
            'token': self.access_token,
            'host': 'mosop-uat.csvw.com'
        }
        response = requests.get(url, params=payload, verify=False, headers=headers)
        response_dict = json.loads(response.text)
        sim_info_dict = {}
        try:
            sim_info_dict = response_dict['data'][0]
        except KeyError as e:
            if e == 'data':
                pass
        for key in ['iccid', 'msisdn', 'imei', 'imsi']:
            if key not in sim_info_dict['vehicleSim']:
                sim_info_dict['vehicleSim'][key] = None
            else:
                continue

        return sim_info_dict

    def get_puser_info(self, vin, brand):
        url = f'https://mosop-uat.csvw.com/dashboard-api/mos-tcrm-core-user/mos-tcrm-core-user/api/v1/admin/info/{vin}'
        payload = {
            'desensitized': 'false',
            'brand': brand
        }
        headers = {
            'token': self.access_token,
            'host': 'mosop-uat.csvw.com'
        }
        response = requests.get(url, params=payload, verify=False, headers=headers)
        response_dict = json.loads(response.text)
        puser_info_dict = {}
        try:
            if response_dict['data'] != []:
                for user_info_dict in response_dict['data']:
                    if user_info_dict['role'] == 'PRIMARY_USER':
                        puser_info_dict = user_info_dict
                    else:
                        pass
            else:
                puser_info_dict = {'mobile': '没有绑定主用户'}
        except KeyError as e:
            if e == 'data':
                pass
        return puser_info_dict

    def get_enrollment_info(self, vin, brand):
        url = f'https://mosop-uat.csvw.com/dashboard-api/cesp-bso-ves/mos-bso-core-ves/api/v4/admin/binding-vehicles/search'
        payload = {
            'desensitized': 'true',
            'pageIndex': 1,
            'pageSize': 10,
            'vin': vin,
            'brand': brand
        }
        headers = {
            'token': self.access_token,
            'host': 'mosop-uat.csvw.com'
        }
        response = requests.get(url, params=payload, verify=False, headers=headers)
        response_dict = json.loads(response.text)
        try:
            enrollment_id = response_dict['data']['pageData'][0]['enrollmentId']
            activation_status = response_dict['data']['pageData'][0]['activationStatus']
        except IndexError as e:
            return '暂无enrollment记录'

        url = f'https://mosop-uat.csvw.com/dashboard-api/cesp-bso-ves/mos-bso-core-ves/api/v4/admin/' \
              f'enrollments/{enrollment_id}/actions/queryBindEvent'
        payload = {
            'id': enrollment_id,
            'desensitized': 'true',
            'brand': brand
        }
        headers = {
            'token': self.access_token,
            'host': 'mosop-uat.csvw.com'
        }
        response = requests.get(url, params=payload, verify=False, headers=headers)
        enrollment_event_list = json.loads(response.text)['data']['enrEventList']
        enrollment_event_dict = {
            'now_status':activation_status,
            'event_history':{}
        }
        for enrollment_raw_event in enrollment_event_list:
            if enrollment_raw_event['targetStatus'] != enrollment_raw_event['sourceStatus']:
                targetStatus = enrollment_raw_event['targetStatus']
                enrollment_event_dict['event_history'][targetStatus] = {}
                enrollment_event_dict['event_history'][targetStatus]['sourceStatus'] = enrollment_raw_event['sourceStatus']
                enrollment_event_dict['event_history'][targetStatus]['createTime'] = enrollment_raw_event['createTime']
                enrollment_event_dict['event_history'][targetStatus]['eventResult'] = enrollment_raw_event['eventResult']
        return enrollment_event_dict

    def get_prnr(self, vin):
        url = f'http://vesp-gvs-vehicle.uatapps.aliocp.csvw.com/api/v3/vehicles/{vin}/feature?isPrnr=true'
        response = requests.get(url, verify=False)
        try:
            prnr = json.loads(response.text)['data']['prnr']
            hu_type = json.loads(response.text)['data']['huType']
            ocu_type = json.loads(response.text)['data']['setting']
            return True, prnr, hu_type, ocu_type
        except KeyError as e:
            print('获取PR号失败，因为:', json.loads(response.text)['description'])
            return False, json.loads(response.text)['description'], json.loads(response.text)['description'], json.loads(response.text)['description']

    def get_service_list(self, vin, brand):
        url = f'https://mosop-uat.csvw.com/dashboard-api/mos-gvs-core-vehicle/admin/vesp-gvs-vehicle/api/v2/vehicles/{vin}/capabilities?vin={vin}&brand={brand}'
        headers = {
            'token': self.access_token,
            'host': 'mosop-uat.csvw.com'
        }
        response = requests.get(url, verify=False,  headers=headers)
        response = json.loads(response.text)
        try:
            service_list = response['data']
            return 1, service_list
        except KeyError:
            return 0, response['description']

    def get_sp_details(self, vin, brand):
        try:
            status, vehicle_info = self.get_vehicle_info(vin, brand)
            if not status:
                sp_details = '车辆未找到！'
                return sp_details
            if vehicle_info is not None:
                sp_details_dict = {
                    'vehicle_info': vehicle_info,
                    'sim_info': self.get_sim_info(vin, brand),
                    'puser_info': self.get_puser_info(vin, brand),
                    'enrollment_info': self.get_enrollment_info(vin, brand),
                    # 'service_list': self.get_service_list(vin, brand)
                }
                # print(json.dumps(sp_details_dict, indent=4, ensure_ascii=False))
                vehicle_info_dict = {
                    'VIN': sp_details_dict['vehicle_info']['vin'],
                    '品牌': sp_details_dict['vehicle_info']['vehicleModel']['vehicleSeries']['vehicleBrand']['name'],
                    '发动机号': sp_details_dict['vehicle_info']['engineNumber'],
                    '车机Fazit ID (SN)': sp_details_dict['vehicle_info']['deviceSn'],
                    '燃油类型': sp_details_dict['vehicle_info']['vehicleModel']['vehicleModelType']['code'],
                    'MOS项目': sp_details_dict['vehicle_info']['vehicleModel']['platformVersion']['code'],
                    # 'sop': sp_details_dict['vehicle_info']['vehicleModel']['sop']['code'],
                    '产线平台': sp_details_dict['vehicle_info']['vehicleModel']['productLine']['code'],
                    'prnr': sp_details_dict['vehicle_info']['prnr'],
                    '车机类型': sp_details_dict['vehicle_info']['huType'],
                    'OCU类型': sp_details_dict['vehicle_info']['ocuType'],
                    'OCU Fazit ID (SN)': sp_details_dict['vehicle_info']['devices'][0]['sn']
                }
                sim_info_dict = {
                    'ICCID': sp_details_dict['sim_info']['vehicleSim']['iccid'],
                    'MSISDN': sp_details_dict['sim_info']['vehicleSim']['msisdn'],
                    'IMEI': sp_details_dict['sim_info']['vehicleSim']['imei'],
                    'IMSI': sp_details_dict['sim_info']['vehicleSim']['imsi'],
                    '运营商': sp_details_dict['sim_info']['carrier']['name']
                }
                if sp_details_dict['enrollment_info'] != '暂无enrollment记录':
                    enrollment_now_status = sp_details_dict['enrollment_info']['now_status']
                else:
                    enrollment_now_status = '暂无enrollment记录'
                translate_dict = {
                    'ABOLISHED': '已解绑，下一步为实名解除',
                    'BOUND': '已绑定，下一步为DP主账户绑定',
                    'CANCELED': '实名已解除，绑车状态不再更新',
                    'REALNAME_SUCCEED': '实名认证成功，如果还未车机登录请前往车机登录主账户；如果已经登录，绑车状态不再更新',
                    'VEHICLE_CERTIFIED': '首次车机登录成功，如果还未实名认证，请在确保SIM卡完成注册之后前往MOS APP进行实名认证',
                    'REALNAME_VERIFYING': '实名认证中',
                    'DP_SYNCED': 'DP主账户绑定成功，请前往车机登录主账户并在确保SIM卡完成注册之后前往MOS APP进行实名认证',
                    'SERVICE_ACTIVATING': 'DP主账户绑定中，请确保完成PIN（安全码）设置并在MBB WebCenter完成车辆数据的维护',
                }
                for key, value in translate_dict.items():
                    if enrollment_now_status == key:
                        enrollment_now_status = value
                puser_info_dict = {
                    '主账户手机号': sp_details_dict['puser_info']['mobile'],
                    '当前主账户绑定状态': enrollment_now_status
                }

                sp_details = {
                    '车辆MOS相关信息': vehicle_info_dict,
                    'SIM卡信息': sim_info_dict,
                    '主账户': puser_info_dict
                }
                # sp_details = {
                #     'basic': sp_details,
                #     'detail': sp_details_dict
                # }
            else:
                print('\033[31m车辆未找到！\033[0m')
                sp_details = '车辆未找到！'
        except KeyError as e:
            sp_details =  f'后台错误无{e}字段'
            print(f'\033[31m车辆后台信息{e}不全，请重新填写绑车信息表\033[0m')
        return sp_details


