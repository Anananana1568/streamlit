import sqlite3
import streamlit as st
import re
from io import BytesIO
from PIL import Image
import pandas as pd

# 从数据库中获取数据标注情况
def get_label_status():
    cursor.execute(f"SELECT * FROM image_data LIMIT 0, 50")
    rows = cursor.fetchall()
    label_status = {}
    for row in rows:
        id = row[0]
        up5_label = row[6]
        up4_label = row[8]
        up3_label = row[10]
        up2_label = row[12]
        up1_label = row[14]
        down1_label = row[16]
        down2_label = row[18]
        down3_label = row[20]
        down4_label = row[22]
        down5_label = row[24]
        
        # 检查 up1_label 和 down1_label 是否有 none
        labels = [up5_label, up4_label, up3_label, up2_label, up1_label, 
                down1_label, down2_label, down3_label, down4_label, down5_label]
        
        if any(label == 'none' for label in labels):
            label_status[id] = "empty"  # 未标注
        else:
            label_status[id] = "filled"  # 已标注
    return label_status


def create_table():
    label_status = get_label_status()  # 获取标注状态
    data = []
    
    # 构建数据行和列
    for row_id in range(1, 11):  # 5行
        row = []
        for col_id in range(1, 6):  # 10列
            data_id = (row_id - 1) * 5 + col_id
            row.append(data_id)  # 添加ID
        data.append(row)
    
    # 创建 DataFrame，行标题和列标题都为 'data_id'
    columns = [f"{i}" for i in range(1, 6)]  # 确保列名唯一
    df = pd.DataFrame(data, columns=columns)  # 行索引保持默认
    return df, label_status

def highlight_filled(val, label_status):
    """ 根据标注状态改变单元格的颜色 """
    color = ''
    if val and isinstance(val, int):  # 如果是数字并且对应的id存在
        if label_status.get(val, "empty") == "filled":  # 标注过的
            color = 'background-color: red; color: white;'  # 红色背景白色字体
        else:  # 未标注
            color = 'background-color: white; color: black;'  # 白色背景黑色字体
    return color


# 读取已标注的数据ID
def read_labeled_ids():
    try:
        with open("/Users/liyurong/Downloads/streamlit/data/labeled_ids.txt", "r") as file:
            return set(line.strip() for line in file.readlines())
    except FileNotFoundError:
        return set()

# 记录已标注的ID到文件
def record_labeled_id(data_id):
    with open("/Users/liyurong/Downloads/streamlit/data/labeled_ids.txt", "a") as file:
        file.write(f"{data_id}\n")

def get_data_from_db(row_id):
    cursor.execute("SELECT * FROM image_data WHERE id=?", (row_id,))
    row = cursor.fetchone()  # 获取第一行结果
    if row:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))
    return None

def update_labels_in_db(data_id, up_labels, down_labels):
    for i in range(1, 6):
        up_label = up_labels[i - 1]
        down_label = down_labels[i - 1]
        
        cursor.execute(f"""
            UPDATE image_data
            SET up{i}_label = ?, down{i}_label = ?
            WHERE id = ?
        """, (up_label, down_label, data_id))
    
    conn.commit()

