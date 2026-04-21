import json
import requests
from VMP_Config import *
from flask import Flask, render_template, url_for, request, jsonify
from EnrollRequestManager import SPTool
import AVCGetter
import LiveTokenGetter
from cert_key_resolve import cert_key_parse
from vehicle_project_rule import *
from uat_af_dp_congif_set import *
from Live_iam_x509_signature import *
from iam_x509_signature import *
from AFC_SIMCard_Serach import *
from parse_csr_hex import *
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

app = Flask(__name__)


@app.route("/")
def index():
    base_url = request.url_root[:-1]
    return render_template("index.html")


@app.route("/json_formatter")
def json_formatter():
    return render_template('json-formatter.html')


@app.route("/jwt_decoder")
def jwt_decoder():
    return render_template('jwt_decode.html')


@app.route("/hex_to_ascii")
def hex_to_ascii():
    return render_template('hex-ascii-converter.html')


@app.route("/uat_sp_tool")
def uat_sp_tool():
    return render_template(
        'uat_sp_tool.html',
        bind_url=url_for('bind_person_car_api'),
        unbind_url=url_for('unbind_person_car_api'),
        replace_url=url_for('replace_hu_api'),
        query_vehicle_url=url_for('query_vehicle_data_api', vin='__VIN__'),
        query_service_url=url_for('query_service_list_api', vin='__VIN__'),
        upload_master_data_url=url_for('upload_master_data_api')
    )


