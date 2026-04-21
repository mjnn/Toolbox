import time
import win32com.client
import re
import pythoncom


def get_vcode_list():
    pythoncom.CoInitialize()
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    count = 0
    while True:
        inbox = outlook.GetDefaultFolder(6)
        eidpVcodeFolder = inbox.Folders("邮箱验证码").Folders("eidp二次验证验证码")
        allMessages = eidpVcodeFolder.Items
        allMessages.Sort("[ReceivedTime]", True)
        messages = []
        # 取前十条
        for i, message in enumerate(allMessages):
            if i >= 10:
                break
            messages.append(message)
        unreadMessages = []
        # 取未读
        for message in messages:
            if message.Unread:
                unreadMessages.append(message)
                message.Unread = False
        # 如没有未读就等2秒再检查一遍
        if not unreadMessages:
            time.sleep(2)
            count = count + 1
            if count == 5:
                unreadMessageList = []
                app = messages[0].Subject[18:]
                vcode = re.findall(r'验证码[::]\s*(\d{6})', messages[0].body)[0]
                unreadMessageDict = {
                    '应用': app,
                    '验证码': vcode
                }
                unreadMessageList.append(unreadMessageDict)
                break
            continue
        else:
            unreadMessageList = []
            for unreadMessage in unreadMessages:
                app = unreadMessage.Subject[18:]
                vcode = re.findall(r'验证码[::]\s*(\d{6})', unreadMessage.body)[0]
                unreadMessageDict = {
                    '应用': app,
                    '验证码': vcode
                }
                unreadMessageList.append(unreadMessageDict)
            break
    return unreadMessageList