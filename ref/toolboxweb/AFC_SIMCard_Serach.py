import os

import pandas as pd

from legacy_paths import toolboxweb_root


def _afc_sim_excel_root() -> str:
    """Prefer bundled/static folder when it contains spreadsheets; else legacy OneDrive path."""
    local = toolboxweb_root() / "static" / "data" / "afc_sims"
    if local.is_dir():
        if any(local.rglob("*.xlsx")) or any(local.rglob("*.xls")):
            return str(local)
    return r"D:/onedrive/OneDrive - 上汽大众汽车有限公司/AFC车SIM卡/"


def list_files_with_filter(folder_path):
    results = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            filename = os.path.join(root, file)
            project = os.path.basename(root)
            results.append((filename, project))
    return results


def merge_sim_excel():
    folder_path = _afc_sim_excel_root()
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(
            f"电信 SIM 本地数据目录不存在: {folder_path}。"
            "可将 Excel 放入 toolboxweb/static/data/afc_sims/，或在内网使用原 OneDrive 目录。"
        )
    file_list = list_files_with_filter(folder_path)
    df_list = []
    for filename in file_list:
        df = pd.read_excel(filename[0])
        df['项目'] = filename[1]
        df_list.append(df)
    df = pd.concat(df_list, axis=0, ignore_index=True)
    df.drop(columns='客户名称', inplace=True)
    return df


def search_sim_data(iccid=None, msisdn=None, imsi=None):
    try:
        df = merge_sim_excel()
        df = df.astype(str)
        if iccid:
            if len(iccid) == 20:
                df_filed = df[df['ICCID(20位)'] == iccid]
            else:
                df_filed = df[df['ICCID'] == iccid]
            if df_filed.empty:
                search_result = {
                    'success': False,
                    'data': 'sim_card_not_found'
                }
            else:
                msisdn = df_filed['用户号码'].iloc[0]
                imsi = df_filed['L_IMSI'].iloc[0]
                project = df_filed['项目'].iloc[0]
                search_result = {
                    'success': True,
                    'data': {
                        'iccid': iccid,
                        'msisdn': msisdn,
                        'imsi': imsi,
                        '项目': project
                    }
                }
        elif msisdn:
            df_filed = df[df['用户号码'] == msisdn]
            iccid = df_filed['ICCID(20位)'].iloc[0]
            imsi = df_filed['L_IMSI'].iloc[0]
            project = df_filed['项目'].iloc[0]
            search_result = {
                'success': True,
                'data': {
                    'iccid': iccid,
                    'msisdn': msisdn,
                    'imsi': imsi,
                    '项目': project
                }
            }
        else:
            df_filed = df[df['L_IMSI'] == imsi]
            iccid = df_filed['ICCID(20位)'].iloc[0]
            msisdn = df_filed['用户号码'].iloc[0]
            project = df_filed['项目'].iloc[0]
            search_result = {
                'success': True,
                'data': {
                    'iccid': iccid,
                    'msisdn': msisdn,
                    'imsi': imsi,
                    '项目': project
                }
            }
    except Exception as e:
        search_result = {
            'success': False,
            'data': str(e),
        }
    return search_result