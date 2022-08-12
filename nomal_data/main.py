import csv
import json
import os
import shutil
import urllib
from lxml import etree
import xlrd
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import log
import re
import filesys
from get_quote import get_quote_mian
import time
from urllib.parse import urlparse, parse_qs


def get_url_params(url, name):
    url_obj = urlparse(url)
    query_obj = parse_qs(url_obj.query)
    return query_obj[name][0]


def create_driver():
    caps = DesiredCapabilities.CHROME
    caps['loggingPrefs'] = {
        'browser': 'ALL',
        'performance': 'ALL',
    }
    caps['perfLoggingPrefs'] = {
        'enableNetwork': True,
        'enablePage': False,
        'enableTimeline': False
    }
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument("–incognito")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("blink-setting=imagesEnable=false")
    options.add_argument('--disable-gpu')
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-single-click-autofill")
    options.add_argument("--disable-autofill-keyboard-accessory-view[8]")
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    options.add_argument(
        'user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/91.0.4280.88 Safari/537.36"')
    options.add_experimental_option('w3c', False)
    options.add_experimental_option('perfLoggingPrefs', {
        'enableNetwork': True,
        'enablePage': False,
    })
    dr = webdriver.Chrome(options=options, desired_capabilities=caps)
    with open('./stealth.min.js') as f:
        js = f.read()
    dr.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": js
    })
    return dr


def set_parameter(dr, journal, start, end):
    log.logger.debug('设置参数')
    time.sleep(1)
    try:
        WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/dl/dd[3]/div[2]/input'))).send_keys(
            journal)
        # 介绍4中操作方法
        data0 = "$('input[id=datebox0]').removeAttr('readonly')"  # 2.jQuery，移除属性
        dr.execute_script(data0)
        dr.find_element_by_id('datebox0').send_keys(start)
        time.sleep(1)
        data1 = "$('input[id=datebox1]').removeAttr('readonly')"  # 4.jQuery，设置为空（同3）
        dr.execute_script(data1)
        dr.find_element_by_id('datebox1').send_keys(end)
        time.sleep(1)
        WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/input[2]'))).click()

        # 点击检索
        WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/div[2]/input'))).click()
    except Exception as e:
        # print(e)
        return False
    else:
        return True


def get_number_info(dr):
    try:
        time.sleep(2)
        paper_num = WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[3]/div[2]/div[2]/div[2]/form/div/div[1]/div[1]/span[1]/em'))).text
        try:
            pages_str = WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
                (By.XPATH, '/html/body/div[3]/div[2]/div[2]/div[2]/form/div/div[1]/div[1]/span[2]'))).text
            pages_str = pages_str[2:]
        except:
            pages_str = '1'
    except:
        return None
    else:
        paper_num = int(re.sub(r'\D', "", paper_num))
        # log.logger.info('共有' + str(paper_num) + '篇文献')
        pages_number = int(re.sub(r'\D', "", pages_str))
        # log.logger.info('共有' + str(pages_number) + '页')
        return paper_num, pages_number


def get_response_and_post_data(driver):
    for typelog in driver.log_types:
        perfs = driver.get_log(typelog)
        for row in perfs:
            log_data = row
            if log_data['level'] == 'WARNING':
                continue
            try:
                log_json = json.loads(log_data["message"])
            except Exception as ex:
                continue
            log = log_json['message']
            if log['method'] == 'Network.responseReceived':
                requestId = log['params']['requestId']
                type = log["params"]["type"]
                if type != "XHR":
                    continue
                url = log["params"]["response"]["url"]
                regex_person_document = re.compile(
                    r'https://kns.cnki.net/kns8/Brief/GetGridTableHtml')
                if regex_person_document.findall(url):
                    try:
                        response_body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': requestId})
                        request_form_data = driver.execute_cdp_cmd("Network.getRequestPostData",
                                                                   {'requestId': requestId})
                        data = response_body['body']
                        post_data = str(request_form_data["postData"])
                        return [data, post_data]
                    except Exception as ex:
                        ex.with_traceback()
                        return None


