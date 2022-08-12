# 姓   名：xhw
# 开发时间：2021/12/15 20:38
import logging

# 第一步：创建Logger并进行设置
logger = logging.getLogger('applog')
logger.setLevel(logging.DEBUG)

# 第二步：创建Handler并设置
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

ch1 = logging.FileHandler('logging.log')
ch1.setLevel(logging.DEBUG)

# 第三步：创建Formatter
datefmt = "%a %d %b %Y %H:%M:%S"
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt)
datefmt = "%a %d %b %Y %H:%M:%S"
# 第四步：将Formatter添加到Handler
ch.setFormatter(formatter)
ch1.setFormatter(formatter)

# 第五步：将Handler添加到Logger
logger.addHandler(ch)
logger.addHandler(ch1)
