from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from binascii import unhexlify, Error as BinAsciiError
from datetime import datetime
from iam_x509_signature import hex_to_ascii, csr_preprocess


def parse_csr_hex(hex_csr_string: str) -> dict:
    """
    解析一个十六进制编码的CSR字符串，并返回一个包含其内容的字典。

    Args:
        hex_csr_string: 十六进制编码的CSR字符串。

    Returns:
        一个字典，包含解析后的CSR内容。如果解析失败，会包含一个 'error' 键。
    """
    parsed_data = {}
    hex_csr_string = csr_preprocess(hex_csr_string)

    try:
        # 1. 将十六进制字符串转换为DER编码的字节流
        der_csr_bytes = unhexlify(hex_csr_string)
    except Exception as e:
        parsed_data['error'] = f"无效的十六进制字符串: {e}"
        return parsed_data

    try:
        # 2. 从DER字节流加载CSR
        csr = x509.load_der_x509_csr(der_csr_bytes)
    except Exception as e:
        parsed_data['error'] = f"无法解析CSR，数据可能损坏或格式不正确: {e}"
        return parsed_data

    # 3. 解析Subject（主题）信息
    subject_info = {}
    for attribute in csr.subject:
        # 尝试映射常见的OID到易读的名称
        if attribute.oid == x509.oid.NameOID.COMMON_NAME:
            subject_info['common_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.ORGANIZATION_NAME:
            subject_info['organization_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME:
            subject_info['organizational_unit_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.LOCALITY_NAME:
            subject_info['locality_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.STATE_OR_PROVINCE_NAME:
            subject_info['state_or_province_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.COUNTRY_NAME:
            subject_info['country_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.EMAIL_ADDRESS:
            subject_info['email_address'] = attribute.value
        else:
            # 对于不常见的OID，保留其原始的OID字符串
            subject_info[attribute.oid.dotted_string] = attribute.value
    parsed_data['subject_info'] = subject_info
    parsed_data['subject_dn_string'] = csr.subject.rfc4514_string() # RFC4514标准的Subject DN字符串

    # 4. 解析Public Key（公钥）信息
    public_key = csr.public_key()
    public_key_info = {
        'type': public_key.__class__.__name__, # 例如 'RSAPublicKey' 或 'ECDSAPublicKey'
        'key_size_bits': None,
        'pem_format': None
    }

    if isinstance(public_key, rsa.RSAPublicKey):
        public_key_info['key_size_bits'] = public_key.key_size
    elif isinstance(public_key, ec.EllipticCurvePublicKey):
        public_key_info['curve_name'] = public_key.curve.name
        public_key_info['key_size_bits'] = public_key.curve.key_size # 椭圆曲线密钥的大小
    # 可以添加其他密钥类型的处理，如 dsa.DSAPublicKey

    # 将公钥导出为PEM格式，方便查看
    try:
        public_key_info['pem_format'] = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    except Exception as e:
        public_key_info['pem_format'] = f"无法导出PEM格式的公钥: {e}"

    parsed_data['public_key'] = public_key_info

    # 5. 解析签名算法
    parsed_data['signature_algorithm'] = csr.signature_algorithm_oid.dotted_string
    parsed_data['signature_hash_algorithm'] = csr.signature_hash_algorithm.name

    # 6. 验证CSR的签名（使用CSR中包含的公钥）
    # 这可以确认CSR本身的完整性，没有被篡改
    parsed_data['is_signature_valid'] = csr.is_signature_valid

    # 7. 解析CSR扩展
    extensions_list = []
    for ext in csr.extensions:
        ext_info = {
            'oid': ext.oid.dotted_string,
            'name': ext.oid._name if hasattr(ext.oid, '_name') else ext.oid.dotted_string, # 尝试获取常见名称
            'critical': ext.critical,
            'value': None
        }
        # 对常见的扩展类型进行特殊处理，以便更好地展现其内容
        if ext.oid == x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
            sans = ext.value
            dns_names = [name.value for name in sans.get_values_for_type(x509.DNSName)]
            ip_addresses = [str(ip) for ip in sans.get_values_for_type(x509.IPAddress)]
            ext_info['value'] = {'dns_names': dns_names, 'ip_addresses': ip_addresses}
        elif ext.oid == x509.oid.ExtensionOID.BASIC_CONSTRAINTS:
            value = ext.value
            ext_info['value'] = {
                'ca': value.ca,
                'path_length': value.path_length
            }
        else:
            # 对于其他未知或不常见的扩展，尝试将其值转换为字符串
            try:
                ext_info['value'] = str(ext.value)
            except Exception:
                ext_info['value'] = "[无法解析的具体值]" # 无法转换时提供一个占位符

        extensions_list.append(ext_info)
    parsed_data['extensions'] = extensions_list

    return parsed_data


from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from binascii import unhexlify, Error as BinAsciiError
from datetime import datetime

# 辅助函数：解析X.509Name对象，用于Subject和Issuer
def _parse_x509_name(name_obj: x509.Name) -> dict:
    """
    解析 X.509 Name 对象，提取其中的属性。
    """
    name_info = {}
    for attribute in name_obj:
        # 尝试映射常见的OID到易读的名称
        if attribute.oid == x509.oid.NameOID.COMMON_NAME:
            name_info['common_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.ORGANIZATION_NAME:
            name_info['organization_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME:
            name_info['organizational_unit_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.LOCALITY_NAME:
            name_info['locality_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.STATE_OR_PROVINCE_NAME:
            name_info['state_or_province_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.COUNTRY_NAME:
            name_info['country_name'] = attribute.value
        elif attribute.oid == x509.oid.NameOID.EMAIL_ADDRESS:
            name_info['email_address'] = attribute.value
        else:
            # 对于不常见的OID，保留其原始的OID字符串
            name_info[attribute.oid.dotted_string] = attribute.value
    name_info['full_dn_string'] = name_obj.rfc4514_string()  # RFC4514标准的DN字符串
    return name_info

def parse_x509_hex_certificate(hex_cert_string: str) -> dict:
    """
    解析一个十六进制编码的X.509证书字符串，并返回一个包含其内容的字典。
    会在解析前移除字符串末尾的`00`字节以处理可能的填充。

    Args:
        hex_cert_string: 十六进制编码的X.509证书字符串。

    Returns:
        一个字典，包含解析后的证书内容。如果解析失败，会包含一个 'error' 键。
    """
    parsed_data = {}

    try:
        # 1. 将十六进制字符串转换为DER编码的字节流
        der_cert_bytes = unhexlify(hex_cert_string)

        # 2. 移除末尾的00字节（如果存在）
        # 循环移除，以防有多个连续的00填充
        while der_cert_bytes.endswith(b'\x00'):
            der_cert_bytes = der_cert_bytes[:-1]

    except BinAsciiError as e:
        parsed_data['error'] = f"无效的十六进制字符串: {e}"
        return parsed_data
    except Exception as e:
        parsed_data['error'] = f"处理十六进制字符串时发生未知错误: {e}"
        return parsed_data

    try:
        # 3. 从DER字节流加载X.509证书
        cert = x509.load_der_x509_certificate(der_cert_bytes)
    except Exception as e:
        parsed_data['error'] = f"无法解析X.509证书，数据可能损坏或格式不正确: {e}"
        return parsed_data

    # 4. 解析证书基本信息
    parsed_data['version'] = cert.version.name  # 证书版本 (e.g., 'v3')
    parsed_data['serial_number'] = f"0x{cert.serial_number:x}"  # 序列号 (十六进制表示)

    # 5. 解析颁发者 (Issuer) 和主题 (Subject) 信息
    parsed_data['issuer'] = _parse_x509_name(cert.issuer)
    parsed_data['subject'] = _parse_x509_name(cert.subject)

    # 6. 解析有效期 - 修正：使用 UTC 时间属性来避免警告
    parsed_data['not_valid_before'] = cert.not_valid_before_utc.isoformat() + 'Z'  # 开始日期 (ISO 8601格式，UTC时区)
    parsed_data['not_valid_after'] = cert.not_valid_after_utc.isoformat() + 'Z'  # 结束日期 (ISO 8601格式，UTC时区)

    # 7. 解析公钥信息
    public_key = cert.public_key()
    public_key_info = {
        'type': public_key.__class__.__name__,  # 例如 'RSAPublicKey' 或 'ECDSAPublicKey'
        'key_size_bits': None,
        'pem_format': None
    }

    if isinstance(public_key, rsa.RSAPublicKey):
        public_key_info['key_size_bits'] = public_key.key_size
    elif isinstance(public_key, ec.EllipticCurvePublicKey):
        public_key_info['curve_name'] = public_key.curve.name
        public_key_info['key_size_bits'] = public_key.curve.key_size

    try:
        public_key_info['pem_format'] = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8').strip()
    except Exception as e:
        public_key_info['pem_format'] = f"无法导出PEM格式的公钥: {e}"

    parsed_data['public_key'] = public_key_info

    # 8. 解析签名算法和签名值
    parsed_data['signature_algorithm_oid'] = cert.signature_algorithm_oid.dotted_string
    parsed_data['signature_hash_algorithm'] = cert.signature_hash_algorithm.name
    # 签名值通常不需要单独解析，它用于验证证书完整性，但可以获取其十六进制表示
    # parsed_data['signature_value'] = cert.signature.hex()

    # 9. 导出整个证书为PEM格式，方便查看
    try:
        parsed_data['pem_certificate'] = cert.public_bytes(
            encoding=serialization.Encoding.PEM
        ).decode('utf-8').strip()
    except Exception as e:
        parsed_data['pem_certificate'] = f"无法导出PEM格式的证书: {e}"

    # 10. 解析证书扩展 (Extensions)
    extensions_list = []
    for ext in cert.extensions:
        ext_info = {
            'oid': ext.oid.dotted_string,
            'name': ext.oid._name if hasattr(ext.oid, '_name') else ext.oid.dotted_string,
            'critical': ext.critical,
            'value': None
        }

        # 对于常见的扩展类型进行特殊处理，以便更好地展现其内容
        if ext.oid == x509.oid.ExtensionOID.BASIC_CONSTRAINTS:
            value = ext.value
            ext_info['value'] = {
                'ca_flag': value.ca,
                'path_length': value.path_length if value.path_length is not None else "无限制"
            }
        elif ext.oid == x509.oid.ExtensionOID.KEY_USAGE:
            value = ext.value
            key_usages = {}
            # 标记哪些Key Usage是启用的
            key_usages['digital_signature'] = value.digital_signature
            key_usages['content_commitment'] = value.content_commitment
            key_usages['key_encipherment'] = value.key_encipherment
            key_usages['data_encipherment'] = value.data_encipherment
            key_usages['key_agreement'] = value.key_agreement
            key_usages['key_cert_sign'] = value.key_cert_sign
            key_usages['crl_sign'] = value.crl_sign

            # 修正：只有当 key_agreement 是 True 时，才检查 encipher_only 和 decipher_only
            # 否则，按照 cryptography 库的语义，它们是未定义的
            if value.key_agreement:
                key_usages['encipher_only'] = value.encipher_only
                key_usages['decipher_only'] = value.decipher_only
            else:
                key_usages['encipher_only'] = False
                key_usages['decipher_only'] = False  # 如果 key_agreement 为 False，则这些也应视为 False

            ext_info['value'] = key_usages
        elif ext.oid == x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
            sans = ext.value
            dns_names = [name.value for name in sans.get_values_for_type(x509.DNSName)]
            ip_addresses = [str(ip) for ip in sans.get_values_for_type(x509.IPAddress)]
            uris = [str(uri) for uri in sans.get_values_for_type(x509.UniformResourceIdentifier)]
            emails = [str(email) for email in sans.get_values_for_type(x509.RFC822Name)]
            ext_info['value'] = {
                'dns_names': dns_names,
                'ip_addresses': ip_addresses,
                'uris': uris,
                'emails': emails
            }
        elif ext.oid == x509.oid.ExtensionOID.EXTENDED_KEY_USAGE:
            ext_info['value'] = [oid.dotted_string for oid in ext.value]
        elif ext.oid == x509.oid.ExtensionOID.AUTHORITY_KEY_IDENTIFIER:
            value = ext.value
            ext_info['value'] = {
                'key_identifier': value.key_identifier.hex() if value.key_identifier else None,
                'authority_cert_issuer': [_parse_x509_name(name) for name in
                                          value.authority_cert_issuer] if value.authority_cert_issuer else [],
                'authority_cert_serial_number': f"0x{value.authority_cert_serial_number:x}" if value.authority_cert_serial_number else None
            }
        elif ext.oid == x509.oid.ExtensionOID.SUBJECT_KEY_IDENTIFIER:
            ext_info['value'] = ext.value.digest.hex()
        elif ext.oid == x509.oid.ExtensionOID.CRL_DISTRIBUTION_POINTS:
            points = []
            # Handling a potential case where `dp.full_name` might be None
            for dp in ext.value:
                if dp.full_name:
                    uris = [str(name.value) for name in
                            dp.full_name.get_values_for_type(x509.UniformResourceIdentifier)]
                    if uris:  # Only add if there are actual URIs
                        points.append({'uris': uris})
                elif dp.crl_issuer:  # Also check crl_issuer if full_name is None
                    crl_issuer_names = [_parse_x509_name(name) for name in dp.crl_issuer]
                    if crl_issuer_names:
                        points.append({'crl_issuer': crl_issuer_names})
            ext_info['value'] = points
        else:
            # 对于其他未知或不常见的扩展，尝试将其值转换为字符串
            try:
                ext_info['value'] = str(ext.value)
            except Exception:
                ext_info['value'] = "[无法解析的具体值]"  # 无法转换时提供一个占位符

        extensions_list.append(ext_info)
    parsed_data['extensions'] = extensions_list
    return parsed_data


