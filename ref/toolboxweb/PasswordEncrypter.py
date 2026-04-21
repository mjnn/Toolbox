from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

# # 您的公钥（Base64 编码）
# public_key_str = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC0lqYaFXtB7HR46f8SEqRoPwX3gU42hH9nZvTO6RuwIRQQVKbTKdIBw9VcKRx9UMyL4mNwsfaSXRRqLXuHjnv/E3yc2KtlJPPSkJMfKu///Oj+vs0aDCacmBzUe+cY/v9m4UcgXn26lME/PXkmCzR+sfWXc/V7G0bYl4YYmMs9jwIDAQAB"
#
# # 要加密的明文
# plaintext = "Mjnn991126@#"


def encrypt_password(public_key_str, plaintext):
    # 将 Base64 编码的公钥转换为 RSA 密钥对象
    public_key = RSA.import_key(base64.b64decode(public_key_str))

    # 创建 PKCS1_v1_5 加密器
    cipher = PKCS1_v1_5.new(public_key)

    # 加密数据（需要将字符串转换为字节）
    encrypted_data = cipher.encrypt(plaintext.encode('utf-8'))

    # 将加密结果转换为 Base64 字符串
    encrypted_base64 = base64.b64encode(encrypted_data).decode('utf-8')

    return encrypted_base64




