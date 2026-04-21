import re
from datetime import datetime


class VehicleConfigError(Exception):
    """自定义异常，用于表示车辆配置数据生成过程中的错误"""
    pass
# 规则数据，与前端JavaScript中的rules数组保持一致
# 注意：Python中的换行符'\n'在字符串中就是字面量，无需转义
RULES = [
    # 项目版本号 OCU类型 品牌 车机类型 燃油类型 车机软件版本号 PRNR 发电机号 运营商 产线平台 HU零件号 OCU零件号
    { "项目版本号": "MOS3_1", "OCU类型": "LOW", "品牌": "VW", "车机类型": "CNS2.0", "燃油类型": "FV", "车机软件版本号": ["0138"], "PRNR": "~28UN~27T0\n~28UW~27T0", "发电机号": "空", "运营商": "CMCC", "产线平台": "MQB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS3_1", "OCU类型": "LOW", "品牌": "VW", "车机类型": "CRS3.0", "燃油类型": "FV", "车机软件版本号": ["0138"], "PRNR": "~28AT", "发电机号": "空", "运营商": "CMCC", "产线平台": "MQB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS3_1", "OCU类型": "HIGH", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "FV", "车机软件版本号": ["00XX", "01XX"], "PRNR": "~28AR~27T3\n~28AR~27T0", "发电机号": "空", "运营商": "CMCC", "产线平台": "MQB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS3_1", "OCU类型": "HIGH", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "FV", "车机软件版本号": ["04XX"], "PRNR": "~28AR~27T3\n~28AR~27T0", "发电机号": "空", "运营商": "CMCC", "产线平台": "MQB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS3_2", "OCU类型": "HIGH", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "FV", "车机软件版本号": ["02XX", "03XX"], "PRNR": "~28AR~27T3\n~28AR~27T0", "发电机号": "空", "运营商": "CMCC", "产线平台": "MQB_37W", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS3_2_PLUS", "OCU类型": "HIGH", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "FV", "车机软件版本号": ["07XX", "C7XX"], "PRNR": "~28AR~27T3\n~28AR~27T0", "发电机号": "空", "运营商": "CMCC", "产线平台": "MQB_37W", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS3.X_BM", "OCU类型": "HIGH", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "FV", "车机软件版本号": ["06XX", "08XX", "C8XX", "09XX", "C9XX"], "PRNR": "~28AR~27T3\n~28AR~27T0", "发电机号": "空", "运营商": "CMCC", "产线平台": "MQB_37W", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS_CEI", "OCU类型": "OCB", "品牌": "VW", "车机类型": "SOC", "燃油类型": "FV", "车机软件版本号": ["00XX", "X0XX", "01XX", "X1XX", "04XX", "X4XX"], "PRNR": "~28DJ", "发电机号": "空", "运营商": "CUSC", "产线平台": "MQB_37WBaseline", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS3_GP", "OCU类型": "Conmod5G", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "FV", "车机软件版本号": ["01XX", "C1XX", "02XX", "C2XX"], "PRNR": "~28DK~27UY~2EL8\n~28DL~27UY~2EL8", "发电机号": "空", "运营商": "CUSC", "产线平台": "MQB_37WBaseline", "HU零件号": "3JD035866", "OCU零件号": "3JD035741" },
    { "项目版本号": "MOS3_GP_2", "OCU类型": "Conmod5G", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "FV", "车机软件版本号": ["C3XX", "03XX", "C4XX", "04XX"], "PRNR": "~28DL~27UY~2EL8\n~28DK~27UY~2EL8", "发电机号": "空", "运营商": "CUSC", "产线平台": "MQB_37WBaseline", "HU零件号": "3JD035866A", "OCU零件号": "3JD035741B" },
    { "项目版本号": "MOS3_GP_3", "OCU类型": "Conmod5G", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "FV", "车机软件版本号": ["C5XX", "05XX", "C6XX", "06XX"], "PRNR": "~28DL~27UY~2EL8\n~28DK~27UY~2EL8", "发电机号": "空", "运营商": "CUSC", "产线平台": "MQB_37WBaseline", "HU零件号": "3JD035866B", "OCU零件号": "3JD035741E" },
    { "项目版本号": "MOS3_GP_4", "OCU类型": "Conmod5G", "品牌": "VW", "车机类型": "CNS3.0", "燃油类型": "PHEV", "车机软件版本号": ["C5XX", "05XX", "C6XX", "06XX", "C7XX", "07XX"], "PRNR": "~28DL~27UY~2EL8\n~28DK~27UY~2EL8", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MQB_37WBaseline", "HU零件号": "3JD035866C", "OCU零件号": "3JD035741C" },
    { "项目版本号": "MOS3_PNS", "OCU类型": "PNS", "品牌": "VW", "车机类型": "PNS", "燃油类型": "FV", "车机软件版本号": ["0138"], "PRNR": "~28YZ~27Q4~2EL7", "发电机号": "空", "运营商": "CMCC", "产线平台": "MQB_37W", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS4_0", "OCU类型": "OCU4", "品牌": "VW", "车机类型": "ICAS3", "燃油类型": "BEV", "车机软件版本号": ["0XXX", "1XXX"], "PRNR": "~28AS~2KS3\n~28AS~2KS0\n~28AV~2KS0\n~28AV~2KS3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS4_0_ME3", "OCU类型": "OCU4", "品牌": "VW", "车机类型": "ICAS3", "燃油类型": "BEV", "车机软件版本号": ["2XXX"], "PRNR": "~28AS~2KS3\n~28AS~2KS0\n~28AV~2KS0\n~28AV~2KS3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS4_0_ME3_1", "OCU类型": "OCU4", "品牌": "VW", "车机类型": "ICAS3", "燃油类型": "BEV", "车机软件版本号": ["291XX", "2949"], "PRNR": "~28AS~2KS3\n~28AS~2KS0\n~28AV~2KS0\n~28AV~2KS3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS4_0_ME3_2", "OCU类型": "OCU4", "品牌": "VW", "车机类型": "ICAS3", "燃油类型": "BEV", "车机软件版本号": ["292XX", "293XX", "2959"], "PRNR": "~28AS~2KS3\n~28AS~2KS0\n~28AV~2KS0\n~28AV~2KS3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS4_0_ME3_7", "OCU类型": "OCU4", "品牌": "VW", "车机类型": "ICAS3", "燃油类型": "BEV", "车机软件版本号": ["296XX", "297XX", "E96XX", "E97XX"], "PRNR": "~28AS~2KS3\n~28AS~2KS0\n~28AV~2KS0\n~28AV~2KS3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS4_0_ME3_8_2", "OCU类型": "OCU4", "品牌": "VW", "车机类型": "ICAS3", "燃油类型": "BEV", "车机软件版本号": ["298XX", "E98XX"], "PRNR": "~28AS~2KS3\n~28AS~2KS0\n~28AV~2KS0\n~28AV~2KS3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "IDS5", "OCU类型": "OCU4", "品牌": "VW", "车机类型": "ICAS3", "燃油类型": "BEV", "车机软件版本号": ["K3XX", "K4XX", "63XX", "64XX", "M6XX", "76XX"], "PRNR": "~28DC~24N3\n~28DB~24N0\n~28DB~24N3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "10C035878B", "OCU零件号": "14G035284C" },
    { "项目版本号": "Audi_A7L", "OCU类型": "Conbox", "品牌": "AUDI", "车机类型": "MIB3", "燃油类型": "FV", "车机软件版本号": ["35XX", "36XX"], "PRNR": "~2I8Z~2IV3", "发电机号": "空", "运营商": "CMCC", "产线平台": "MLB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "Audi_A7L_CL37", "OCU类型": "Conbox", "品牌": "AUDI", "车机类型": "MIB3", "燃油类型": "FV", "车机软件版本号": ["37XX", "38XX"], "PRNR": "~2I8Z~2IV3", "发电机号": "空", "运营商": "CMCC", "产线平台": "MLB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "Audi_A7L_CL39", "OCU类型": "Conbox", "品牌": "AUDI", "车机类型": "MIB3", "燃油类型": "FV", "车机软件版本号": ["39XX", "40XX", "42XX"], "PRNR": "~2I8Z~2IV3", "发电机号": "空", "运营商": "CMCC", "产线平台": "MLB", "HU零件号": "4M2035138", "OCU零件号": "80D035285B" },
    { "项目版本号": "Audi_CSUV", "OCU类型": "HIGH", "品牌": "AUDI", "车机类型": "MIB3", "燃油类型": "FV", "车机软件版本号": ["37XX", "38XX"], "PRNR": "~2I8Z~2EL5", "发电机号": "空", "运营商": "CMCC", "产线平台": "MLB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "Audi_ASUVe", "OCU类型": "OCU4", "品牌": "AUDI", "车机类型": "MIB3", "燃油类型": "BEV", "车机软件版本号": ["37XX", "38XX"], "PRNR": "~2ER6~2KS3~2IU3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "Audi_ASUVe_RD", "OCU类型": "OCU4", "品牌": "AUDI", "车机类型": "MIB3", "燃油类型": "BEV", "车机软件版本号": ["3840", "3873", "42XX"], "PRNR": "~2ER6~2KS3~2IU3", "发电机号": "DKX575213", "运营商": "CUSC", "产线平台": "MEB", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "Audi_A5L", "OCU类型": "Conmod", "品牌": "AUDI", "车机类型": "HCP3", "燃油类型": "FV", "车机软件版本号": ["0138"], "PRNR": "~2ER6~2JH1", "发电机号": "空", "运营商": "CUSC", "产线平台": "PPC", "HU零件号": "8B3035040E", "OCU零件号": "85C035283AD" },
    { "项目版本号": "Audi_BNB", "OCU类型": "IAM", "品牌": "AUDI", "车机类型": "ZXD", "燃油类型": "BEV", "车机软件版本号": ["0138"], "PRNR": "~PB0~KS0~U5N~U8B~U4M\n~PB0~KS1~U5N~U8B~U4M", "发电机号": "DKX575213", "运营商": "CTCC", "产线平台": "ADP", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "Audi_C_SUVE", "OCU类型": "IAM", "品牌": "AUDI", "车机类型": "ZXD", "燃油类型": "BEV", "车机软件版本号": ["0138"], "PRNR": "~PB1~KS0~U5N~U8B~U4M\n~PB1~KS1~U5N~U8B~U4M", "发电机号": "DKX575213", "运营商": "CTCC", "产线平台": "ADP", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "Audi_Q4", "OCU类型": "Conmod", "品牌": "AUDI", "车机类型": "ICC", "燃油类型": "FV", "车机软件版本号": ["X177-A200"], "PRNR": "~2ED6~2JH0\n~2ED6~2JH1", "发电机号": "空", "运营商": "CUSC", "产线平台": "MQB_37WBaseline", "HU零件号": "83H035020", "OCU零件号": "82D035741" },
    { "项目版本号": "MOS_A_NB", "OCU类型": "IAM", "品牌": "VW", "车机类型": "ZXD", "燃油类型": "PHEV", "车机软件版本号": ["0135"], "PRNR": "~200X~28DL~2EL6~2KS0\n~200X~28DL~2EL6~2KS1", "发电机号": "DKX575213", "运营商": "CTCC", "产线平台": "ADP", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS_F_SUV", "OCU类型": "IAM", "品牌": "VW", "车机类型": "ZXD", "燃油类型": "EREV", "车机软件版本号": ["0138"], "PRNR": "~206V~28DL~2EL8~2KS1", "发电机号": "DKX575213", "运营商": "CTCC", "产线平台": "ADP", "HU零件号": "空", "OCU零件号": "空" },
    { "项目版本号": "MOS_C_SUV", "OCU类型": "CDCU", "品牌": "VW", "车机类型": "CDCU", "燃油类型": "BEV", "车机软件版本号": ["0138"], "PRNR": "~28AY~27UT~2EL8", "发电机号": "DKX575213", "运营商": "CTCC", "产线平台": "CEA", "HU零件号": "空", "OCU零件号": "空" },
]


def generate_vehicle_config_data(
    project: str,
    car_software_version: str,
    hu_fazit_id: str,
    ocu_iccid: str,
    msisdn: str,
    ocu_fazit_id: str,
    vehicle_vin: str,
    application_department: str
) -> dict:
    """
    根据输入的车辆信息和预设规则生成完整的车辆配置数据字典。
    参数:
        project (str): 所属项目 (项目版本号)。
        car_software_version (str): 车机软件版本号。
        hu_fazit_id (str): HU Fazit ID（SN号）。
        ocu_iccid (str): OCU ICCID（19或20位数字）。
        msisdn (str): MSISDN（11位手机号码，无需+86）。
        ocu_fazit_id (str): OCU Fazit ID（SN号）。
        vehicle_vin (str): 车辆VIN码（17位）。
        application_department (str): 申请部门。
    返回:
        dict: 包含所有车辆配置数据的字典。
    抛出:
        VehicleConfigError: 如果输入数据不合法或规则匹配失败。
    """
    # 1. 客户端输入校验
    errors = []
    if not project:
        errors.append("所属项目为必填项！")
    if not car_software_version:
        errors.append("车机软件版本号为必填项！")
    if not hu_fazit_id:
        errors.append("HU Fazit ID（SN号）为必填项！")
    ocu_iccid = ocu_iccid.strip()
    if not ocu_iccid:
        errors.append("OCU ICCID为必填项！")
    # elif not re.fullmatch(r"^\d{19,20}$", ocu_iccid):
    #     errors.append("OCU ICCID必须是19或20位数字！")
    msisdn = msisdn.strip().replace("+86", "") # 移除 +86
    if not msisdn:
        errors.append("MSISDN为必填项！")
    # elif not re.fullmatch(r"^\d{11}$", msisdn):
    #     errors.append("MSISDN必须是11位数字！")
    if not ocu_fazit_id:
        errors.append("OCU Fazit ID（SN号）为必填项！")
    vehicle_vin = vehicle_vin.strip()
    if not vehicle_vin:
        errors.append("车辆VIN码为必填项！")
    elif len(vehicle_vin) != 17:
        errors.append("车辆VIN码必须为17位！")
    if not application_department:
        errors.append("申请部门为必填项！")
    if errors:
        raise VehicleConfigError("\n".join(errors))
    # 2. 根据规则匹配字段
    derived_fields = {
        "OCU类型": "",
        "品牌": "",
        "车机类型": "",
        "燃油类型": "",
        "PRNR": "",
        "发电机号": "",
        "运营商": "",
        "产线平台": "",
        "HU零件号": "",
        "OCU零件号": ""
    }
    # 将输入的车机软件版本号转换为大写并去除首尾空格，以便匹配规则
    car_software_version_normalized = car_software_version.upper().strip()
    matching_rules = []
    for rule in RULES:
        if rule['项目版本号'] == project:
            for pattern in rule['车机软件版本号']:
                # 将规则中的 'X' 替换为 '[0-9A-Z]' (表示数字或大写字母)
                # 使用 ^ 和 $ 确保完整匹配
                regex_pattern = re.compile(f"^{pattern.replace('X', '[0-9A-Z]')}$", re.IGNORECASE)
                if regex_pattern.fullmatch(car_software_version_normalized):
                    matching_rules.append(rule)
                    break # 找到一个匹配的版本号模式即可，避免重复添加同一条规则
    if not matching_rules:
        raise VehicleConfigError(
            f"根据项目版本号 '{project}' 和车机软件版本号 '{car_software_version}' " 
            "未找到匹配的规则，请检查输入。"
        )
    elif len(matching_rules) > 1:
        # 与前端逻辑一致，多条匹配时使用第一条并给出警告
        import warnings
        warnings.warn(
            f"警告：找到 {len(matching_rules)} 条匹配规则，已使用第一条。 " 
            "请考虑更精确的车机软件版本号输入。"
        )
        selected_rule = matching_rules[0]
    else:
        selected_rule = matching_rules[0]
    # 填充派生字段
    for key, val in derived_fields.items():
        rule_value = selected_rule.get(key)
        # 如果规则中是“空”，则转换为Python的空字符串
        derived_fields[key] = '' if rule_value == '空' else rule_value
    # 对于PRNR，前端会处理换行符，后端也应如此
    if derived_fields["PRNR"]:
        derived_fields["PRNR"] = derived_fields["PRNR"].replace(r'\n', '\n')
    # 3. 组合所有数据
    now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_data = {
        "所属项目": project,
        "添加环境": "UAT", # 固定值
        "OCU类型": derived_fields["OCU类型"],
        "品牌": derived_fields["品牌"],
        "HU Fazit ID": hu_fazit_id,
        "车机类型": derived_fields["车机类型"],
        "OCU ICCID": ocu_iccid,
        "MSISDN": msisdn,
        "OCU Fazit ID": ocu_fazit_id,
        "燃油类型": derived_fields["燃油类型"],
        "车辆VIN码": vehicle_vin,
        "发动机号": "CUGP00037", # 固定值
        "车机软件版本号": car_software_version,
        "项目版本号": project, # 与所属项目相同
        "PRNR": derived_fields["PRNR"],
        "发电机号": derived_fields["发电机号"],
        "VehicleNum": 1, # 固定值
        "生产时间": now_formatted,
        "颜色代码": "P1P1", # 固定值
        "颜色": "雅致白", # 固定值
        "运营商": derived_fields["运营商"],
        "产线平台": derived_fields["产线平台"],
        "HU零件号": derived_fields["HU零件号"],
        "OCU零件号": derived_fields["OCU零件号"],
        "申请部门": application_department
    }
    return full_data
# --- 使用示例 ---


if __name__ == "__main__":
    # 示例1: 成功生成数据
    print("--- 示例1: 成功生成数据 (MOS3_GP, C100) ---")
    try:
        data1 = generate_vehicle_config_data(
            project="MOS3_GP",
            car_software_version="C100",
            hu_fazit_id="HU_SN_12345",
            ocu_iccid="1234567890123456789",
            msisdn="13800138000",
            ocu_fazit_id="OCU_SN_54321",
            vehicle_vin="WVWZZZ1K0WP000001",
            application_department="技术部"
        )
        import json
        print(json.dumps(data1, indent=2, ensure_ascii=False))
        print("\n" + "="*50 + "\n")
    except VehicleConfigError as e:
        print(f"数据生成失败: {e}\n")
    # 示例2: 成功生成数据 (Audi_A7L_CL39, 42A1)
    print("--- 示例2: 成功生成数据 (Audi_A7L_CL39, 42A1) ---")
    try:
        data2 = generate_vehicle_config_data(
            project="Audi_A7L_CL39",
            car_software_version="42A1", # 匹配 42XX
            hu_fazit_id="AUDI_HU_SN_987",
            ocu_iccid="98765432109876543210",
            msisdn="13911112222",
            ocu_fazit_id="AUDI_OCU_SN_654",
            vehicle_vin="LA890DEF123456789",
            application_department="研发部"
        )
        import json
        print(json.dumps(data2, indent=2, ensure_ascii=False))
        print("\n" + "="*50 + "\n")
    except VehicleConfigError as e:
        print(f"数据生成失败: {e}\n")
    # 示例3: VIN码长度错误
    print("--- 示例3: VIN码长度错误 ---")
    try:
        generate_vehicle_config_data(
            project="MOS3_GP",
            car_software_version="C100",
            hu_fazit_id="HU_SN_12345",
            ocu_iccid="1234567890123456789",
            msisdn="13800138000",
            ocu_fazit_id="OCU_SN_54321",
            vehicle_vin="WVWZZZ1K0WP00001", # 16位
            application_department="技术部"
        )
    except VehicleConfigError as e:
        print(f"数据生成失败: {e}\n")
    print("\n" + "="*50 + "\n")
    # 示例4: 车机软件版本号不匹配
    print("--- 示例4: 车机软件版本号不匹配 ---")
    try:
        generate_vehicle_config_data(
            project="MOS3_GP",
            car_software_version="UNKNOWN", # 未知版本号
            hu_fazit_id="HU_SN_12345",
            ocu_iccid="1234567890123456789",
            msisdn="13800138000",
            ocu_fazit_id="OCU_SN_54321",
            vehicle_vin="TESTVIN123456789",
            application_department="技术部"
        )
    except VehicleConfigError as e:
        print(f"数据生成失败: {e}\n")
    print("\n" + "="*50 + "\n")
    # 示例5: MSISDN格式错误
    print("--- 示例5: MSISDN格式错误 ---")
    try:
        generate_vehicle_config_data(
            project="MOS3_GP",
            car_software_version="C100",
            hu_fazit_id="HU_SN_12345",
            ocu_iccid="1234567890123456789",
            msisdn="abc13800138000", # 包含非数字字符
            ocu_fazit_id="OCU_SN_54321",
            vehicle_vin="TESTVIN123456789",
            application_department="技术部"
        )
    except VehicleConfigError as e:
        print(f"数据生成失败: {e}\n")
    print("\n" + "="*50 + "\n")
    # 示例6: 多个必填项缺失
    print("--- 示例6: 多个必填项缺失 ---")
    try:
        generate_vehicle_config_data(
            project="",
            car_software_version="",
            hu_fazit_id="",
            ocu_iccid="123", # 错误格式
            msisdn="",
            ocu_fazit_id="",
            vehicle_vin="",
            application_department=""
        )
    except VehicleConfigError as e:
        print(f"数据生成失败: \n{e}\n")
    print("\n" + "="*50 + "\n")

