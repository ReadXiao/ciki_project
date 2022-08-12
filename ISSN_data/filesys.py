# 姓   名：xhw
# 开发时间：2021/12/15 20:35
import csv
import os
import shutil


def create_file(filename, file_format):
    with open(filename, 'w', encoding='gb18030', newline='') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(file_format)
        f.close()


def write_file(filename, row):
    with open(filename, 'a+', encoding='gb18030', newline='') as f:  # 创建目标文件
        csv_writer = csv.writer(f)
        csv_writer.writerow(row)
        f.close()
