from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes # <<-- 额外导入 hashes 模块
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import sys # 用于打印警告信息到标准错误输出
def cert_key_parse(cert_file=None, key_file=None):
    """
    解析上传的证书和密钥文件，提取关键信息。
    Args:
        cert_file: 上传的证书文件对象 (werkzeug.FileStorage)。
        key_file: 上传的密钥文件对象 (werkzeug.FileStorage)。
    Returns:
        一个字典，包含证书和密钥的解析结果或错误信息。
    """
    results = {}
    if cert_file:
        try:
            cert_bytes = cert_file.read()
            cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
            # 提取证书信息
            issuer = cert.issuer.rfc4514_string()
            subject = cert.subject.rfc4514_string()
            serial_number = f"0x{cert.serial_number:X}" # 转换为十六进制字符串
            not_valid_before = cert.not_valid_before.isoformat()
            not_valid_after = cert.not_valid_after.isoformat()
            # 公钥信息
            public_key = cert.public_key()
            public_key_type = public_key.__class__.__name__
            public_key_size = getattr(public_key, 'key_size', 'N/AF') # RSA/DSA/ECC都有key_size
            # --- UPDATED: 获取证书指纹 (使用推荐的最新方法) ---
            fingerprint_sha256 = '获取失败'
            try:
                # 推荐且兼容最新版本 cryptography 的方式: 序列化为DER再哈希
                cert_der = cert.public_bytes(serialization.Encoding.DER)
                hasher = hashes.Hash(hashes.SHA256(), backend=default_backend())
                hasher.update(cert_der)
                fingerprint_sha256 = hasher.finalize().hex()
            except Exception as e_fingerprint:
                # 如果上述方法失败，尝试旧版本指纹方法 (如果库版本过旧且指纹方法签名不同)
                # 这种情况通常发生在 cryptography < 42.0.0 的版本，且 `fingerprint` 方法只接受一个参数 `hashes.SHA256()`
                # 但由于用户之前遇到的错误是 "takes 1 positional arguments but 2 were given"，
                # 说明即使是旧版，直接传入 serialization.Encoding.DER 也不是正确的用法。
                # 最佳实践是升级库或使用 DER+hash 组合。
                print(f"Warning: 计算证书SHA256指纹失败，尝试其他方式无效。错误: {e_fingerprint}", file=sys.stderr)
                fingerprint_sha256 = "无法获取，请尝试更新您的 cryptography 库。"
            # 转换为PEM格式（如果原始不是PEM，或者只是为了标准化输出）
            pem_content = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
            # 详细文本表示
            detailed_text = f"发行者 (Issuer): {issuer}\n" \
                            f"主体 (Subject): {subject}\n" \
                            f"序列号 (Serial Number): {serial_number}\n" \
                            f"有效期从 (Not Valid Before): {not_valid_before}\n" \
                            f"有效期至 (Not Valid After): {not_valid_after}\n" \
                            f"公钥类型 (Public Key Type): {public_key_type}\n" \
                            f"公钥大小 (Public Key Size): {public_key_size} bits\n" \
                            f"SHA256指纹: {fingerprint_sha256}\n" \
                            f"\n--- PEM 格式证书内容 (截取前200字符) ---\n" \
                            f"{pem_content[:200]}...\n"
            results['cert_info'] = {
                'issuer': issuer,
                'subject': subject,
                'serial_number': serial_number,
                'not_valid_before': not_valid_before,
                'not_valid_after': not_valid_after,
                'public_key_type': public_key_type,
                'public_key_size': public_key_size,
                'fingerprint_sha256': fingerprint_sha256,
                'pem_content': pem_content,
                'detailed_text': detailed_text
            }
        except ValueError as ve:
            # 捕获load_pem_x509_certificate可能抛出的ValueErrors（如格式错误）
            results['cert_error'] = f"解析证书失败，可能文件格式不正确或不是PEM编码: {str(ve)}"
        except Exception as e:
            results['cert_error'] = f"解析证书时发生未知错误: {str(e)}"
    if key_file:
        try:
            key_bytes = key_file.read()
            private_key = None
            pem_content = None
            # 尝试加载PEM格式私钥，可能无密码或有密码
            try:
                private_key = serialization.load_pem_private_key(
                    key_bytes, password=None, backend=default_backend()
                )
            except ValueError:
                # 如果PEM无密码加载失败，可能是DER或带密码的PEM。
                # 由于前端没有密码输入，带密码的PEM会失败
                pass # 目前暂不处理带密码的密钥
            if private_key is None: # 如果PEM加载失败，尝试DER格式
                # 注意：如果文件不是有效的DER，这里会再次抛出ValueError
                try:
                    private_key = serialization.load_der_private_key(
                        key_bytes, password=None, backend=default_backend()
                    )
                except ValueError:
                    # 如果DER也失败，且之前没有明确的PEM密码错误，再给出通用错误
                    if 'key_error' not in results:
                        results['key_error'] = "解析密钥失败: 可能是PEM格式但有密码，或不是有效的PEM/DER格式。"
            # 如果 private_key 已经成功加载了
            if private_key:
                # 转换为PEM格式，以便显示 (私钥内容不完全返回以增强安全性)
                pem_content = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8, # PKCS8 是比较通用的格式
                    encryption_algorithm=serialization.NoEncryption()
                ).decode('utf-8')
                key_type = private_key.__class__.__name__
                key_size = getattr(private_key, 'key_size', 'N/AF')
                public_exponent_val = getattr(private_key, 'public_exponent', None)
                detailed_text = f"密钥类型 (Key Type): {key_type}\n" \
                                f"密钥大小 (Key Size): {key_size} bits\n"
                if public_exponent_val:
                    detailed_text += f"公钥指数 (Public Exponent, 仅RSA): {public_exponent_val}\n"
                detailed_text += f"\n--- PEM 格式密钥内容 (截取前200字符, 私钥内容不显示完整) ---\n" \
                                 f"{pem_content[:200]}...\n"
                results['key_info'] = {
                    'key_type': key_type,
                    'key_size': key_size,
                    'public_exponent': public_exponent_val,
                    'pem_content': pem_content, # 这里只显示前200字符
                    'detailed_text': detailed_text
                }
            elif 'key_error' not in results:
                # 如果代码走到这里，说明 private_key 还是 None，且没有更具体的错误信息，则给出一个通用错误
                results['key_error'] = "解析密钥失败: 未知格式或无法识别的密钥文件，也可能缺少密码。"
        except ValueError as ve:
            results['key_error'] = f"解析密钥失败，可能文件格式不正确或需要密码: {str(ve)}"
        except Exception as e:
            results['key_error'] = f"解析密钥时发生未知错误: {str(e)}"
    if not results.get('cert_info') and not results.get('key_info') and \
            not results.get('cert_error') and not results.get('key_error'):
        return {'error': '未收到有效的文件或文件内容无法解析。'}
    return results
