import json
from Zone_token_getter import *
from TimeStampProcessor import *
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def create_vin(vin, project, zone_token, cookies):
    if project == 'MOS_F_SUV':
        url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/vehicle/createVehicle'
        payload = {
            "vin": vin,
            "brandName": "大众",
            "modelProject": "SVW-M1",
            "modelYear": "2025",
            "mesModelName": "冬季选装包4,夏季选装包8",
            "modelBaseId": "235",
            "modelId": "1000000151",
            "productDate": datetime.now().strftime('%Y-%m-%d'),
            "vehicleType": 2,
            "saleStatus": 0,
            "saleModelName": "SVWm1",
            "color": "",
            "tagIdList": [],
            "activateTime": None,
            "invoiceDate": None,
            "manufactureDate": None
        }
        vehicle_data_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
        result = json.loads(vehicle_data_response.text)['message']

    elif project == 'MOS_A_NB_Low':
        url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/vehicle/createVehicle'
        payload = {
            "vin": vin,
            "brandName": "大众",
            "modelProject": "SVW-M0",
            "modelYear": "2025",
            "mesModelName": "夏季选装包22,冬季选装包4-A车-L",
            "modelBaseId": "236",
            "modelId": "1000000150",
            "productDate": "2025-10-15",
            "vehicleType": 2,
            "saleStatus": 0,
            "saleModelName": "SVWm0-L",
            "color": "",
            "tagIdList": [],
            "activateTime": None,
            "invoiceDate": None,
            "manufactureDate": None
        }
        vehicle_data_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
        result = json.loads(vehicle_data_response.text)['message']

    elif project == 'MOS_A_NB_High':
        url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/vehicle/createVehicle'
        payload = {
            "vin": vin,
            "brandName": "大众",
            "modelProject": "SVW-M0",
            "modelYear": "2025",
            "mesModelName": "夏季选装包22,冬季选装包4,夏季选装包8-A车-H",
            "modelBaseId": "260",
            "modelId": "1000000190",
            "productDate": "2025-10-15",
            "vehicleType": 2,
            "saleStatus": 0,
            "saleModelName": "SVWm0-H",
            "color": "",
            "tagIdList": [],
            "activateTime": None,
            "invoiceDate": None,
            "manufactureDate": None
        }
        vehicle_data_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
        result = json.loads(vehicle_data_response.text)['message']

    else:
        result = '传入项目未知'

    return result


def create_zxd(zxd_sn, zone_token, cookies):
    url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/zxd1/createZxd1'
    payload = {
        "sn": zxd_sn,
        "partNumber": "3ER03586",
        "tagIdList": []
    }
    zxd_data_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
    result = json.loads(zxd_data_response.text)['message']
    return result


def create_iam(iam_sn, iam_iccid, iam_mdn, zone_token, cookies):
    url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/iam/createIam'
    payload = {
        "iccid": iam_iccid,
        "sn": iam_sn,
        "terminalModel": "i-BOX 3.65",
        "terminalCode": "7A09270003",
        "manufactureDate": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "simNumber": iam_mdn,
        "tagIdList": []
    }
    iam_data_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
    result = json.loads(iam_data_response.text)['message']
    return result


def bind_zxd(zxd_sn, vin, zone_token, cookies):
    get_id_result = get_id_by_value('zxd', zxd_sn, zone_token, cookies)
    status = get_id_result['success']
    result = get_id_result['data']
    if status:
        url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/zxd1/bindZxd1'
        payload = {
            "id": result,
            "vin": vin
        }
        zxd_bind_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
        result = json.loads(zxd_bind_response.text)['message']
    else:
        pass
    return result


def bind_iam(iam_sn, vin, zone_token, cookies):
    get_id_result = get_id_by_value('iam', iam_sn, zone_token, cookies)
    status = get_id_result['success']
    result = get_id_result['data']
    if status:
        url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/iam/bindingIam'
        payload = {
            "id": result,
            "vin": vin
        }
        zxd_bind_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
        result= json.loads(zxd_bind_response.text)['message']
    else:
        pass
    return result


