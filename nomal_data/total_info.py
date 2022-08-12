import pandas as pd
import os
import numpy as np


def out_get(path, files):
    total_papers_list = []
    quote_papers_list = []
    rate_list = []
    paper_name = []
    for file in files:
        data_frame = pd.read_csv(path + '\\' + file, encoding='gb18030')
        total_papers = data_frame['文献总数'].values[0]
        have_papers = data_frame.shape[0]  # 已爬取文献总数
        quote_papers = data_frame['外引'].sum()
        rate = quote_papers / total_papers
        total_papers_list.append(total_papers)
        quote_papers_list.append(quote_papers)
        paper_name.append(file[:-4])
        rate_list.append(rate)
    print(len(paper_name))
    df = pd.DataFrame()
    df['文献名'] = paper_name
    df['总文献数'] = total_papers_list
    df['外引文献数'] = quote_papers_list
    df['比率'] = rate_list
    df.to_excel("文献外引统计信息.xlsx", index=0)


def get_total_info(path, files):
    total_papers_list = []
    have_papers_list = []
    rate_list = []
    paper_name = []
    for file in files:
        data_frame = pd.read_csv(path + '\\' + file, encoding='gb18030')
        total_papers = data_frame['文献总数'].values[0]
        have_papers = data_frame.shape[0]
        rate = have_papers / total_papers
        total_papers_list.append(total_papers)
        have_papers_list.append(have_papers)
        paper_name.append(file[:-4])
        rate_list.append(rate)
    print(len(paper_name))
    df = pd.DataFrame()
    df['文献名'] = paper_name
    df['总文献数'] = total_papers_list
    df['爬取文献总数'] = have_papers_list
    df['比率'] = rate_list
    df.to_excel("爬取情况统计信息.xlsx", index=0)


def drop_duplicate_by_index(file):
    data_frame = pd.read_csv(file, encoding = 'gb18030')
    data_frame = data_frame.drop_duplicates(['序号'])
    data_frame.to_csv(file, encoding = 'gb18030', index = False)


if __name__ == "__main__":
    path = r"data"
    files = os.listdir(path)  # 获得文件夹中所有文件的名称列表
    for file in files:
        drop_duplicate_by_index(path + '\\' + file)
    out_get(path, files)
    get_total_info(path, files)

 # 使用方法
# eg:drop_duplicate_by_index(r'C:\data_analysis\total\data\西安电子科技大学学报.csv')