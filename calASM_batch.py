import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys
import math
import os
import matplotlib.pyplot as plt
import matplotlib
import time
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING

# ================= Matplotlib 绘图配置 =================
try:
    plt.style.use('seaborn-v0_8-whitegrid')
except:
    plt.style.use('ggplot')

matplotlib.rcParams['font.family'] = ['Times New Roman', 'SimSun', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# ================= 批量列表 =================
STOCK_LIST = [
    ("600372", "中航机载"),
    ("601698", "中国卫通"),
    ("600435", "北方导航"),
    ("002519", "银河电子"),
    ("000700", "模塑科技"),
    ("002361", "神剑股份"),
    ("002759", "天际股份"),
    ("603601", "再升科技"),
    ("600783", "鲁信创投"),
    ("002151", "北斗星通"),
    ("002565", "顺灏股份"),
    ("002202", "金风科技"),
    ("600879", "航天电子"),
    ("000559", "万向钱潮"),
    ("600118", "中国卫星"),
    ("002149", "西部材料"),
    ("000547", "航天发展"),
    ("002792", "通宇通讯"),
    ("002413", "雷科防务"),
    ("002131", "利欧股份"),
]

# 设定分析日期 (默认今天)
TARGET_DATE_STR = datetime.now().strftime("%Y%m%d")
# 预测天数 (T+1 到 T+X)
PREDICT_DAYS = 3

# ================= 表格绘图超参数 =================
TABLE_TITLE_FONT_SIZE = 24       # 主标题字号
TABLE_HEADER_FONT_SIZE = 13      # 表头字号
TABLE_CELL_FONT_SIZE = 16        # 单元格内容字号 (连板数等特殊列会独立设置)
TABLE_CELL_FONT_SIZE_NORMAL = 14 # 普通单元格字号
TABLE_FIG_WIDTH = 12             # 图片总宽度
TABLE_ROW_HEIGHT = 0.04          # 数据行高度系数
TABLE_HEADER_HEIGHT = 0.05       # 表头行高度系数
TABLE_FIG_HEIGHT_BASE = 1.0      # 图片基础高度
TABLE_FIG_HEIGHT_PER_ROW = 0.4   # 每行数据增加的高度

# ================= 工具函数 (复用自交互版) =================

def round_half_up(value, decimals=2):
    """
    严格的四舍五入函数 (解决Python默认银行家舍入导致的0.01%偏差)
    """
    try:
        # 转换为字符串构建 Decimal 避免浮点传入的精度问题
        d = Decimal(str(value))
        # 构造目标精度，例如 '0.01'
        fmt = "0." + "0" * decimals
        return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))
    except:
        return value

