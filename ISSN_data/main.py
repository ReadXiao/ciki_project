import csv
import shutil

import urllib

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import log
import re
import filesys
from get_quote import getUrlParams, get_quote_mian
import time
import json
from lxml import etree
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


def set_parameter(dr, ISSN, start, end):
    log.logger.debug('设置参数')
    time.sleep(1)
    try:
        WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/dl/dd[3]/div[2]/input'))).send_keys(
            ISSN)
        # 输入开始年份
        WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
            (By.XPATH,
             '/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/div/input'))).send_keys(
            start)
        # 输入结束年份
        WebDriverWait(dr, 3, 0.5).until(EC.presence_of_element_located(
            (By.XPATH,
             '/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[2]/div/input'))).send_keys(
            end)
        element = dr.find_element_by_xpath(
            '/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/dl/dd[3]/div[2]/div[1]/div[2]/ul[3]/li[3]/a')
        dr.execute_script("arguments[0].click();", element)
        dr.execute_script("arguments[0].click();", element)
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
            (By.XPATH, '/html/body/div[3]/div[2]/div[2]/div[2]/form/div/div[1]/div[1]/span[1]'))).text
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


def getResponseAndPostData(driver):
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


def get_basic_inf_by_test(text):
    # //*[@id="gridTable"]/table/tbody/tr[1]
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
                quote = element.xpath('./td[6]/a/text()')
                url = element.xpath("""./td[2]/a/@href""")[0]
                basic_inf['num'] = int(num)
                basic_inf['url'] = url
                basic_inf['journal'] = journal.strip().encode("GB18030", 'ignore').decode("GB18030", "ignore")
                basic_inf['title'] = title.strip().encode("GB18030", 'ignore').decode("GB18030", "ignore")
                basic_inf['author'] = author.strip().replace(";", "；").replace("；；", "；").encode("GB18030", 'ignore').decode("GB18030", "ignore")
                basic_inf['quote'] = 0 if not quote else int(quote[0])
                basic_inf['send_time'] = send_time.strip().encode("GB18030", 'ignore').decode("GB18030", "ignore")
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
            dbname = get_url_params(basic_inf['url'], "dbname")
            filename = get_url_params(basic_inf['url'], "filename")
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
    log.logger.info('新增：' + str(all_add))
    return add_num


def get_page_info_in_this_journal(dr, journal, ISSN, start_page, start, end, journal_path):
    error2_path = './error/error2.csv'
    if not set_parameter(dr, ISSN, start, end):
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
    response_and_postData = getResponseAndPostData(dr)
    if response_and_postData:
        response = response_and_postData[0]
    else:
        return -1
    current_total_get = 0
    html = etree.HTML(response)
    searchSql = html.xpath("""//*[@id="sqlVal"]""")[0].attrib["value"]
    postData = response_and_postData[1]
    url_decode = urllib.parse.unquote(postData)
    params = url_decode.replace("IsSearch=true", "IsSearch=false&SearchSql={}&".format(searchSql))
    for this_page in range(start_page, pages_number+1):
        params = re.sub("CurPage=\d+", "CurPage={}".format(this_page), params)
        params = re.sub("RecordsCntPerPage=.", "RecordsCntPerPage={}".format(5), params)
        req = send_request(dr, url="https://kns.cnki.net/kns8/Brief/GetGridTableHtml", params=params)
        if req == -1:
            log.logger.debug('期刊:' + journal + ',第' + str(this_page) + '页爬取失败')
            filesys.write_file(error2_path, (journal, this_page, ISSN))
            return current_total_get
        get_pages_number = get_all_info_in_this_page_by_request(dr, req, journal, paper_num, journal_path)
        if get_pages_number == -1:
            log.logger.debug('期刊:' + journal + ',第' + str(this_page) + '页爬取失败')
            filesys.write_file(error2_path, (journal, this_page, ISSN))
            return current_total_get
        log.logger.debug('期刊:' + journal + ',第' + str(this_page) + '页，新增：' + str(get_pages_number))
        current_total_get += get_pages_number
    return current_total_get


