#!/bin/sh

# 设置环境变量
export IS_DOCKER_RUN=${IS_DOCKER_RUN:-"true"}

# 运行 install.py
python install.py

# 运行 Streamlit 应用
streamlit run st.py