def get_id_by_value(item, value, zone_token, cookies):
    decimal_random = generate_17_decimal_random()
    if item == 'zxd':
        url = f'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/zxd1/getZxd1?sn={value}&limit=10&page=1&__rid={str(decimal_random)}'
        response = get_request_to_zone_vehicleinfo(url, zone_token, cookies)
        response_dict = json.loads(response.text)
        http_code = response_dict['code']
        if http_code != 200:
            result = {
                'success': False,
                'data': f'请求接口异常：{response_dict}'
            }
        else:
            if not response_dict['data']['list']:
                result = {
                    'success': False,
                    'data': f'UAT AF DP主数据平台未找到{value}！'
                }
            else:
                zxd_id = response_dict['data']['list'][0]['id']
                result = {
                    'success': True,
                    'data': zxd_id
                }

    elif item == 'iam':
        url = f'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/iam/getIam?iamsn={value}&limit=10&page=1&__rid={str(decimal_random)}'
        response = get_request_to_zone_vehicleinfo(url, zone_token, cookies)
        response_dict = json.loads(response.text)
        http_code = response_dict['code']
        if http_code != 200:
            result = {
                'success': False,
                'data': f'请求接口异常：{response_dict}'
            }
        else:
            if not response_dict['data']['list']:
                result = {
                    'success': False,
                    'data': f'UAT AF DP主数据平台未找到{value}！'
                }
            else:
                zxd_id = response_dict['data']['list'][0]['id']
                result = {
                    'success': True,
                    'data': zxd_id
                }
    elif item == 'vin':
        url = f'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/vehicle/getVehicle?vin={value}&limit=10&page=1&__rid={str(decimal_random)}'
        response = get_request_to_zone_vehicleinfo(url, zone_token, cookies)
        response_dict = json.loads(response.text)
        http_code = response_dict['code']
        if http_code != 200:
            result = {
                'success': False,
                'data': f'请求接口异常：{response_dict}'
            }
        else:
            if not response_dict['data']['list']:
                result = {
                    'success': False,
                    'data': f'UAT AF DP主数据平台未找到{value}！'
                }
            else:
                vin_id = response_dict['data']['list'][0]['id']
                result = {
                    'success': True,
                    'data': vin_id
                }
    else:
        result = {
            'success': False,
            'data': f'传参错误:{item}'
        }
    return result


def uat_af_dp_data_read_vin(vin, zone_token, cookies):
    decimal_random = generate_17_decimal_random()
    url = f'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/vehicle/detail?vin={vin}&__rid={str(decimal_random)}'
    response = get_request_to_zone_vehicleinfo(url, zone_token, cookies)
    response_dict = json.loads(response.text)
    http_code = response_dict['code']
    if http_code != 200:
        result = {
            'success': False,
            'data': f'请求接口异常：{response_dict}'
        }
    else:
        if not response_dict['data']:
            result = {
                'success': False,
                'data': f'UAT AF DP主数据平台未找到{vin}！'
            }
        else:
            dp_data_source = response_dict['data']
            dp_data = {'vin': dp_data_source['vin'], '已绑定件': dp_data_source['bindEcuTypeList'], '车型': dp_data_source['model']['vehicleModel']}
            for ecu in dp_data['已绑定件']:
                if ecu == 'IAM':
                    dp_data['IAM信息'] = dp_data_source['iam']
                elif ecu == 'ZXD':
                    dp_data['ZXD信息'] = dp_data_source['zxd']
            result = {
                'success': True,
                'data': dp_data
        }
    return result