def login():
    st.sidebar.header("用户登录")
    username = st.sidebar.text_input("用户名")
    password = st.sidebar.text_input("密码", type="password")
    
    if st.sidebar.button("登录"):
        if username in users and users[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success("登录成功!")
        else:
            st.error("用户名或密码错误!")

def show_data_page():
    if 'page' not in st.session_state:
        st.session_state.page = 1

    labeled_ids = read_labeled_ids()


    # 手动输入ID跳转
    input_id = st.sidebar.text_input("输入ID跳转", "")

    # 如果用户输入了ID，跳转到该ID对应的数据
    if input_id:
        try:
            input_id = int(input_id)  # 尝试将输入转换为整数
            st.session_state.page = input_id  # 跳转到对应的页面
            st.success(f"已跳转到数据ID {input_id}")
        except ValueError:
            st.error("请输入有效的数字ID")

    def show_data_for_page(page):
        row_id = page
        if row_id in labeled_ids:
            # 如果该数据已经被标注过，跳到下一条
            return None, None

        json_data = get_data_from_db(row_id)

        if json_data:
            st.markdown(f"""
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 6px; text-align: center; 
                            box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1); width: 60%; margin: auto;">
                    <h2 style="margin: 0; font-size: 24px;">第 {page} 条数据 / 共 50 条数据</h2>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            st.sidebar.image(Image.open(BytesIO(json_data['image_data'])), use_container_width=True)
            st.sidebar.markdown('<h3 style="color: red;font-style: italic;font-size: 24px;">caption</h3>', unsafe_allow_html=True)
            st.sidebar.write(json_data['caption'].strip('<p>').strip('</p>'))
            st.sidebar.markdown('<h3 style="color: red; font-style: italic;font-size: 24px;">sentence</h3>', unsafe_allow_html=True)
            sentence = re.sub(r'<xref[^>]*>(.*?)</xref>', r'\1', json_data['sentence'])
            st.sidebar.write(sentence)

            # 初始化 up_labels 和 down_labels
            up_labels = ["none"] * 5
            down_labels = ["none"] * 5

            for i in range(5, 0, -1):  # 上文从 5 到 1
                st.markdown(f'<h3 style="color: red; font-size: 18px;">上文第{i}句</h3>', unsafe_allow_html=True)
                content = json_data[f"up{i}"]
                st.markdown(f'<h3 style="font-size: 18px;">{content}</h3>', unsafe_allow_html=True)

                col1, col2 = st.columns([2, 1])
                with col2:
                    up_label_value = json_data.get(f"up{i}_label", "none").lower()  # 获取数据库中对应的值并转为小写

                    up_labels[i - 1] = st.radio(
                        "是否相关", 
                        ["none", "true", "false"], 
                        index=["none", "true", "false"].index(up_label_value if up_label_value in ["none", "true", "false"] else "none"),
                        key=f"up_label_{i}"
                    )
                st.text("")
                st.markdown("<hr>", unsafe_allow_html=True)

            for i in range(1, 6):  # 下文从 1 到 5
                st.markdown(f'<h3 style="color: red; font-size: 18px;">下文第{i}句</h3>', unsafe_allow_html=True)
                content1 = json_data[f"down{i}"]
                st.markdown(f'<h3 style="font-size: 18px;">{content1}</h3>', unsafe_allow_html=True)

                col1, col2 = st.columns([3, 1])
                with col2:
                    down_label_value = json_data.get(f"down{i}_label", "none").lower()  # 获取数据库中对应的值并转为小写

                    down_labels[i - 1] = st.radio(
                        "是否相关", 
                        ["none", "true", "false"], 
                        index=["none", "true", "false"].index(down_label_value if down_label_value in ["none", "true", "false"] else "none"),
                        key=f"down_label_{i}"
                    )

                st.text("")
                st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(f"""
                    <h2 style="margin: 0; font-size: 14px;">第 {page} 条数据 / 共 50 条数据</h2>
                </div>
            """, unsafe_allow_html=True)

            return row_id,up_labels, down_labels
        else:
            st.write('未找到该数据！')
            return ["none"] * 5, ["none"] * 5

    row_id,up_labels, down_labels = show_data_for_page(st.session_state.page)

    if up_labels is None and down_labels is None:
        # 如果数据已经标注过，直接跳到下一页
        if st.session_state.page < 50:  # 假设数据总共有50行
            st.session_state.page += 1
        return

    if st.button("提交"):
        if 'none' in up_labels or 'none' in down_labels:
            temp_li = [{"up": idx} for idx, label in enumerate(up_labels) if label == 'none'] + [{"down": idx} for idx, label in enumerate(down_labels) if label == 'none']
            for dic in temp_li:
                if 'up' in dic:
                    st.warning(f"up{dic['up'] + 1}未标注")
                else:
                    st.warning(f"down{dic['down'] + 1}未标注")
        else:
            st.success("提交成功!")
            st.session_state['up_labels'] = up_labels
            st.session_state['down_labels'] = down_labels
            # 更新数据库
            update_labels_in_db(row_id, up_labels, down_labels)
            # 记录已标注ID
            record_labeled_id(row_id)

    col2_1, col2_2 = st.columns(2)
    with col2_1:
        if st.button('上一页', key="prev"):
            if st.session_state.page > 1:
                st.session_state.page -= 1
    with col2_2:
        if st.button('下一页', key="next"):
            if st.session_state.page < 50:  # 假设数据总共有50行
                st.session_state.page += 1

db_path = "/Users/liyurong/Downloads/streamlit/image_data_try.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

users = {"user1": "password1", "user2": "password2"}

# 加载所有信息
if "logged_in" not in st.session_state:
    login()
else:
    st.markdown(f'<h3 style="color: black; font-size: 24px;">数据标注</h3>', unsafe_allow_html=True)
    col3_1,col3_2=st.columns(2)
    with col3_1:
        st.markdown(f'<h3 style="color: black; font-size: 16px;">1.数据标注情况</h3>', unsafe_allow_html=True)
        # 生成表格
        df, label_status = create_table()
        # 为每个单元格应用不同的背景色
        styled_df = df.style.applymap(lambda val: highlight_filled(val, label_status))
        # 显示表格，保持滚动功能
        st.dataframe(styled_df, use_container_width=True)
    with col3_2:
        st.markdown(f'<h3 style="color: black; font-size: 16px;">2.标注须知</h3>', unsafe_allow_html=True)
        st.markdown(f'<h3 style="color: black; font-size: 14px;">以下几种情况视为相关：</h3>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    show_data_page()

# 关闭数据库连接
conn.close()