def get_by_year(start, end, journal, ISSN, start_page, journal_path):
    time.sleep(0.2)
    dr = create_driver()
    dr.get(login_url)
    filesys.create_file(journal_path, ["序号", "篇名", "作者", "刊名", "发表时间", "被引", "自引", "外引", "文献总数", "状态"])
    this_journal_get_num = get_page_info_in_this_journal(dr, journal, ISSN, start_page, start, end, journal_path)
    if this_journal_get_num == -1:
        filesys.write_file('./error/error2.csv', (journal, 1, ISSN))
        dr.quit()
    else:
        log.logger.info('期刊:' + journal + ',新爬取文献数：' + str(this_journal_get_num))
        dr.quit()


def read_long_journals(deal_file_path):
    long_journals = list()
    with open(deal_file_path, 'r', encoding='gb18030', errors='ignore') as f:
        reader = csv.reader(line.replace('\0', '') for line in f)
        for row in reader:
            if not row:
                continue
            long_journals.append((row[0], row[1]))
    return long_journals


def read_error2(deal_file_path):
    long_journals = list()
    with open(deal_file_path, 'r', encoding='gb18030', errors='ignore') as f:
        reader = csv.reader(line.replace('\0', '') for line in f)
        for row in reader:
            if not row:
                continue
            if row[0] not in '期刊名':
                long_journals.append((row[0], row[1], row[2]))
    return long_journals


def read_error3(deal_file_path):
    read_error3 = list()
    with open(deal_file_path, 'r', encoding='gb18030', errors='ignore') as f:
        reader = csv.reader(line.replace('\0', '') for line in f)
        for row in reader:
            if not row:
                continue
            if row[0] not in '年份':
                read_error3.append((row[0],row[1],row[2], row[3],row[4],row[5],row[6],row[7],row[8], row[9],row[10],row[11]))
    return read_error3


def get_Issn(start, end):
    deal_file_path = 'error/error_journals.csv'
    long_journals = read_long_journals(deal_file_path)
    for long_journal in long_journals:
        journal = long_journal[0]
        cu_jo = journal.replace(":", "-")  # 期刊名中一些特殊符号在创建文件的时候替换
        cu_jo = cu_jo.replace("/", "-")
        journal_path = "./data/" + cu_jo + ".csv"
        get_by_year(start, end, long_journal[0], long_journal[1], 1, journal_path)


def get_error2(count, start, end):
    deal_file_path = './error/error2.csv'
    long_journals = read_long_journals(deal_file_path)
    while long_journals and count > 0:
        date = time.strftime("%Y-%m-%d_%H-%M-%S")
        log_path = './error/error2_log/' + date + "_error2.csv"
        shutil.move(deal_file_path, log_path)
        filesys.create_file('error/error2.csv', ['期刊名', '页号', 'ISSN'])
        count -= 1
        for long_journal in long_journals:
            cu_jo = long_journal[0].replace(":", "-")  # 期刊名中一些特殊符号在创建文件的时候替换
            cu_jo = cu_jo.replace("/", "-")
            journal_path = "./data/" + cu_jo + ".csv"
            get_by_year(start, end, long_journal[0], long_journal[2], long_journal[1], journal_path)
        long_journals = read_long_journals(deal_file_path)


def get_error3(count):
    deal_file_path = './error/error3.csv'
    error3_list = read_error3(deal_file_path)
    dr = create_driver()
    while error3_list and count > 0:
        count -= 1
        date = time.strftime("%Y-%m-%d_%H-%M-%S")
        log_path = './error/error3_log/' + date + "_error3.csv"
        shutil.move(deal_file_path, log_path)
        filesys.create_file('error/error3.csv',
                            ["序号", "篇名", "作者", "刊名", "发表时间", "被引", "自引", "外引", "文献总数", "数据库编码", "数据库名", "文件编号"])
        for error3_info in error3_list:
            journal_path = "./long_data/" + error3_info[3]
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
        error3_list = read_error3(deal_file_path)
    dr.quit()


if __name__ == "__main__":
    login_url = 'https://kns.cnki.net/kns8/AdvSearch?dbcode=CJFQ'
    filesys.create_file('error/error2.csv', ['期刊名', '页号', 'ISSN'])
    filesys.create_file('error/error3.csv',["序号", "篇名", "作者", "刊名", "发表时间", "被引", "自引", "外引", "文献总数", "数据库编码", "数据库名", "文件编号"])
    start = 2019
    end = 2020
    get_Issn(start, end)
    get_error2(30, start, end)
    get_error3(10)
