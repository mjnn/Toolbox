import json
import re
from Zone_token_getter import *
from TimeStampProcessor import *
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def hex_to_ascii(hex_string):
    cleaned_hex_string = hex_string.replace(" ", "").strip()
    if not cleaned_hex_string:
        return "错误：输入的十六进制字符串为空。"
    if len(cleaned_hex_string) % 2 != 0:
        return f"错误：十六进制字符串长度（{len(cleaned_hex_string)}）必须是偶数，因为一个字节需要两个十六进制字符。"
    try:
        byte_data = bytes.fromhex(cleaned_hex_string)
        ascii_string = byte_data.decode('ascii')
        return ascii_string
    except ValueError as e:
        return f"错误：输入的十六进制字符串包含无效的十六进制字符。详细：{e}"
    except UnicodeDecodeError as e:
        return f"错误：十六进制数据无法完全解码为 ASCII 字符串，可能包含非 ASCII 字符。尝试使用 'utf-8' 解码或检查数据。详细：{e}"
    except Exception as e:
        return f"发生未知错误：{e}"


def csr_preprocess(csr):
    if csr[0:8] == '7103AF0B':
        csr = csr[14:]
        csr = re.sub(r'(00)+$', '', csr)
        csr = hex_to_ascii(csr)
        print('处理后的CSR：', csr)
        return csr
    elif csr[0:4] == '3330':
        csr = re.sub(r'(00)+$', '', csr)
        csr = hex_to_ascii(csr)
        print('处理后的CSR：', csr)
        return csr
    elif csr[0:4] == '3081':
        csr = re.sub(r'(00)+$', '', csr)
        print('可能直接传的AScii CSR')
        return csr
    elif csr[0:4] == '3333':
        csr = re.sub(r'(00)+$', '', csr)
        csr = hex_to_ascii(csr)
        csr = hex_to_ascii(csr)
        print('可能直接传的AScii CSR')
        return csr


def iam_x509_cert_sign(csr, zone_token, cookies):
    csr = csr_preprocess(csr)
    url = 'https://zapi-zone.mosop-uat.csvw.com/usap/web/webapi/x509/carCert/apply'
    payload = {
        'csr': csr
    }
    apply_response = post_request_to_zone_usap(url, payload, zone_token, cookies)
    apply_result = json.loads(apply_response.text)['message']
    if apply_result != '成功':
        return False, {"error": apply_response.text}
    else:
        decimal_random = generate_17_decimal_random()
        url = f'https://zapi-zone.mosop-uat.csvw.com/usap/web/webapi/x509/carCert/search?perPage=10&page=1&__rid={str(decimal_random)}'
        search_cert_response = get_request_to_zone_usap(url, zone_token, cookies)
        certs = json.loads(search_cert_response.text)['data']['items']
        cert_id = ''
        iam_sn = ''
        for cert in certs:
            if cert['creatorName'] == 'INT18186':
                cert_id = cert['certId']
                iam_sn = cert['subjectCn']
                break
            else:
                continue
        if cert_id == '':
            return False, {"error": search_cert_response}
        else:
            url = f'https://zapi-zone.mosop-uat.csvw.com/usap/web/webapi/x509/cert/export?certId={cert_id}'
            export_cert_response = get_request_to_zone_usap(url, zone_token, cookies)
            cert_signed = export_cert_response.text
            cert_signed = pad_hex_to_800_bytes(cert_signed)
            return True, {iam_sn: cert_signed}


def pad_hex_to_800_bytes(hex_input_string):
    """
    将十六进制字符串转换为字节，并在末尾补齐00，直到总字节数达到800。
    参数:
        hex_input_string (str): 用户输入的十六进制字符串。例如 "48656c6c6f" 或 "48 65 6c"
    返回:
        str: 补齐后的十六进制字符串 (总长度为 1600 个十六进制字符)，
             或包含错误信息的字符串。
    """
    TARGET_BYTE_LENGTH = 800
    TARGET_HEX_LENGTH = TARGET_BYTE_LENGTH * 2 # 800 字节 = 1600 个十六进制字符
    # 1. 清理输入：移除所有空格，并转换为小写（fromhex 允许大小写，但规范化有助于处理）
    cleaned_hex = hex_input_string.replace(" ", "").strip().lower()
    # 2. 校验清理后的十六进制字符串是否为空
    if not cleaned_hex:
        # 如果输入为空，则直接返回 800 个零字节
        print(f"提示：输入的十六进制为空，将生成 {TARGET_BYTE_LENGTH} 个零字节。")
        return (b'\x00' * TARGET_BYTE_LENGTH).hex()
    # 3. 校验十六进制字符串长度是否为偶数
    if len(cleaned_hex) % 2 != 0:
        return f"错误：输入的十六进制字符串 '{hex_input_string}' 清理后长度 ({len(cleaned_hex)}) 为奇数，无法解析为完整的字节序列。"
    try:
        # 4. 将十六进制字符串转换为字节序列
        original_bytes = bytes.fromhex(cleaned_hex)
        current_byte_length = len(original_bytes)
        # 5. 检查原始字节长度是否已经超过目标长度
        if current_byte_length > TARGET_BYTE_LENGTH:
            # 如果原始字节数据已经超过 800 字节，我们不进行截断，而是返回原始数据并提示
            print(f"警告：输入的十六进制数据转换为 {current_byte_length} 字节，已超过 {TARGET_BYTE_LENGTH} 字节目标长度。")
            print("将返回原始数据，不进行截断。")
            return original_bytes.hex()
        # 6. 计算需要补齐的零字节数量
        padding_needed = TARGET_BYTE_LENGTH - current_byte_length
        # 7. 创建补齐用的零字节序列
        padding_bytes = b'\x00' * padding_needed
        # 8. 合并原始字节和补齐字节
        padded_bytes = original_bytes + padding_bytes
        # 9. 将补齐后的字节序列转换回十六进制字符串并返回
        return padded_bytes.hex()
    except ValueError as e:
        # 捕获 bytes.fromhex() 可能抛出的错误，例如包含无效字符
        return f"错误：输入的十六进制字符串 '{hex_input_string}' 包含无效的十六进制字符。详细：{e}"
    except Exception as e:
        # 捕获其他未知错误
        return f"发生未知错误：{e}"


def get_x509_cert_by_sn(sn, zone_token, cookies):
    decimal_random = generate_17_decimal_random()
    url = f'https://zapi-zone.mosop-uat.csvw.com/usap/web/webapi/x509/carCert/search?sn={sn}&perPage=10&page=1&__rid={str(decimal_random)}'
    search_cert_response = get_request_to_zone_usap(url, zone_token, cookies)
    certs = json.loads(search_cert_response.text)['data']['items']
    if not certs:
        return False, {sn: '该IAM没有签发过证书！'}
    else:
        cert_id = certs[0]['certId']
        url = f'https://zapi-zone.mosop-uat.csvw.com/usap/web/webapi/x509/cert/export?certId={cert_id}'
        export_cert_response = get_request_to_zone_usap(url, zone_token, cookies)
        cert_signed = export_cert_response.text
        cert_signed = pad_hex_to_800_bytes(cert_signed)
        return True, {sn: cert_signed}