def plot_summary_overview(summary_data, title_prefix):
    """
    绘制所有股票的总览表 (自定义复杂表头版本)
    """
    if not summary_data:
        return

    # 1. 提取日期元数据 (从第一行数据中获取)
    meta_dates = ("T+1", "T+2", "T+3")
    if "_meta_dates" in summary_data[0]:
        meta_dates = summary_data[0]["_meta_dates"]
    
    # 2. 准备数据列表 (移除 _meta_dates 字段)
    clean_data = []
    for item in summary_data:
        new_item = item.copy()
        if "_meta_dates" in new_item:
            del new_item["_meta_dates"]
        # 按顺序排列 values [名称, 现价, T_偏离, T1_..., T2_..., T3_...]
        clean_data.append([
            new_item['名称'], new_item['现价'], new_item['T_偏离'],
            new_item['T1_触线'], new_item['T1_空间'], new_item['T1_板'],
            new_item['T2_触线'], new_item['T2_空间'], new_item['T2_板'],
            new_item['T3_触线'], new_item['T3_空间'], new_item['T3_板']
        ])
    
    # 定义列数
    n_cols = 12 
    n_rows = len(clean_data)
    
    # 动态计算图表大小
    fig_width = TABLE_FIG_WIDTH
    fig_height = max(1.5, n_rows * TABLE_FIG_HEIGHT_PER_ROW + TABLE_FIG_HEIGHT_BASE)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('off')
    
    # 颜色配置
    header_main_color = '#2c3e50'   # 深蓝 (一级表头)
    row_colors = ['#ffffff', '#f2f2f2']
    
    d1, d2, d3 = meta_dates
    
    # 构造单行复杂表头 (换行显示关键信息)
    headers = [
        "名称", "现价", "当前\n偏离", 
        f"{d1}\n触线价", f"{d1}\n允许涨幅", f"{d1}\n连板",
        f"{d2}\n触线价", f"{d2}\n允许涨幅", f"{d2}\n连板",
        f"{d3}\n触线价", f"{d3}\n允许涨幅", f"{d3}\n连板"
    ]
    
    full_table_data = [headers] + clean_data
    
    # 绘制表格
    table = ax.table(cellText=full_table_data,
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])
    
    table.auto_set_font_size(False)
    table.set_fontsize(TABLE_CELL_FONT_SIZE_NORMAL)
    
    # ================= 格式化单元格 =================
    # 获取单元格字典
    cells = table.get_celld()
    
    for (row, col), cell in cells.items():
        cell.set_linewidth(0.5)
        
        # --- Header ---
        if row == 0:
            cell.set_facecolor(header_main_color)
            cell.set_text_props(weight='bold', color='white', size=TABLE_HEADER_FONT_SIZE)
            cell.set_height(TABLE_HEADER_HEIGHT) # 略高以容纳换行
        
        # --- Data Rows ---
        else:
            data_row_idx = row - 1
            cell.set_height(TABLE_ROW_HEIGHT)
            cell.set_facecolor(row_colors[data_row_idx % 2])
            text_val = cell.get_text().get_text()
            
            # 名称 (Col 0)
            if col == 0:
                cell.set_text_props(weight='bold')

            # 偏离 (Col 3)
            # 偏离% (Col 2)
            if col == 2:
                try:
                    val = float(text_val.replace('%', ''))
                    # 使用标准四舍五入
                    rounded_val = round_half_up(val, 2)
                    cell.get_text().set_text(f"{rounded_val:.2f}") 
                    if abs(val) > 80: cell.set_text_props(color='red', weight='bold')
                except: pass
            
            # 允许最大涨幅 (Col 4, 7, 10)
            if col in [4, 7, 10]:
                if "触发" in text_val or "已触发" in text_val:
                    cell.set_text_props(color='white', weight='bold')
                    cell.set_facecolor('#c0392b')
                else:
                    try:
                        val = float(text_val.replace('%', ''))
                        # 使用标准四舍五入
                        rounded_val = round_half_up(val, 2)
                        cell.get_text().set_text(f"{rounded_val:.2f}") 
                        
                        if val < 10.0:
                            cell.set_text_props(color='red', weight='bold')
                        elif val < 20.0:
                            cell.set_text_props(color='#e67e22', weight='bold') 
                    except: pass
            
            # 连板 (Col 5, 8, 11)
            if col in [5, 8, 11]:
                try:
                    val = int(text_val)
                    if val > 0:
                        cell.set_text_props(weight='bold', color='#2980b9')
                        cell.set_fontsize(TABLE_CELL_FONT_SIZE)
                except: pass

    # 大标题
    full_title = f"{title_prefix} - 异动分析总览"
    plt.title(full_title, fontsize=TABLE_TITLE_FONT_SIZE, weight='bold', pad=20)
    
    # 添加底部说明
    note_text = "备注: 未来三天允许最大涨幅基于 [假设当日股价不变(0%)且指数不变(0%)] 推算得出，仅供参考。"
    plt.figtext(0.5, 0.01, note_text, ha="center", fontsize=12, color="#555555")
    
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    
    if not os.path.exists("images"): os.makedirs("images")
    safe_title = f"images/总览_{title_prefix}_{datetime.now().strftime('%H%M')}.png"
    
    try:
        plt.savefig(safe_title, dpi=300, bbox_inches='tight')
        print(f"   [总览已保存] {safe_title}")
    except Exception as e:
        print(f"   [保存失败] {e}")
    plt.close()

def get_realtime_quote_single(code):
    """
    单独获取某只股票的最新分钟级价格 (替代全市场扫描，速度更快)
    """
    try:
        # 获取当天分钟数据，period='1'代表1分钟线
        # adjust='' 不复权，保持一致
        df = ak.stock_zh_a_hist_min_em(symbol=code, period='1', adjust='')
        if df is None or df.empty:
            return None
        
        # 格式: 时间, 开盘, 收盘, 最高, 最低, ...
        # 只取最新一行
        last_row = df.iloc[-1]
        time_str = str(last_row['时间']) # 例如 "2024-05-21 10:35:00"
        price = float(last_row['收盘'])
        
        return {'time': time_str, 'price': price}
    except Exception as e:
        return None