def uat_af_dp_data_read(vin=None, zxdsn=None, iamsn=None, iccid=None):
    decimal_random = generate_17_decimal_random()
    zone_token, cookies = web_driver_get_zone_token_cookies()
    if vin:
        result = uat_af_dp_data_read_vin(vin, zone_token, cookies)
        return result
    elif zxdsn:
        url = f'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/zxd1/getZxd1?sn={zxdsn}&limit=10&page=1&__rid={str(decimal_random)}'
        response = get_request_to_zone_vehicleinfo(url, zone_token, cookies)
        response_dict = json.loads(response.text)
        http_code = response_dict['code']
        if http_code != 200:
            result = {
                'success': False,
                'data': f'请求接口异常：{response_dict}'
            }
        else:
            if not response_dict['data']['list']:
                result = {
                    'success': False,
                    'data': f'UAT AF DP主数据平台未找到{zxdsn}！'
                }
            else:
                vin = response_dict['data']['list'][0]['vin']
                if vin:
                    result = uat_af_dp_data_read_vin(vin, zone_token, cookies)
                else:
                    result = {
                        'success': False,
                        'data': f'该zxd{zxdsn}没有绑定任何vin!'
                    }
        return result
    elif iamsn:
        url = f'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/iam/getIam?iamsn={iamsn}&limit=10&page=1&__rid={str(decimal_random)}'
        response = get_request_to_zone_vehicleinfo(url, zone_token, cookies)
        response_dict = json.loads(response.text)
        http_code = response_dict['code']
        if http_code != 200:
            result = {
                'success': False,
                'data': f'请求接口异常：{response_dict}'
            }
        else:
            if not response_dict['data']['list']:
                result = {
                    'success': False,
                    'data': f'UAT AF DP主数据平台未找到{iamsn}！'
                }
            else:
                vin = response_dict['data']['list'][0]['vin']
                if vin:
                    result = uat_af_dp_data_read_vin(vin, zone_token, cookies)
                else:
                    result = {
                        'success': False,
                        'data': f'该zxd{iamsn}没有绑定任何vin!'
                    }
        return result
    elif iccid:
        url = f'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/iam/getIam?iccid={iccid}&limit=10&page=1&__rid={str(decimal_random)}'
        response = get_request_to_zone_vehicleinfo(url, zone_token, cookies)
        response_dict = json.loads(response.text)
        http_code = response_dict['code']
        if http_code != 200:
            result = {
                'success': False,
                'data': f'请求接口异常：{response_dict}'
            }
        else:
            if not response_dict['data']:
                result = {
                    'success': False,
                    'data': f'UAT AF DP主数据平台未找到{iccid}！'
                }
            else:
                vin = response_dict['data']['list'][0]['vin']
                if vin:
                    result = uat_af_dp_data_read_vin(vin, zone_token, cookies)
                else:
                    result = {
                        'success': False,
                        'data': f'该zxd{iccid}没有绑定任何vin!'
                    }
        return result


def delete_item_by_value(item, value, zone_token, cookies):
    if item == 'zxd':
        get_zxd_result = get_id_by_value(item, value, zone_token, cookies)
        status = get_zxd_result['success']
        result = get_zxd_result['data']
        if status:
            zxd_id = result
        else:
            return False, {'error': f'删除ecu失败：{result}'}

        url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/zxd1/deleteZxd1'
        payload = {
            "id": zxd_id
        }

        delete_zxd_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
        delete_result = json.loads(delete_zxd_response.text)
        http_code = delete_result['code']
        result = delete_result['message']
        if http_code == 200:
            return True, {'ZXD删除结果': result}
        else:
            return False, {'error': result}

    elif item == 'iam':
        get_iam_result = get_id_by_value(item, value, zone_token, cookies)
        status = get_iam_result['success']
        result = get_iam_result['data']
        if status:
            iam_id = result
        else:
            return False, {'error': f'删除ecu失败：{result}'}

        url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/iam/deleteIam'
        payload = {
            "id": iam_id
        }

        delete_iam_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
        delete_result = json.loads(delete_iam_response.text)
        http_code = delete_result['code']
        result = delete_result['message']
        if http_code == 200:
            return True, {'IAM删除结果': result}
        else:
            return False, {'error': result}

    elif item == 'vin':
        get_vin_result = get_id_by_value(item, value, zone_token, cookies)
        status = get_vin_result['success']
        result = get_vin_result['data']
        if status:
            vin_id = result
        else:
            return False, {'error': f'删除车辆失败：{result}'}

        url = 'https://zapi-zone.mosop-uat.csvw.com/ba/cvb/vehicle/deleteVehicle'
        payload = {
            "id": vin_id
        }

        delete_vin_response = post_request_to_zone_vehicleinfo(url, payload, zone_token, cookies)
        delete_result = json.loads(delete_vin_response.text)
        http_code = delete_result['code']
        result = delete_result['message']
        if http_code == 200:
            return True, {'VIN删除结果': result}
        else:
            return False, {'error': result}