def send_request(driver, url, params, method='POST'):
    if method == 'GET':
        parm_str = ''
        for key, value in params.items():
            parm_str = parm_str + key + '=' + str(value) + '&'
        if parm_str.endswith('&'):
            parm_str = '?' + parm_str[:-1]
        driver.get(url + parm_str)
    else:
        jquery = open("jquery-3.6.0.min.js", "r").read()
        driver.execute_script(jquery)
        ajax_query = '''
                       $.ajax('%s', {
                       type: '%s',
                       data: '%s', 
                       crossDomain: true,
                       xhrFields: {
                        withCredentials: true
                       },
                       success: function(){}
                       });
                       ''' % (url, method, params)
        try:
            ajax_query = ajax_query.replace(" ", "").replace("\n", "")
            resp = driver.execute_script("return " + ajax_query)
            return resp
        except:
            return -1


def get_basic_inf_by_dr(dr, k):
    basic_inf = {}
    get_path = "/html/body/div[3]/div[2]/div[2]/div[2]/form/div/table/tbody/tr[" + str(k) + "]"
    try:
        info_element = WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, get_path)))
    except:
        log.logger.info('1、页面信息获取失败！')
        return -1
    else:
        try:
            num = info_element.find_element_by_xpath('./td[1]').text
            title = info_element.find_element_by_xpath('./td[2]').text
            author = info_element.find_element_by_xpath('./td[3]').text
            journal = info_element.find_element_by_xpath('./td[4]').text
            send_time = info_element.find_element_by_xpath('./td[5]').text
            quote = info_element.find_element_by_xpath('./td[7]').text
            url = info_element.find_element_by_xpath('./td[2]/a').get_attribute('href')
        except:
            log.logger.info('2、页面信息获取失败！')
            return -1
        basic_inf['num'] = num
        basic_inf['url'] = url
        basic_inf['journal'] = journal
        basic_inf['title'] = title
        basic_inf['author'] = author.replace(';', '；').replace(';;', '；').replace('；；', '；')
        basic_inf['quote'] = 0 if not quote else int(quote)
        basic_inf['send_time'] = send_time
        return basic_inf