def get_market_rules(stock_code):
    """根据代码判断指数和涨跌停限制"""
    index_code = "sh000002" # 默认沪市A股
    index_name = "上证A股"
    limit_ratio = 1.10
    
    if stock_code.startswith("6"):
        index_code = "sh000002" 
        index_name = "上证A股"
        if stock_code.startswith("688"):
            limit_ratio = 1.20
    elif stock_code.startswith("0") or stock_code.startswith("3"):
        index_code = "sz399107"
        index_name = "深证A股"
        if stock_code.startswith("300"):
            limit_ratio = 1.20
    
    return index_code, index_name, limit_ratio

def get_future_trading_dates(start_date_str, count):
    dates = []
    try:
        df = ak.tool_trade_date_hist_sina()
        all_dates = df['trade_date'].astype(str).tolist()
        dates = [d for d in all_dates if d > start_date_str]
        dates = dates[:count]
    except:
        pass
    
    try:
        current_date = datetime.strptime(start_date_str, "%Y%m%d")
    except:
        return [f"T+{i+1}" for i in range(count)]

    while len(dates) < count:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:
            d_str = current_date.strftime("%Y%m%d")
            if d_str not in dates:
                dates.append(d_str)
    return dates

def plot_result_table(df, title):
    if df.empty: return

    rows, cols = df.shape
    # 同步 interactive 的尺寸参数
    fig_height = max(3, rows * 0.4 + 1.5)
    fig_width = 10 
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('off')
    
    header_color = '#40466e'
    row_colors = ['#f9f9f9', '#ffffff'] 
    border_color = '#dddddd'

    table = ax.table(cellText=df.values,
                     colLabels=df.columns,
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])

    table.auto_set_font_size(False)
    table.set_fontsize(16) # 内容字号
    
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(border_color)
        cell.set_linewidth(1)
        
        if row == 0:
            cell.set_facecolor(header_color)
            cell.set_text_props(weight='bold', color='white', size=18) # 表头字号
            cell.set_height(0.12)
        else:
            cell.set_height(0.1)
            cell.set_facecolor(row_colors[row % 2])
            text_val = cell.get_text().get_text()
            column_name = df.columns[col]

            if column_name == "类型":
                if "预测" in text_val:
                    cell.set_text_props(color='#d62728', weight='bold') 
                elif "今日" in text_val:
                    cell.set_text_props(color='#2ca02c', weight='bold') 
                elif "历史" in text_val:
                    cell.set_text_props(color='#7f7f7f')

            if column_name == "剩余空间":
                if "触发" in text_val or "已触发" in text_val:
                    cell.set_text_props(color='red', weight='bold')
                    cell.set_facecolor('#ffeeee')

            if column_name == "允许涨幅":
                try:
                    val_float = float(text_val.replace('%', ''))
                    if val_float < 10.0:
                        cell.set_text_props(color='red', weight='bold') 
                except:
                    pass

            if column_name == "允许连板":
                try:
                    val = int(text_val)
                    if val > 0:
                         cell.set_text_props(weight='bold', color='#1f77b4')
                except:
                    pass

    plt.title(title, fontsize=24, weight='bold', pad=20) # 标题字号
    plt.tight_layout()
    
    # 创建 images 文件夹
    if not os.path.exists("images"):
        os.makedirs("images")
        
    filename = f"images/{title.replace(' ', '_').replace('/', '-')}.png"
    try:
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"   [已保存] {filename}")
    except Exception as e:
        print(f"   [保存失败] {e}")
    plt.close()

