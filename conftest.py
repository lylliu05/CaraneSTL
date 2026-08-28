import sys
import os

# 让 pytest 能找到 app 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
