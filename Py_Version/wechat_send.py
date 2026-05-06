import os
import configparser
import platform

if platform.system() == 'Windows':
    from wxauto import WeChat
    from comtypes.gen.UIAutomationClient import IUIAutomation

def sending_pics():
    import platform
    if platform.system() != 'Windows':
        print("微信发送功能仅支持 Windows 系统，macOS/Linux 上已跳过此任务。")
        print("生成的图片已保存在 ./pic/ 目录中，请手动发送。")
        return

    path = os.getcwd()
    path = os.path.join(path, 'pic')

    # print(path)

    # 自动发送图片
    config = configparser.ConfigParser()
    config.read("config.ini", encoding = "utf-8")
    if config.has_option("Sending", "pic") and config.has_option("Sending", "whos"):
        print("检测到您已进行发送默认配置，开始运行发送任务！！")
        pics = config.get("Sending", "pic").strip().split("|")
        # 只选择一张图
        if len(pics) == 1:
            files = os.path.join(path, pics[0])
            # print(files)

        # 选择一张图以上
        else:
            files = [
                os.path.join(path, pic) for pic in pics # need absolute path
            ]

        whos = config.get("Sending", "whos").strip().split("|")
        wx = WeChat()
        for who in whos:
            wx.SendFiles(filepath = files, who = who)

    else:
    # 手动发送图片
        plot_list = [
            'eia_tab.png',
            'eia_pic.png',
            'eia.png']


        plot_no = input("请选择您要发送的图片序号（可多选）1.表格图 2.季节图 3.合并后的图：")

        while len(plot_no) < 1:
            plot_no = input("请选择您要发送的图片序号（可多选）1.表格图 2.季节图 3.合并后的图：")

        # 只选择一张图
        if len(plot_no) == 1:
            files = os.path.join(path, plot_list[int(plot_no) - 1])
            # print(files)

        # 选择一张图以上
        else:
            plot_no = list(plot_no.replace(" ", ""))
            plot_no = list(set(map(int, plot_no)))
            plot_list = [plot_list[i-1] for i in plot_no]
            files = [
                os.path.join(path, p_list) for p_list in plot_list # need absolute path
            ]

        whos = input("请输入您要发送的联系人或群名称，多个请用空格分隔：").split()
        wx = WeChat()
        for who in whos:
            # print(who)
            wx.SendFiles(filepath = files, who = who)

        print("图片发送完成！！")