@app.route('/uat_sp_tool/api/upload_master_data', methods=['POST'])
def upload_master_data_api():
    if 'file' not in request.files:
        return jsonify({'message': '请求中没有文件！'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': '没有选择任何文件！'}), 400
    if file:
        spt = SPTool()
        code, result = spt.import_vehicle_data('vw', file)
        if code == 1:
            try:
                error_code = result['errorCode']
                return jsonify({"success": False, "message": result['message']}), 404
            except Exception as e:
                return jsonify({"success": True, "message": result})

        elif code == 2:
            return jsonify({"success": False, "message": result}), 500


@app.route('/uat_sp_tool/api/bind_person_car', methods=['POST'])
def bind_person_car_api():
    data = request.json
    vin = data.get('vin')
    phone = data.get('phone')
    if not vin or not phone:
        return jsonify({"success": False, "message": "VIN和手机号不能为空"}), 400
    spt = SPTool()
    code, result = spt.bind_puser(phone, vin, 'vw')
    if code == 1:
        return jsonify({"success": True, "message": result})
    elif code == 0:
        return jsonify({"success": False, "message": result}), 404
    elif code == 2:
        return jsonify({"success": False, "message": result}), 500


@app.route('/uat_sp_tool/api/unbind_person_car', methods=['POST'])
def unbind_person_car_api():
    data = request.json
    vin = data.get('vin')
    if not vin:
        return jsonify({"success": False, "message": "VIN不能为空"}), 400
    spt = SPTool()
    code, result = spt.unbind_puser(vin, 'vw')
    if code == 1:
        return jsonify({"success": True, "message": result})
    elif code == 0:
        return jsonify({"success": False, "message": result}), 404
    elif code == 2:
        return jsonify({"success": False, "message": result}), 500


@app.route('/uat_sp_tool/api/replace_hu_api', methods=['POST'])
def replace_hu_api():
    data = request.json
    vin = data.get('vin')
    new_sn = data.get('newSn')
    if not vin or not new_sn:
        return jsonify({"success": False, "message": "VIN和新车机SN号不能为空"}), 400
    spt = SPTool()
    result = spt.change_hu(vin, 'vw', new_sn)
    if result == '该设备已安装':
        return jsonify({"success": False, "message": '新件已绑定其他车辆！'}), 201
    return jsonify({"success": True, "message": result})


@app.route('/uat_sp_tool/api/vehicle_data/<vin>', methods=['GET'])
def query_vehicle_data_api(vin):
    spt = SPTool()
    data = spt.get_sp_details(vin, 'vw')
    if data != '车辆未找到！':
        return jsonify(data)
    elif '后台错误' in data:
        return jsonify({"message": data}), 500
    else:
        return jsonify({"message": f"VIN: {vin} 的车辆数据不存在"}), 404


@app.route('/uat_sp_tool/api/service_list/<vin>', methods=['GET'])
def query_service_list_api(vin):
    spt = SPTool()
    code, result = spt.get_service_list(vin, 'vw')
    if code == 1:
        return jsonify({"success": True, "message": result})
    elif code == 0:
        return jsonify({"success": False, "message": result}), 500


@app.route('/barcode', methods=['GET'])
def barcode():
    return render_template('barcode_query.html')


@app.route('/AVC/api/barcode', methods=['POST'])
def query_product_line_barcode():
    data = request.json
    vins = data.get('vins')
    token = LiveTokenGetter.get_app_live_token('车辆数据服务中心(AVC)')['token']
    vehicle_barcode_infos = []
    for vin in vins:
        vehicle_baugruppe_info_dict = AVCGetter.get_vehicle_info_request(token, vin, 'VehicleBaugruppeInfo')
        if vehicle_baugruppe_info_dict != {'error': '未查询到任何信息！'}:
            baugruppenum = []
            baugruppesnrLong = []
            erfDatumZeit = []
            for baugruppe in vehicle_baugruppe_info_dict:
                baugruppenum.append(baugruppe['baugruppe'])
                baugruppesnrLong.append(baugruppe['baugruppesnrLong'])
                erfDatumZeit.append(baugruppe['erfDatumZeit'])
            baugruppe_info = {'条码号': baugruppenum, '条码内容': baugruppesnrLong, '条码录入时间': erfDatumZeit}
            vehicle_barcode_infos.append(baugruppe_info)
        else:
            vehicle_barcode_infos.append(vehicle_baugruppe_info_dict)
        return jsonify(vehicle_barcode_infos)


@app.route('/prnum', methods=['GET'])
def prnum():
    return render_template('prnum_query.html')


@app.route('/AVC/api/prnum', methods=['POST'])
def query_product_line_prnum():
    data = request.json
    vins = data.get('vins')
    token = LiveTokenGetter.get_app_live_token('车辆数据服务中心(AVC)')['token']
    vehicle_pr_infos = []
    for vin in vins:
        vehicle_pr_info_dict = AVCGetter.get_vehicle_info_request(token, vin, 'VehiclePrInfo')
        if vehicle_pr_info_dict != {'error': '未查询到任何信息！'}:
            prnum = []
            prfam = []
            for pr in vehicle_pr_info_dict:
                prfam.append(pr['prFamily'])
                prnum.append(pr['prNum'])
            pr_info = {'PR簇': prfam, 'PR号': prnum}
            vehicle_pr_infos.append(pr_info)
        else:
            vehicle_pr_infos.append(vehicle_pr_info_dict)
        return jsonify(vehicle_pr_infos)


@app.route('/check_point', methods=['GET'])
def check_point():
    return render_template('check_point_query.html')


@app.route('/AVC/api/check_point', methods=['POST'])
def query_product_line_check_point():
    data = request.json
    vins = data.get('vins')
    token = LiveTokenGetter.get_app_live_token('车辆数据服务中心(AVC)')['token']
    vehicle_guodian_infos = []
    for vin in vins:
        checkpoint_infos = AVCGetter.get_vehicle_info_request(token, vin, 'VehicleGuoDianInfo')
        if checkpoint_infos != {'error': '未查询到任何信息！'}:
            checkpoint_status = []
            checkpoint_date = []
            checkpoint_time = []
            checkpoint_position = []
            for guodian in checkpoint_infos:
                checkpoint_status.append(guodian['status'])
                checkpoint_date.append(guodian['mdatum'])
                checkpoint_time.append(guodian['mzeit'])
                checkpoint_position.append(guodian['fanlage'])
            vehicle_guodian_info = {'工位': checkpoint_position, '状态点': checkpoint_status, '日期': checkpoint_date,
                                    '时间': checkpoint_time}
            vehicle_guodian_infos.append(vehicle_guodian_info)
        else:
            vehicle_guodian_infos.append(checkpoint_infos)
        return jsonify(vehicle_guodian_infos)


@app.route('/unicom_sim_query_tool', methods=['GET'])
def unicom_sim_query_tool():
    return render_template('unicom_sim_query.html')


@app.route('/api/unicom_sim_query', methods=['GET'])
def unicom_sim_query():
    project = request.args.get('project')
    search_value = request.args.get('search_value')
    response = requests.get(
        url=f'http://47.116.180.173:5000/JasperGetter/SIMData?project={project}&search_value={search_value}',
    )
    return response.text


@app.route('/uat_cei_dp_query', methods=['GET'])
def uat_cei_dp_query():
    return render_template('uat_cei_dp_query.html')


@app.route('/uat_cei_dp/api/get_uat_cei_dp_info/<vin>', methods=['GET'])
def get_uat_cei_dp_info(vin):
    url = 'http://svw-cei-vehicle.uatapps.aliocp.csvw.com/vehicle/internal/v1/info/detail/by/vin'
    parameter = {'vin': vin}
    response = requests.get(url, params=parameter)
    try:
        response = json.loads(response.text)['data']
        response_dict = {
            'vin': response['vin'],
            '车机SN': response['pdsn'],
            'iccid': response['iccid'],
            'imei': response['imei'],
            'imsi': response['imsi'],
            '软件版本': response['softwareVersion'],
            '硬件版本': response['hardwareVersion'],
            'RP状态': response['rnpStatus'],
            'RP时间': response['rnpDate'],
            'sim卡状态': response['simStatus'],
            'SL版本': response['servicelistVersion'],
            '品牌': response['brandName'],
            '车系': response['seriesName'],
            'model code': response['modelCode'],
            '车型': response['modelName'],
            '运营商': response['simOperatorName'],
            '换件标记': response['swapFlag'],
            '记录创建时间': response['createdTime'],
            '记录更新时间': response['updatedTime']
        }
        return jsonify(response_dict)
    except KeyError as e:
        return jsonify(json.loads(response.text))


@app.route('/live_cei_dp_query', methods=['GET'])
def live_cei_dp_query():
    return render_template('live_cei_dp_query.html')


@app.route('/live_cei_dp/api/get_live_cei_dp_info/<vin>', methods=['GET'])
def get_live_cei_dp_info(vin):
    url = 'http://svw-cei-vehicle.prodapps.aliocp.csvw.com/vehicle/internal/v1/info/detail/by/vin'
    parameter = {'vin': vin}
    response = requests.get(url, params=parameter)
    try:
        response = json.loads(response.text)['data']
        response_dict = {
            'vin': response['vin'],
            '车机SN': response['pdsn'],
            'iccid': response['iccid'],
            'imei': response['imei'],
            'imsi': response['imsi'],
            '软件版本': response['softwareVersion'],
            '硬件版本': response['hardwareVersion'],
            'RP状态': response['rnpStatus'],
            'RP时间': response['rnpDate'],
            'sim卡状态': response['simStatus'],
            'SL版本': response['servicelistVersion'],
            '品牌': response['brandName'],
            '车系': response['seriesName'],
            'model code': response['modelCode'],
            '车型': response['modelName'],
            '运营商': response['simOperatorName'],
            '换件标记': response['swapFlag'],
            '记录创建时间': response['createdTime'],
            '记录更新时间': response['updatedTime']
        }
        return jsonify(response_dict)
    except KeyError as e:
        return jsonify(json.loads(response.text))


@app.route('/cert_key_resolve_tool', methods=['GET'])
def cert_key_resolve_tool():
    return render_template('cert_key_resolver.html')


@app.route('/api/cert_key_resolver', methods=['POST'])
def cert_key_resolver():
    cert_file = request.files.get('cert')
    key_file = request.files.get('key')
    results = cert_key_parse(cert_file, key_file)
    if results == {'error': '未收到有效的文件或文件内容无法解析。'}:
        return jsonify(results), 400
    else:
        return jsonify(results)


@app.route('/submit_vehicle_config_tool', methods=['GET'])
def submit_vehicle_config_tool():
    return render_template('vehicle_test_data_set.html')


@app.route('/api/submit_vehicle_config_sp', methods=['POST'])
def submit_vehicle_config_sp():
    vehicle_data_dict = request.json['vehicle_data']
    if vehicle_data_dict['项目版本号'] == 'MOS_A_NB_Low' or vehicle_data_dict['项目版本号'] == 'MOS_A_NB_High':
        vehicle_data_dict['项目版本号'] = 'MOS_A_NB'
    check_duplicted = request.json['check_duplicated']
    vin = vehicle_data_dict['车辆VIN码']
    spt = SPTool()
    vehicle_data = spt.get_sp_details(vin, 'vw')
    if vehicle_data == '车辆未找到！':
        response = spt.vehicle_test_data_file_processor('vw', vehicle_data_dict)
        return jsonify(response)
    else:
        if check_duplicted:
            return jsonify(f'{vin}车辆信息在后台存在!')
        else:
            response = spt.vehicle_test_data_file_processor('vw', vehicle_data_dict)
            return jsonify(response)


@app.route('/api/submit_vehicle_config_cdp', methods=['POST'])
def submit_vehicle_config_cdp():
    vehicle_data_dict = request.json['vehicle_data']
    check_duplicated = request.json['check_duplicated']
    vin = vehicle_data_dict['车辆VIN码']
    cookies = web_driver_get_vmp_cookies()
    status_vehicle, result_vehicle = query_vehicle_info('vin', vin, cookies)
    if not status_vehicle:
        if result_vehicle == '未在车辆管理平台登记,请联系管理员':
            set_result = set_vmp_data(vehicle_data_dict, cookies)
            response = {
                '数据维护结果': set_result
            }
        else:
            # VIN查询失败但反馈不是查不到
            msg = f'检查车辆重复值异常:{result_vehicle}'
            response = {
                '数据维护结果': msg
            }
    else:
        if check_duplicated:
            response = f'{vin}车辆信息在后台存在!'
        else:
            set_result = set_vmp_data(vehicle_data_dict, cookies)
            response = {
                '数据维护结果': set_result
            }

    return jsonify(response)


@app.route('/api/submit_vehicle_config_afdp', methods=['POST'])
def submit_vehicle_config_afdp():
    vehicle_data_dict = request.json['vehicle_data']
    check_duplicated = request.json['check_duplicated']
    vin = vehicle_data_dict['车辆VIN码']
    check_result = uat_af_dp_data_read(vin)['data']
    if check_result == f'UAT AF DP主数据平台未找到{vin}！':
        status, result = uat_af_dp_config_set(vehicle_data_dict)
        if status:
            return jsonify(result)
        else:
            return jsonify(result), 400
    else:
        if check_duplicated:
            return jsonify(f'{vin}车辆信息在后台存在!')
        else:
            status, result = uat_af_dp_config_set(vehicle_data_dict)
            if status:
                return jsonify(result)
            else:
                return jsonify(result), 400


@app.route('/get_signed_iam_x509_cert_tool', methods=['GET'])
def get_signed_iam_x509_cert_tool():
    return render_template('get_signed_iam_x509_cert_tool.html')


@app.route('/api/get_signed_iam_x509_cert', methods=['POST'])
def get_signed_iam_x509_cert():
    csr_list = request.json['csrs']
    statuses = []
    results = []
    zone_token, cookies = web_driver_get_zone_token_cookies()
    for csr in csr_list:
        status, result = iam_x509_cert_sign(csr, zone_token, cookies)
        statuses.append(status)
        results.append(result)
    return jsonify(results)


@app.route('/api/signed_iam_x509_cert_check', methods=['POST'])
def signed_iam_x509_cert_check():
    sn_list = request.json['iamSns']
    statuses = []
    results = []
    zone_token, cookies = web_driver_get_zone_token_cookies()
    for sn in sn_list:
        status, result = get_x509_cert_by_sn(sn, zone_token, cookies)
        statuses.append(status)
        results.append(result)
    return jsonify(results)


@app.route('/get_signed_live_iam_x509_cert_tool', methods=['GET'])
def get_signed_live_iam_x509_cert_tool():
    return render_template('get_signed_live_iam_x509_cert_tool.html')


@app.route('/api/get_signed_live_iam_x509_cert', methods=['POST'])
def get_signed_live_iam_x509_cert():
    csr_list = request.json['csrs']
    statuses = []
    results = []
    zone_token, cookies = web_driver_get_zone_live_token_cookies()
    for csr in csr_list:
        status, result = live_iam_x509_cert_sign(csr, zone_token, cookies)
        statuses.append(status)
        results.append(result)
    return jsonify(results)


@app.route('/api/signed_live_iam_x509_cert_check', methods=['POST'])
def signed_live_iam_x509_cert_check():
    sn_list = request.json['iamSns']
    statuses = []
    results = []
    zone_token, cookies = web_driver_get_zone_live_token_cookies()
    for sn in sn_list:
        status, result = live_get_x509_cert_by_sn(sn, zone_token, cookies)
        statuses.append(status)
        results.append(result)
    return jsonify(results)


@app.route('/uds_nrc_list_check_tool', methods=['GET'])
def uds_nrc_list_check_tool():
    return render_template('uds_nrc_list.html')


@app.route('/uat_sp_project_change_tool', methods=['GET'])
def change_uat_sp_project_tool():
    return render_template('uat_sp_project_change.html')


@app.route('/api/change_uat_project', methods=['POST'])
def change_uat_sp_project():
    vin = request.json['车辆VIN码']
    hu_sw_version = request.json['车机软件版本号']
    department = request.json['申请部门']
    target_project = request.json['目标项目版本号']
    spt = SPTool()
    sp_details = spt.get_sp_details(vin, 'vw')
    try:
        vehicle_info_dict = sp_details['车辆MOS相关信息']
        sim_info_dict = sp_details['SIM卡信息']
    except KeyError:
        try:
            error_message = sp_details['error_message']
            return jsonify({'success': False, 'error': error_message}), 404
        except KeyError as e:
            return jsonify({'success': False, 'error': f'{e}'})
    try:
        vehicle_data_dict = generate_vehicle_config_data(
            project=target_project,
            car_software_version=hu_sw_version,
            hu_fazit_id=vehicle_info_dict['车机Fazit ID (SN)'],
            ocu_iccid=sim_info_dict['ICCID'],
            msisdn=sim_info_dict['MSISDN'],
            ocu_fazit_id=vehicle_info_dict['OCU Fazit ID (SN)'],
            vehicle_vin=vin,
            application_department=department
        )
    except VehicleConfigError as e:
        return jsonify({'success': False, 'error': f'{e}'})
    response = spt.vehicle_test_data_file_processor('vw', vehicle_data_dict)
    return jsonify({'success': True, 'data': response, 'message': '项目切换一般需要一天之后才会生效，请耐心等待，24小时后请查询UAT SP后台数据项目版本是否更新！'})


@app.route('/search_afc_sim_info_tool', methods=['GET'])
def search_afc_sim_info_tool():
    return render_template('search_afc_sim_info.html')


@app.route('/api/search_afc_sim_info', methods=['POST'])
def search_afc_sim_info():
    iccid = request.json['iccid']
    msisdn = request.json['msisdn']
    imsi = request.json['imsi']
    search_result = search_sim_data(iccid, msisdn, imsi)
    success_status = search_result['success']
    response = search_result['data']
    if success_status:
        return jsonify({'success': success_status, 'data': response, 'message': f'查询成功！'})
    else:
        return jsonify({'success': success_status, 'data': response, 'message': f'查询失败！{response}'})


@app.route('/uat_af_dp_data_search', methods=['GET'])
def uat_af_dp_data_search_tool():
    return render_template('uat_af_dp_data_search.html')


@app.route('/api/uat_af_dp_data_search', methods=['POST'])
def uat_af_dp_data_search():
    vin = request.json['vin']
    zxdsn = request.json['zxdsn']
    iamsn = request.json['iamsn']
    iccid = request.json['iccid']

    search_result = uat_af_dp_data_read(vin, zxdsn, iamsn, iccid)
    success_status = search_result['success']
    response = search_result['data']
    if success_status:
        return jsonify({'success': success_status, 'data': response, 'message': '查询成功！'})
    else:
        return jsonify({'success': success_status, 'data': response, 'message': '查询失败！'})


@app.route('/uat_vmp_data_search', methods=['GET'])
def uat_vmp_data_search_tool():
    return render_template('uat_vmp_data_search.html')


@app.route('/api/uat_vmp_data_search', methods=['POST'])
def uat_vmp_data_search():
    vin = request.json['vin']
    cduid = request.json['cduid']
    iccid = request.json['iccid']

    if vin is not None:
        by = 'vin'
        value = vin
    elif cduid is not None:
        by = 'cduid'
        value = cduid
    elif iccid is not None:
        by = 'iccid'
        value = iccid
    else:
        return jsonify({'success': False, 'data': {'vin': vin, 'cduid': cduid, 'iccid': iccid}, 'message': '查询失败！'})
    cookies = web_driver_get_vmp_cookies()
    try:
        vmp_data_status = get_vmp_data_status(by, value, cookies)
        success_status = True
    except Exception as e:
        vmp_data_status = e.__str__()
        success_status = False
    response = vmp_data_status
    if success_status:
        return jsonify({'success': success_status, 'data': response, 'message': '查询成功！'})
    else:
        return jsonify({'success': success_status, 'data': response, 'message': '查询失败！'})


@app.route('/api/x509_csr_parse', methods=['POST'])
def x509_csr_parse():
    csr = request.json['csr']
    csr_parsed = parse_csr_hex(csr)
    return jsonify(csr_parsed)


@app.route('/api/x509_cert_parse', methods=['POST'])
def x509_cert_parse():
    cert = request.json['cert']
    cert_parsed = parse_x509_hex_certificate(cert)
    return jsonify(cert_parsed)


@app.route('/uat_afc_dp_swap', methods=['GET'])
def afc_swap_tool():
    return render_template('uat_afc_swap.html')


@app.route('/api/afc_swap', methods=['POST'])
def afc_swap():
    project = request.json['project']
    vin = request.json['vin']
    if project == 'AF':
        zxdsn = request.json['zxdsn']
        iamsn = request.json['iamsn']
        iccid = request.json['iccid']
        msisdn = request.json['msisdn']
        status, AF_swap_result = af_swap(vin, zxdsn, iamsn, iccid, msisdn)
        print(AF_swap_result)
        return jsonify({'success': status, 'data': AF_swap_result, 'message': '换件请求成功！'})


    if project == 'C':
        cduid = request.json['cduid']
        iccid = request.json['iccid']
        msisdn = request.json['msisdn']
        return jsonify({'success': True, 'data': 'C车换件模块正在开发中', 'message': '换件请求成功！'})


@app.route('/hex_to_800_byte_tool', methods=['GET'])
def hex_to_800_byte_tool():
    return render_template('hex_to_800byte.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