def get_all_info_in_this_page(dr, paper_num_this_page, journal, paper_num, journal_path):
    get_pages_number = 0
    time.sleep(4)  # 调试过程中，这里断点，爬完整个期刊未出现反爬的情况，因此给加个延迟
    basic_inf_test = get_basic_inf_by_dr(dr, 1)
    if basic_inf_test == -1:
        # 如果第一条信息都获取失败，代表该页面没有进入
        return -1
    for i in range(1, paper_num_this_page + 1):
        basic_inf = get_basic_inf_by_dr(dr, i)
        if basic_inf == -1:
            return -1
        if basic_inf['quote'] > 0:
            dbcode = get_url_params(basic_inf['url'], "DbCode")
            dbname = get_url_params(basic_inf['url'], "DbName")
            filename = get_url_params(basic_inf['url'], "FileName")
            self_quote_num = get_quote_mian(dr, dbcode, dbname, filename)
            if self_quote_num == -1:  # 文献引证文献信息获取失败，记录错误日志
                filesys.write_file('./error/error3.csv',
                                   (basic_inf['num'],
                                    basic_inf['title'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
                                    basic_inf['author'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
                                    journal,
                                    basic_inf['send_time'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
                                    basic_inf['quote'],
                                    -1,
                                    -1,
                                    paper_num, dbcode, dbname, filename))
                continue
            else:
                get_pages_number += 1
                # 去自引成功自引数赋值
                basic_inf['self_quote_num'] = self_quote_num
        else:
            get_pages_number += 1
            # 引用数为0，自引数为0
            basic_inf['self_quote_num'] = 0
        save_inf = (
            basic_inf['num'],
            basic_inf['title'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
            basic_inf['author'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
            basic_inf['journal'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
            basic_inf['send_time'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
            basic_inf['quote'],
            basic_inf['self_quote_num'],
            basic_inf['quote'] - basic_inf['self_quote_num'],
            paper_num
        )
        filesys.write_file(journal_path, save_inf)
    return get_pages_number


def get_all_info_in_this_journal(dr, journal, start, end, journal_path):
    if not set_parameter(dr, journal, start, end):
        log.logger.debug(journal + '：期刊参数设置失败')
        return -1
    try:
        time.sleep(2)
        element = dr.find_element_by_xpath(
            '/html/body/div[3]/div[2]/div[2]/div[2]/form/div/div[1]/div[2]/div[2]/div/div/ul/li[3]/a')
        dr.execute_script("arguments[0].click();", element)
        dr.execute_script("arguments[0].click();", element)
    except:
        log.logger.info(journal + '：期刊数据获取失败，没有表格控件！')
        return -1
    time.sleep(3)
    num_info = get_number_info(dr)
    paper_num = -1
    pages_number = -1
    if num_info:
        paper_num = num_info[0]
        pages_number = num_info[1]
    else:
        log.logger.info(journal + '：期刊数据获取失败，文献数量信息获取失败！')
        return -1
    current_total_get = 0
    for this_page in range(1, pages_number + 1):  # 前闭后开
        # 第1页不需要点击下一页
        get_pages_number = 0
        if this_page != 1:
            try:
                time.sleep(1)
                WebDriverWait(dr, 5, 0.5).until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="PageNext"]'))).click()
                time.sleep(2)
            except:
                # 下一页点击失败
                log.logger.debug('期刊:' + journal + ',第' + str(this_page) + '页爬取失败')
                filesys.write_file('./error/error2.csv', (journal, this_page))
                return current_total_get
        if this_page == pages_number:  # 最后一页文献数不足20
            get_pages_number = get_all_info_in_this_page(dr, paper_num - ((this_page - 1) * 50), journal, paper_num, journal_path)
        else:
            get_pages_number = get_all_info_in_this_page(dr, 50, journal, paper_num, journal_path)
        if get_pages_number == -1 and this_page == 1:
            # 如果第一页的信息都没有获取成功，代表这个期刊搜索失败
            log.logger.info(journal + '：第一页数据信息获取失败，期刊获取失败！')
            return -1
        # get_pages_number为-1代表页面没加载到页面信息
        elif get_pages_number == -1:
            log.logger.debug('期刊:' + journal + ',第' + str(this_page) + '页爬取失败')
            filesys.write_file('./error/error2.csv', (journal, this_page))
            return current_total_get
        current_total_get += get_pages_number
    return current_total_get


def get_basic_inf_by_test(text):
    all_basic_inf = list()
    try:
        html = etree.HTML(text)
        info_element = html.xpath('//tr')
        if info_element:
            for element in info_element[1:]:
                basic_inf = {}
                num = element.xpath('./td[1]/text()')[0]
                title = element.xpath('./td[2]/a/text()')[0]
                authors = element.xpath('./td[3]//a/text()')
                author = ""
                if not authors:
                    author = element.xpath('./td[3]/text()')[0]
                else:
                    for e in element.xpath('./td[3]//a/text()'):
                        author = author + e + "；"
                    author = author[:-1]
                journals = element.xpath('./td[4]/a/font/text()')
                if not journals:
                    journals = element.xpath('./td[4]/a/text()')
                if not journals:
                    journals = element.xpath('./td[4]/font/text()')
                if not journals:
                    journals = element.xpath('./td[4]/text()')
                journal = ""
                for e in journals:
                    journal = journal + e + ' '
                journal = journal[:-1]
                send_time = element.xpath('./td[5]/text()')[0]
                quote = element.xpath('./td[7]/span/a/text()')
                url = element.xpath("""./td[2]/a/@href""")[0]
                basic_inf['num'] = int(num)
                basic_inf['url'] = url
                basic_inf['journal'] = journal.strip()
                basic_inf['title'] = title.strip().encode("GB18030", 'ignore').decode("GB18030", "ignore")
                basic_inf['author'] = author.strip().replace(";", "；")
                basic_inf['quote'] = 0 if not quote else int(quote[0])
                basic_inf['send_time'] = send_time.strip()
                all_basic_inf.append(basic_inf)
            return all_basic_inf
        else:
            return -1
    except:
        return -1


def get_all_info_in_this_page_by_request(dr, req, journal, paper_num, journal_path):
    add_num = 0
    all_add = 0
    all_basic_info = get_basic_inf_by_test(req)
    if all_basic_info == -1:
        return -1
    for i in range(0, len(all_basic_info)):
        basic_inf = all_basic_info[i]
        if basic_inf['quote'] > 0:
            dbcode = get_url_params(basic_inf['url'], "DbCode")
            dbname = get_url_params(basic_inf['url'], "DbName")
            filename = get_url_params(basic_inf['url'], "FileName")
            self_quote_num = get_quote_mian(dr, dbcode, dbname, filename)
            if self_quote_num == -1:  # 文献引证文献信息获取失败
                log.logger.info('--------------------去自引失败！')
                filesys.write_file('./error/error3.csv',
                                   (basic_inf['num'],
                                    basic_inf['title'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
                                    basic_inf['author'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
                                    journal.encode("GB18030", 'ignore').decode("GB18030", "ignore"),
                                    basic_inf['send_time'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
                                    basic_inf['quote'],
                                    -1,
                                    -1,
                                    paper_num, dbcode, dbname, filename))
                continue
            else:
                add_num += 1
                all_add += 1
                basic_inf['self_quote_num'] = self_quote_num
        else:
            add_num += 1
            all_add += 1
            basic_inf['self_quote_num'] = 0
        filesys.write_file(journal_path, (
            basic_inf['num'],
            basic_inf['title'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
            basic_inf['author'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
            basic_inf['journal'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
            basic_inf['send_time'].encode("GB18030", 'ignore').decode("GB18030", "ignore"),
            basic_inf['quote'],
            basic_inf['self_quote_num'],
            basic_inf['quote'] - basic_inf['self_quote_num'],
            paper_num
        ))
    log.logger.info('新增：'+str(all_add))
    return add_num


def get_page_info_in_this_journal(dr, journal, start_page, start, end, journal_path):
    if not set_parameter(dr, journal, start, end):
        log.logger.debug(journal + '：期刊参数设置失败')
        return -1
    try:
        time.sleep(2)
        element = dr.find_element_by_xpath(
            '/html/body/div[3]/div[2]/div[2]/div[2]/form/div/div[1]/div[2]/div[2]/div/div/ul/li[3]/a')
        dr.execute_script("arguments[0].click();", element)
        dr.execute_script("arguments[0].click();", element)
    except:
        log.logger.info(journal + '：期刊数据获取失败，没有表格控件！')
        return -1
    time.sleep(3)
    num_info = get_number_info(dr)
    paper_num = -1
    pages_number = -1
    if num_info:
        paper_num = num_info[0]
        pages_number = num_info[1]
    else:
        log.logger.info(journal + '：期刊数据获取失败，文献数量信息获取失败！')
        return -1
    response_and_post_data = get_response_and_post_data(dr)
    if response_and_post_data:
        response = response_and_post_data[0]
    else:
        return -1
    current_total_get = 0
    html = etree.HTML(response)
    search_sql = html.xpath("""//*[@id="sqlVal"]""")[0].attrib["value"]
    post_data = response_and_post_data[1]
    url_decode = urllib.parse.unquote(post_data)
    params = url_decode.replace("IsSearch=true", "IsSearch=false&SearchSql={}&".format(search_sql))
    for this_page in range(start_page, pages_number + 1):
        time.sleep(0.5)
        params = re.sub("CurPage=\d+", "CurPage={}".format(this_page), params)
        params = re.sub("RecordsCntPerPage=.", "RecordsCntPerPage={}".format(5), params)
        req = send_request(dr, url="https://kns.cnki.net/kns8/Brief/GetGridTableHtml", params=params)
        if req == -1:
            log.logger.debug('期刊:' + journal + ',第' + str(this_page) + '页爬取失败')
            filesys.write_file('./error/error2.csv', (journal, this_page))
            return current_total_get
        get_pages_number = get_all_info_in_this_page_by_request(dr, req, journal, paper_num, journal_path)
        if get_pages_number == -1:
            log.logger.debug('期刊:' + journal + ',第' + str(this_page) + '页爬取失败')
            filesys.write_file('./error/error2.csv', (journal, this_page))
            return current_total_get
        log.logger.debug('期刊:' + journal + ',第' + str(this_page) + '页，新增：' + str(get_pages_number))
        current_total_get += get_pages_number
    return current_total_get


def get_journal(start, end, start_time, end_time, table):
    filesys.create_file('error/error1.csv', ['期刊名', ])
    filesys.create_file('error/error2.csv', ['期刊名', '页号'])
    filesys.create_file('error/error3.csv', ["序号", "篇名", "作者", "刊名", "发表时间", "被引", "自引", "外引", "文献总数", "数据库编码", "数据库名", "文件编号"])
    for row in range(start, end):
        time.sleep(1)
        journal = table.row_values(row)[0]
        dr = create_driver()
        try:
            dr.get(login_url)
        except:
            time.sleep(30)
            filesys.write_file('error/error1.csv', (journal,))
            dr.quit()
            continue
        log.logger.debug('开始爬取' + journal + '期刊')
        if table.row_values(row)[0] == 1:
            dr.quit()
            continue
        cu_jo = journal.replace(":", "-")  # 期刊名中一些特殊符号在创建文件的时候替换
        cu_jo = cu_jo.replace("/", "-")
        journal_path = "./data/" + cu_jo + ".csv"
        filesys.create_file(journal_path, ["序号", "篇名", "作者", "刊名", "发表时间", "被引", "自引", "外引", "文献总数"])
        this_journal_get_num = get_all_info_in_this_journal(dr, journal, start_time, end_time, journal_path)
        if this_journal_get_num == -1:
            os.remove(journal_path)
            filesys.write_file('error/error1.csv', (journal,))
            dr.quit()
            continue
        else:
            log.logger.debug('期刊' + journal + '爬取完成,共爬取文献：' + str(this_journal_get_num))
            dr.quit()


def get_error1(count, start_time, end_time):
    deal_file_path = './error/error1.csv'
    error1_list = read_error_1(deal_file_path)
    while error1_list:
        count -= 1
        date = time.strftime("%Y-%m-%d_%H-%M-%S")
        log_path = './error/error1_log/' + date + "_error1.csv"
        shutil.move(deal_file_path, log_path)
        filesys.create_file(deal_file_path, ['期刊名', ])
        for error1_info in error1_list:
            time.sleep(1)
            dr = create_driver()
            try:
                dr.get(login_url)
            except:
                time.sleep(30)
                filesys.write_file(deal_file_path, (error1_info,))
                dr.quit()
                continue
            cu_jo = error1_info.replace(":", "-")  # 期刊名中一些特殊符号在创建文件的时候替换
            cu_jo = cu_jo.replace("/", "-")
            journal_path = "./data/" + cu_jo + ".csv"
            filesys.create_file(journal_path, ["序号", "篇名", "作者", "刊名", "发表时间", "被引", "自引", "外引", "文献总数"])
            this_journal_get_num = get_all_info_in_this_journal(dr, error1_info, start_time, end_time, journal_path)
            if this_journal_get_num == -1:
                os.remove(journal_path)
                filesys.write_file(deal_file_path, (error1_info,))
                dr.quit()
                continue
            else:
                log.logger.debug('期刊' + error1_info + '爬取完成,共爬取文献：' + str(this_journal_get_num))
                dr.quit()
        error1_list = read_error_1(deal_file_path)
        if not error1_list or count == 0:
            break


def get_error2(count, start_time, end_time):
    deal_file_path = './error/error2.csv'
    error2_list = read_error_2(deal_file_path)
    while error2_list:
        count -= 1
        date = time.strftime("%Y-%m-%d_%H-%M-%S")
        log_path = './error/error2_log/' + date + "_error2.csv"
        shutil.move(deal_file_path, log_path)
        filesys.create_file(deal_file_path, ['期刊名', '页号'])
        for error2_info in error2_list:
            time.sleep(1)
            dr = create_driver()
            try:
                dr.get(login_url)
            except:
                time.sleep(30)
                filesys.write_file(deal_file_path, (error2_info[0], error2_info[1]))
                dr.quit()
                continue
            cu_jo = error2_info[0].replace(":", "-")  # 期刊名中一些特殊符号在创建文件的时候替换
            cu_jo = cu_jo.replace("/", "-")
            journal_path = "./data/" + cu_jo + ".csv"
            this_journal_get_num = get_page_info_in_this_journal(dr, error2_info[0], int(error2_info[1]), start_time, end_time, journal_path)
            if this_journal_get_num == -1:
                filesys.write_file(deal_file_path, (error2_info[0], error2_info[1]))
                dr.quit()
                continue
            else:
                log.logger.debug('期刊' + error2_info[0] + '爬取完成,共爬取文献：' + str(this_journal_get_num))
                dr.quit()
        error2_list = read_error_2(deal_file_path)
        if not error2_list or count == 0:
            break


def get_error3(count):
    deal_file_path = './error/error3.csv'
    error3_list = read_error_3(deal_file_path)
    dr = create_driver()
    while error3_list:
        count -= 1
        date = time.strftime("%Y-%m-%d_%H-%M-%S")
        log_path = './error/error3_log/' + date + "_error3.csv"
        shutil.move(deal_file_path, log_path)
        filesys.create_file('error/error3.csv',
                            ["序号", "篇名", "作者", "刊名", "发表时间", "被引", "自引", "外引", "文献总数", "数据库编码", "数据库名", "文件编号"])
        for error3_info in error3_list:
            cu_jo = error3_info[3].replace(":", "-")
            cu_jo = cu_jo.replace("/", "-")
            journal_path = "./data/" + cu_jo + ".csv"
            self_quote = get_quote_mian(dr, error3_info[9], error3_info[10], error3_info[11])
            if self_quote == -1:
                log.logger.debug('期刊：' + error3_info[3] + '，文献：' + error3_info[1] + "去自引失败！！！")
                filesys.write_file(deal_file_path,
                                   (error3_info[0], error3_info[1], error3_info[2], error3_info[3], error3_info[4],
                                    error3_info[5], error3_info[6], error3_info[7], error3_info[8], error3_info[9],
                                    error3_info[10], error3_info[11]))
            else:
                save_inf = (
                    error3_info[0],
                    error3_info[1],
                    error3_info[2],
                    error3_info[3],
                    error3_info[4],
                    error3_info[5],
                    self_quote,
                    int(error3_info[5]) - self_quote,
                    error3_info[8]
                )
                log.logger.debug('期刊：' + error3_info[3] + '，文献：' + error3_info[1] + "去自引成功！")
                filesys.write_file(journal_path, save_inf)
        log.logger.debug('---------------------------------------------------------------')
        error3_list = read_error_3(deal_file_path)
        if not error3_list or count == 0:
            break
    dr.quit()


def read_error_1(deal_file_path):
    error1_list = list()
    with open(deal_file_path, 'r', encoding='gb18030', errors='ignore') as f:
        reader = csv.reader(line.replace('\0', '') for line in f)
        for row in reader:
            if not row:
                continue
            if row[0] not in '期刊名':
                error1_list.append(row[0])
    return error1_list


def read_error_2(deal_file_path):
    error2_list = list()
    with open(deal_file_path, 'r', encoding='gb18030', errors='ignore') as f:
        reader = csv.reader(line.replace('\0', '') for line in f)
        for row in reader:
            if not row:
                continue
            if row[0] not in '期刊名':
                error2_list.append((row[0], row[1]))
    return error2_list


def read_error_3(deal_file_path):
    read_error3 = list()
    with open(deal_file_path, 'r', encoding='gb18030', errors='ignore') as f:
        reader = csv.reader(line.replace('\0', '') for line in f)
        for row in reader:
            if not row:
                continue
            if row[0] not in '序号':
                read_error3.append(
                    (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11]))
    return read_error3


if __name__ == "__main__":
    login_url = "https://kns.cnki.net/kns8/AdvSearch?dbprefix=SCDB&&crossDbcodes=CJFQ%2CCDMD%2CCIPD%2CCCND%2CCISD%2CSNAD%2CBDZK%2CCCJD%2CCCVD%2CCJFN"
    # 待爬取文献列表
    file = xlrd.open_workbook('102data.xlsx')
    table = file.sheets()[0]
    # 0,33  待爬取文件的序列号范围   start, end 待爬取文献时间区间
    start = "2019-01-01"
    end = "2020-12-31"
    get_journal(0, 7, start, end, table)
    # 10 错误1重复处理10次
    get_error1(10, start, end)
    # 错误2 重复处理30次
    get_error2(30, start, end)
    # 错误3 重复处理10次
    get_error3(10)

