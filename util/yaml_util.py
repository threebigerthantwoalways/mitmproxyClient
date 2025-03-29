# -*- coding:utf-8 -*-
import os,sys,yaml
sys.stdout.reconfigure(encoding='utf-8')
# 当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)


# 读取  dict of list  字典列表
def read_yaml(filepath):
    with open(filepath, mode='r', encoding='utf-8') as f:
        yaml_data = yaml.load(stream=f.read(), Loader=yaml.FullLoader)
        return yaml_data