def analyze_period_combined(df, future_dates, days, threshold, limit_ratio):
    result_data = []

    current_idx = len(df) - 1
    t_row = df.iloc[current_idx]
    current_price = t_row['close']
    current_index = t_row['index_close']
    
    for offset in range(-2, len(future_dates) + 1):
        row_dict = {}

        if offset <= 0:
            type_label = "历史" if offset < 0 else "今日"
            target_idx = current_idx + offset
            if target_idx < 0: continue
            
            target_row = df.iloc[target_idx]
            target_date_str = target_row['date']
            p_end = target_row['close']
            i_end = target_row['index_close']
            actual_pct = target_row['pct_chg']
            
            p_prev = df.iloc[target_idx - 1]['close'] if target_idx > 0 else p_end
            base_idx = target_idx - days
        else:
            type_label = "预测"
            date_str = future_dates[offset - 1]
            try:
                target_date_str = datetime.strptime(date_str, "%Y%m%d").strftime("%m-%d") + f"(T+{offset})"
            except:
                target_date_str = f"{date_str}(T+{offset})"
            
            p_end = current_price
            i_end = current_index
            p_prev = current_price 
            actual_pct = 0.0
            base_idx = current_idx + offset - days

        if base_idx < 0: continue

        base_row = df.iloc[base_idx]
        p_base = base_row['close']
        i_base = base_row['index_close']
        base_date_str = base_row['date']

        # 使用 Decimal 进行高精度计算
        try:
            d_p_end = Decimal(str(p_end)) # 避免直接 f"{p_end:.2f}" 导致的四舍五入偏差
            d_p_base = Decimal(str(p_base))
            d_i_end = Decimal(str(i_end))
            d_i_base = Decimal(str(i_base))
            
            # (p_end / p_base - 1) * 100
            stock_cum_d = ((d_p_end / d_p_base) - 1) * 100
            index_cum_d = ((d_i_end / d_i_base) - 1) * 100
            
            # 偏离值 = 个股 - 指数
            deviation_d = stock_cum_d - index_cum_d
            
            stock_cum = float(stock_cum_d)
            index_cum = float(index_cum_d)
            deviation = float(deviation_d)
        except:
            # 降级处理
            stock_cum = (p_end / p_base - 1) * 100
            index_cum = (i_end / i_base - 1) * 100
            deviation = stock_cum - index_cum
        
        is_triggered = abs(deviation) >= threshold
        
        # 计算理论触线价格
        target_stock_cum = threshold + index_cum
        # raw_trigger_price = p_base * (1 + target_stock_cum / 100)
        
        # 修正逻辑：触线价格必须是交易最小单位(0.01)的整数倍
        # 只要 >= 理论价格 就会触发，因此需要向上取整 (Ceiling) 到分
        # try:
        #     d_raw_trigger = Decimal(str(raw_trigger_price))
        #     # 向上取整到 0.01
        #     d_trigger_tick = d_raw_trigger.quantize(Decimal("0.01"), rounding=ROUND_CEILING)
        #     trigger_price = float(d_trigger_tick)
        # except:
        #     trigger_price = math.ceil(raw_trigger_price * 100) / 100.0
        trigger_price = p_base * (1 + target_stock_cum / 100)
        # 这里需要向上取整保留两位小数
        # trigger_price = math.ceil(trigger_price * 100) / 100.0
        left_space = threshold - deviation
        
        # 允许涨幅 = (触线价格 / 前收盘 - 1) * 100
        # 这里使用修正后的触线价格，确保显示的涨幅与用户拿触线价手算的一致
        rp_tri_pri = round_half_up(trigger_price, 2)
        room_pct = (rp_tri_pri / p_prev - 1) * 100 if p_prev > 0 else 0
            
        limit_boards_val = 0
        if room_pct > 0:
             ratio = 1 + room_pct/100
             if ratio > 1 and math.log(limit_ratio) > 0:
                limit_boards_val = math.floor(math.log(ratio) / math.log(limit_ratio))
        
        # 格式化
        row_dict = {
            "日期": target_date_str,
            "类型": type_label,
            "基准日期": base_date_str,
            "实际涨幅": f"{round_half_up(actual_pct, 2):.2f}%", 
            "区间偏离": f"{round_half_up(deviation, 2):.2f}%",
            "剩余空间": "已触发" if is_triggered else f"{round_half_up(left_space, 2):.2f}%",
            "触线价格": float(f"{round_half_up(trigger_price, 2):.2f}"),
            "允许涨幅": "0.00%" if is_triggered else f"{room_pct:.2f}%",
            # "允许涨幅": "0.00%" if is_triggered else f"{round_half_up(room_pct, 2):.2f}%",
            "允许连板": 0 if is_triggered else limit_boards_val
        }
        result_data.append(row_dict)
    
    return pd.DataFrame(result_data)