def uat_af_dp_config_set(input_json):
    zone_token, cookies = web_driver_get_zone_token_cookies()
    vehicle_data_dict = input_json
    project = vehicle_data_dict['所属项目']
    zxd_sn = vehicle_data_dict['HU Fazit ID']
    iam_iccid = vehicle_data_dict['OCU ICCID']
    iam_mdn = vehicle_data_dict['MSISDN']
    iam_sn = vehicle_data_dict['OCU Fazit ID']
    vin = vehicle_data_dict['车辆VIN码']
    create_vin_result = create_vin(vin, project, zone_token, cookies)
    if create_vin_result == '传入项目未知':
        return False, {'error': '所选项目不是AF车项目！'}
    else:
        create_zxd_result = create_zxd(zxd_sn, zone_token, cookies)
        bind_zxd_result = bind_zxd(zxd_sn, vin, zone_token, cookies)
        create_iam_result = create_iam(iam_sn, iam_iccid, iam_mdn, zone_token, cookies)
        bind_iam_result = bind_iam(iam_sn, vin, zone_token, cookies)
        result = {}
        result['车辆数据维护状态'] = create_vin_result
        result['ZXD数据维护状态'] = create_zxd_result
        result['ZXD绑定维护状态'] = bind_zxd_result
        result['IAM数据维护状态'] = create_iam_result
        result['IAM绑定维护状态'] = bind_iam_result
        return True, result


def af_swap(vin, new_zxd_sn=None, new_iam_sn=None, iam_iccid=None, iam_mdn=None):
    old_zxd_sn = None
    old_iam_sn = None
    swap_result = {}
    zone_token, cookies = web_driver_get_zone_token_cookies()

    # 拉原车数据
    vehicle_data = uat_af_dp_data_read_vin(vin, zone_token, cookies)
    status = vehicle_data['success']
    result = vehicle_data['data']
    if status:
        try:
            old_zxd_sn = result['ZXD信息']['sn']
            old_iam_sn = result['IAM信息']['iamsn']
            old_iccid = result['IAM信息']['iccid']
            old_mdn = result['IAM信息']['msisdn']
        except KeyError as e:
            if e.__str__() == 'ZXD信息':
                old_zxd_sn = None
            elif e.__str__() == 'IAM信息':
                old_iam_sn = None
                old_iccid = None
                old_mdn = None
    else:
        return False, f'拉取旧件信息失败{result}'

    if new_zxd_sn is not None:
        if old_zxd_sn is not None:
            if old_zxd_sn != new_zxd_sn:
                zxd_delete_status, zxd_delete_result = delete_item_by_value('zxd', old_zxd_sn, zone_token, cookies)
                if zxd_delete_status:
                    create_zxd_result = create_zxd(new_zxd_sn, zone_token, cookies)
                    bind_zxd_result = bind_zxd(new_zxd_sn, vin, zone_token, cookies)
                    swap_result['ZXD旧件数据删除状态'] = zxd_delete_result
                    swap_result['ZXD新件数据维护状态'] = create_zxd_result
                    swap_result['ZXD新件绑定维护状态'] = bind_zxd_result
                else:
                    return False, f'删除旧件失败{zxd_delete_result}'
            else:
                return False, f'新旧件SN号不能一致，当前旧件SN：{old_zxd_sn}'
        else:
            return False, f'{vin}该VIN没有绑定任何ZXD！'

    elif new_iam_sn is not None and iam_iccid is not None and iam_mdn is not None:
        if old_iam_sn is not None and old_iccid is not None and old_mdn is not None:

            if old_iam_sn != new_iam_sn and old_iccid!=iam_iccid and old_mdn!=iam_mdn:
                iam_delete_status, iam_delete_result = delete_item_by_value('iam', old_iam_sn, zone_token, cookies)
                if iam_delete_status:
                    create_iam_result = create_iam(new_iam_sn, iam_iccid, iam_mdn, zone_token, cookies)
                    bind_iam_result = bind_iam(new_iam_sn, vin, zone_token, cookies)
                    swap_result['IAM旧件数据删除状态'] = iam_delete_result
                    swap_result['IAM新件数据维护状态'] = create_iam_result
                    swap_result['IAM新件绑定维护状态'] = bind_iam_result
                else:
                    return False, f'删除旧件失败{iam_delete_result}'
            else:
                return False, f'新旧件信息不能一致，当前旧件信息：sn:{old_iam_sn}, iccid:{old_iccid}, msisdn:{old_mdn}'
        else:
            return False, f'{vin}该VIN没有绑定任何IAM！'

    else:
        return False, f'传入参数:\nZXD新件SN:{new_zxd_sn},IAM新件SN:{new_iam_sn},' \
               f'IAM新件ICCID:{iam_iccid},IAM新件MSISDN:{iam_mdn},信息不足以完成任何换件！'

    return True, json.dumps(swap_result, ensure_ascii=False, indent=4)

