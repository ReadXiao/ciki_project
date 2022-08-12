# 姓   名：xhw
# 开发时间：2021/12/15 20:36
import re
import json
import time
from urllib.parse import urlparse, parse_qs
from lxml import etree
from selenium.webdriver.common.by import By
# 得到引证文献html和URL
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import log


def getResponseAndURL(driver):
    for typelog in driver.log_types:
        perfs = driver.get_log(typelog)
        for row in perfs:
            log_data = row
            try:
                log_json = json.loads(log_data['message'])
                log = log_json['message']
                if log['method'] == 'Network.responseReceived':
                    requestId = log['params']['requestId']
                    type = log["params"]["type"]
                    url = log["params"]["response"]["url"]
                    regex_person_document = re.compile(
                        r'https://kns.cnki.net/kcms/detail/frame/list.aspx\?dbcode=[^\s]*&filename=[^\s]*&dbname=['
                        r'^\s]*&RefType=3&vl=[^\s]*')
                    if regex_person_document.findall(url) and type == 'Document':
                        try:
                            response_body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': requestId})
                            data = response_body['body']
                            return [str(data), url]
                        except:
                            # log.logger.error('response.body is null')
                            return None
            except:
                # log.logger.warn("log_data['message'] not json")
                return None


# 获取json数据
def getData(driver, dbcode, dbname, filename, curdbcode, totalCite, vl):
    url = "https://kns.cnki.net/kcms/detail/frame/json.aspx?dbcode={}&dbname={}&filename={}&curdbcode={" \
          "}&page=1&reftype=3&pl={}&vl={}".format(
        dbcode, dbname, filename, curdbcode, totalCite, vl)
    try:
        driver.get(url)
    except:
        return None
    else:
        # 获取页面源代码
        pageSource = driver.page_source
        eleRoot = etree.HTML(pageSource)
        # jsonDataStr = eleRoot.xpath("/html/body/pre")[0].text
        jsonData = eleRoot.xpath("/html/body/pre")
        if not jsonData:
            return None
        else:
            jsonDataStr = jsonData[0].text
        jsonDataStr = jsonDataStr.replace("\"", " ")
        jsonDataStr = jsonDataStr.replace("\\", "/")
        jsonDataStr = jsonDataStr.replace("/\'", " ")
        jsonDataStr = jsonDataStr.replace("\'", "\"")
        try:
            jsonData = json.loads(jsonDataStr)
        except json.decoder.JSONDecodeError:
            return None
        else:
            rows = jsonData['Rows']
        return rows


def start(driver, dbcode, dbname, filename):
    # 请求原始文献详情网页，得到原始文献作者信息
    driver.execute_script("window.open();")  # 注意js语句要带分号
    url = "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode={}&dbname={}&filename={}".format(dbcode, dbname,
                                                                                                filename)
    try:
        driver.get(url)
    except:
        return None
    else:
        handles = driver.window_handles
        driver.switch_to_window(handles[1])
    return driver


def getUrlParams(url, name):
    url_obj = urlparse(url)
    query_obj = parse_qs(url_obj.query)
    # log.logger.info(query_obj[name][0])
    return query_obj[name][0]


def get_original_info(driver):
    # 获取作者姓名
    try:
        time.sleep(1)
        pageSource = etree.HTML(driver.page_source)
        au_elements = pageSource.xpath('/html/body/div[2]/div[1]/div[3]/div/div/div[3]/div/h3[1]//span')
        au_code = list()
        for element in au_elements:
            au_code_element = element.xpath('./input/@value')
            if au_code_element:
                au_code.append((au_code_element[0].split(';'))[0])
            else:
                au_code.append(element.xpath('./text()'))
        return au_code
    except:
        return -1


def get_quote_info(driver):
    # 获取引证文献JSON数据
    try:
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight/2)')
        time.sleep(1)
        nextPageButton = WebDriverWait(driver, 3, 0.5).until(
            EC.element_to_be_clickable((By.XPATH, """//li[text()="引证文献"]""")))
        nextPageButton.click()
    except Exception as e:
        log.logger.info('引证文献点击失败！')
        return None
        # log.logger.info(e)
    else:
        time.sleep(2)
        responseBodyAndURL = getResponseAndURL(driver)
        if responseBodyAndURL:
            responseBody = responseBodyAndURL[0]
            citeURL = responseBodyAndURL[1]
            eleRoot = etree.HTML(responseBody)
            countSpans = eleRoot.xpath("""//span[@name="pcount"]""")
            # groups = re.findall('共<span name="pcount" id="pc_IPFD">1</span>条', str(responseBody))
            res = []
            dbcode = getUrlParams(citeURL, "dbcode")
            dbname = getUrlParams(citeURL, "dbname")
            filename = getUrlParams(citeURL, "filename")
            vl = getUrlParams(citeURL, "vl")
            for countSpan in countSpans:
                totalCite = countSpan.text
                curdbcode = countSpan.attrib["id"][3:]
                res.append(getData(driver, dbcode, dbname, filename, curdbcode, totalCite, vl))
            return res
        else:
            return None


def get_quote_num(box_info, original_info):
    # 解析JSON数据,并与原始作者比较，计算自引证文献数
    res = 0
    for essays in box_info:
        if essays:
            for essay in essays:
                try:
                    au_code_text = essay['AU_CODE'].split(';')
                    au_code = au_code_text[:-1]
                except KeyError:
                    au_code_text = (essay['AU_CN'].split(';'))  # 有可能不存在AU_CODE
                    au_code = au_code_text[:-1]
                if au_code:
                    for code in au_code:
                        if code in original_info:
                            res += 1
                            break
        else:
            break
    return res


def get_quote_mian(driver, dbcode, dbname, filename):
    # 获得网页驱动器
    url = "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode={}&dbname={}&filename={}".format(dbcode, dbname,
                                                                                                filename)
    try:
        driver.execute_script("window.open(arguments[0]);", url)  # 注意js语句要带分号
        # driver.get(url)
        time.sleep(2)
        handles = driver.window_handles
        driver.switch_to.window(handles[1])
    except:
        log.logger.info('网络异常，去自引失败')
        return -1
    else:
        original_info = get_original_info(driver)
        if  original_info == -1:
            log.logger.info('去自引,作者信息获取为空！')
            return -1
        # log.logger.info(original_info)
        quote_info = get_quote_info(driver)
        if not quote_info:
            driver.close()
            driver.switch_to_window(handles[0])
            return -1
        self_quote_num = get_quote_num(quote_info, original_info)
        driver.close()
        driver.switch_to_window(handles[0])
        return self_quote_num

# https://kns.cnki.net/kcms/detail/frame/json.aspx?dbcode=CJFD&dbname=CJFDLAST2019&filename=sccx201903002&curdbcode=CJFQ&page=1&reftype=3&pl=1&vl=bfZRH_l9m3wMRzCLbqFoMFIFrovFXzYqmY-gCPxNDWGCpBOacs2H-rSqNc0_VZ3N
# https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&dbname=CJFDLAST2019&filename=SCCX201903001&uniplatform=NZKPT&v=UEdxGbP4WcWk1IMXVYNPMwlW724J6myjlz%25mmd2Fu4ZaoQ0JL9BJJ%25mmd2B0MGuYAGz1UufsFA