def process_one_stock(stock_code, name):
    print(f"\n--- 处理 {stock_code} {name} ---")
    index_code, index_name, limit_ratio = get_market_rules(stock_code)
    
    start_date = (pd.to_datetime(TARGET_DATE_STR) - timedelta(days=120)).strftime("%Y%m%d")
    
    try:
        # 1. 个股
        # print("   获取个股数据...")
        stock_df = ak.stock_zh_a_hist(symbol=stock_code, start_date=start_date, end_date=TARGET_DATE_STR, adjust="")
        
        # --- 补全实时数据逻辑 ---
        need_realtime = False
        if stock_df is None or stock_df.empty:
             stock_df = pd.DataFrame(columns=['日期', '收盘', '涨跌幅'])
             need_realtime = True
        else:
             # 检查最后一天是否是今天
             last_date = stock_df.iloc[-1]['日期'] # 原始akshare返回是 'YYYY-MM-DD' 或 'YYYYMMDD'
             # 统一格式化比较
             if isinstance(last_date, str):
                 last_d_str = last_date.replace('-', '')
             else:
                 last_d_str = last_date.strftime("%Y%m%d")
             
             if last_d_str < TARGET_DATE_STR:
                 need_realtime = True

        if need_realtime:
            # 尝试单独获取实时价格
            real_data = get_realtime_quote_single(stock_code)
            if real_data:
                rt_time = real_data['time'] # "YYYY-MM-DD HH:MM:SS"
                rt_date_str = rt_time.split(' ')[0].replace('-', '')
                
                # 逻辑优化：只要实时数据的日期 > 历史数据的最后日期，就说明是更新的数据，可以补充
                # 不强制要求等于 TARGET_DATE_STR (这能容忍系统时间快于市场时间的情况，或者补充最近一个交易日的数据)
                if rt_date_str > last_d_str:
                    price = real_data['price']
                    
                    # 计算涨跌幅
                    pct_chg = 0.0
                    if not stock_df.empty:
                        last_close = stock_df.iloc[-1]['收盘'] # 昨收
                        if last_close > 0:
                            pct_chg = (price - last_close) / last_close * 100
                    
                    print(f"   [实时补充] {rt_time} 现价:{price} 涨幅:{pct_chg:.2f}%")
                    
                    new_row = pd.DataFrame({
                        '日期': [rt_date_str], # 使用实时数据的实际日期
                        '收盘': [float(price)],
                        '涨跌幅': [float(pct_chg)]
                    })
                    stock_df = pd.concat([stock_df, new_row], ignore_index=True)
                    # 更新 last_date_str 以便后续分析使用正确的基准
                    # 注意：后续代码中会重新获取 last_date_str = merged.iloc[-1]['date']，所以这里concat进去就够了
                else:
                    # 如果日期没更新，打印一下原因
                    # print(f"   [提示] 实时数据日期({rt_date_str}) 未超过 历史最新({last_d_str})，不予补充")
                    pass
            else:
                print(f"   [警告] 未能获取到 {stock_code} 的实时分钟数据")
        # -----------------------

        if stock_df is None or stock_df.empty:
            print(f"   [跳过] 无法获取 {stock_code} 数据")
            return None, None

        stock_df = stock_df.rename(columns={'日期': 'date', '收盘': 'close', '涨跌幅': 'pct_chg'})
        stock_df['date'] = pd.to_datetime(stock_df['date']).dt.strftime('%Y%m%d')

        # 2. 指数
        # print(f"   获取指数 {index_code} 数据...")
        index_df = ak.stock_zh_index_daily(symbol=index_code)
        if index_df is None or index_df.empty:
            print(f"   [跳过] 无法获取指数 {index_code}数据")
            return None, None
            
        index_df['date'] = pd.to_datetime(index_df['date']).dt.strftime('%Y%m%d')
        index_df = index_df.sort_values('date')
        index_df['index_pct_chg'] = index_df['close'].pct_change() * 100 
        index_df['index_pct_chg'] = index_df['index_pct_chg'].fillna(0)
        index_df = index_df.rename(columns={'close': 'index_close'})[['date', 'index_close', 'index_pct_chg']]
        
        # 3. 合并
        # 改用 left join，防止指数数据未更新导致个股实时数据被丢弃
        merged = pd.merge(stock_df, index_df, on='date', how='left')
        
        # 如果指数数据缺失(例如只有个股实时数据)，则向前填充指数收盘价，涨跌幅设为0
        if merged['index_close'].isnull().any():
            print("   [提示] 该日指数数据缺失，假设指数波动为0进行计算")
            merged['index_close'] = merged['index_close'].ffill()
            merged['index_pct_chg'] = merged['index_pct_chg'].fillna(0.0)

        merged = merged.sort_values('date')
        merged = merged[merged['date'] <= TARGET_DATE_STR]
        
        if len(merged) < 30:
            print("   [警告] 数据不足30天")
            return None, None

        last_date_str = merged.iloc[-1]['date']
        current_price = merged.iloc[-1]['close'] # 获取现价
        future_dates = get_future_trading_dates(last_date_str, PREDICT_DAYS)

        # 4. 分析与绘图
        df_10 = analyze_period_combined(merged, future_dates, 10, 100.0, limit_ratio)
        df_30 = analyze_period_combined(merged, future_dates, 30, 200.0, limit_ratio)
        
        safe_name = name.replace('*', '').replace(':', '')
        title_base = f"{safe_name}({stock_code})异动分析({last_date_str})"
        
        plot_result_table(df_10, f"{title_base}-10日(100%)")
        plot_result_table(df_30, f"{title_base}-30日(200%)")

        # 5. 提取汇总信息
        def extract_summary(res_df):
            # 查找 T, T+1, T+2, T+3
            row_map = {}
            for idx, row in res_df.iterrows():
                if row['类型'] == '今日' or row['日期'] == last_date_str:
                    row_map['T'] = row
                elif '(T+1)' in row['日期']:
                    row_map['T+1'] = row
                elif '(T+2)' in row['日期']:
                    row_map['T+2'] = row
                elif '(T+3)' in row['日期']:
                    row_map['T+3'] = row
            
            t_row = row_map.get('T', {})
            t1_row = row_map.get('T+1', {})
            t2_row = row_map.get('T+2', {})
            t3_row = row_map.get('T+3', {})
            
             # 辅助取日期的函数
            def get_date_str(r_row, default_suffix=""):
                raw = r_row.get("日期", "")
                if not raw: return default_suffix
                if "(" in raw:
                    return raw.split("(")[0]
                if len(raw) == 8 and raw.isdigit():
                    return f"{raw[4:6]}-{raw[6:8]}"
                return raw

            date_t1 = get_date_str(t1_row, "T+1")
            date_t2 = get_date_str(t2_row, "T+2")
            date_t3 = get_date_str(t3_row, "T+3")
            
            summary = {
                # 传递给绘图函数的表头日期 (T+1, T+2, T+3)
                "_meta_dates": (date_t1, date_t2, date_t3),
                
                "名称": name,
                "现价": f"{current_price:.2f}",
                
                "T_实际": t_row.get("实际涨幅", "-"),
                "T_偏离": t_row.get("区间偏离", "-"),
                
                "T1_触线": t1_row.get("触线价格", "-"),
                "T1_空间": t1_row.get("允许涨幅", "-"),
                "T1_板": t1_row.get("允许连板", "-"),
                
                "T2_触线": t2_row.get("触线价格", "-"),
                "T2_空间": t2_row.get("允许涨幅", "-"),
                "T2_板": t2_row.get("允许连板", "-"),

                "T3_触线": t3_row.get("触线价格", "-"),
                "T3_空间": t3_row.get("允许涨幅", "-"),
                "T3_板": t3_row.get("允许连板", "-"),
            }
            return summary

        sum_10 = extract_summary(df_10)
        sum_30 = extract_summary(df_30)
        return sum_10, sum_30

    except Exception as e:
        print(f"   [出错] {e}")
        import traceback
        traceback.print_exc()
        return None, None

def main():
    print("="*60)
    print(f"批量严重异动分析工具 (共 {len(STOCK_LIST)} 支股票)")
    print("结果将保存在 images/ 目录下")
    print("="*60)

    summary_list_10 = []
    summary_list_30 = []
    
    for code, name in STOCK_LIST:
        s10, s30 = process_one_stock(code, name)
        if s10: summary_list_10.append(s10)
        if s30: summary_list_30.append(s30)
        time.sleep(1) # 避免请求过快
    
    print("\n[生成总览表...]")
    plot_summary_overview(summary_list_10, "10日(100%)")
    plot_summary_overview(summary_list_30, "30日(200%)")
        
    print("\n[全部完成]")

if __name__ == "__main__":
    main()
