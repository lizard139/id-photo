import streamlit as st
from rembg import remove, new_session
from PIL import Image
import io
import os

# === 配置页面 (必须是第一个 Streamlit 命令) ===
st.set_page_config(
    page_title="iPhoto ID - 智能证件照",
    page_icon="📸",
    layout="centered",
    initial_sidebar_state="expanded"
)

# === 1. 核心模型加载 (关键修改：适配云端部署) ===
# 使用 st.cache_resource 缓存模型，避免每次刷新都重新下载/加载
@st.cache_resource
def get_model(model_name):
    # 在云端环境(GitHub/Streamlit Cloud)，我们不需要手动指定路径
    # rembg 会自动检测并将模型下载到默认的缓存目录 (~/.u2net)
    # 第一次运行时会慢一些（下载170MB），之后会秒开
    session = new_session(model_name)
    return session

# === 2. 注入 Apple 风格 CSS (UI 美化) ===
st.markdown("""
<style>
    /* 全局字体 - 优先使用 Apple 系统字体 */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    /* 背景色 - macOS 浅灰色 */
    .stApp {
        background-color: #F5F5F7;
    }
    
    /* 标题样式 */
    h1 {
        color: #1D1D1F;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E5E5;
    }
    
    /* 按钮样式 - iOS 蓝色风格 */
    div.stButton > button {
        background-color: #007AFF;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,122,255,0.2);
        transition: all 0.2s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #0051A8;
        box-shadow: 0 4px 8px rgba(0,122,255,0.3);
        transform: translateY(-1px);
    }
    
    /* 上传框样式 - 磨砂玻璃感 */
    div[data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 18px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px dashed #D2D2D7;
    }
    
    /* 图片容器圆角 */
    img {
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* 成功提示框 */
    div.stSuccess {
        background-color: #E8F2E8;
        border: none;
        color: #1D1D1F;
        border-radius: 10px;
    }
    
    /* 进度条颜色 */
    div[data-testid="stProgress"] > div > div > div > div {
        background-color: #007AFF;
    }
</style>
""", unsafe_allow_html=True)

# === 3. 侧边栏设置 ===
st.sidebar.title("⚙️ 设置面板")

# 尺寸定义
SIZE_MAP = {
    "1寸 (标准)": (295, 413),
    "1寸 (高清 2x)": (590, 826),
    "2寸 (标准)": (413, 579),
    "2寸 (高清 2x)": (826, 1158),
    "小2寸 (护照)": (567, 390) 
}

selected_size_name = st.sidebar.selectbox("1. 选择尺寸", list(SIZE_MAP.keys()), index=1)
target_size = SIZE_MAP[selected_size_name]

# 颜色定义
COLOR_MAP = {
    "🔵 标准蓝底": (67, 142, 219),
    "🔴 标准红底": (196, 12, 32),
    "⚪ 纯白底": (255, 255, 255),
    "🏁 透明底 (PNG)": None
}
selected_color_name = st.sidebar.radio("2. 背景颜色", list(COLOR_MAP.keys()))
bg_color = COLOR_MAP[selected_color_name]

st.sidebar.markdown("---")
st.sidebar.info("💡 **提示：** 首次生成可能需要几十秒下载模型，请耐心等待。")

# === 4. 主界面逻辑 ===
st.title("📸 iPhoto ID 智能证件照")
st.markdown("##### 简单、隐私、专业级的证件照生成工具")

uploaded_file = st.file_uploader("拖拽或点击上传照片 (JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    col1, col2 = st.columns([1, 2])
    with col1:
        original_image = Image.open(uploaded_file)
        st.image(original_image, caption="原始照片", use_container_width=True)
    
    with col2:
        st.write(" ")
        st.write(" ")
        generate_btn = st.button("✨ 立即生成证件照")
        
        if generate_btn:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 步骤 1: 获取模型
                status_text.text("Step 1/3: 云端正在唤醒 AI 模型 (首次可能较慢)...")
                # 使用 isnet-general-use，效果最好
                session = get_model("isnet-general-use")
                progress_bar.progress(30)
                
                # 步骤 2: 智能抠图
                status_text.text("Step 2/3: 正在处理发丝细节...")
                img_data = uploaded_file.getvalue()
                
                # 核心抠图逻辑
                img_no_bg_bytes = remove(img_data, session=session) 
                img_no_bg = Image.open(io.BytesIO(img_no_bg_bytes))
                progress_bar.progress(70)
                
                # 步骤 3: 合成与高画质裁剪
                status_text.text("Step 3/3: 正在进行高保真排版...")
                
                if bg_color:
                    final_canvas = Image.new("RGB", target_size, bg_color)
                else:
                    final_canvas = Image.new("RGBA", target_size, (0,0,0,0))
                
                # 智能居中算法 (Cover 模式)
                img_ratio = img_no_bg.width / img_no_bg.height
                canvas_ratio = target_size[0] / target_size[1]
                
                if img_ratio > canvas_ratio:
                    new_height = target_size[1]
                    new_width = int(new_height * img_ratio)
                else:
                    new_width = target_size[0]
                    new_height = int(new_width / img_ratio)
                
                # 高质量重采样
                img_resized = img_no_bg.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                paste_x = (target_size[0] - new_width) // 2
                paste_y = (target_size[1] - new_height) // 2
                if paste_y < 0: paste_y = 0
                
                final_canvas.paste(img_resized, (paste_x, paste_y), img_resized)
                
                progress_bar.progress(100)
                status_text.success("✅ 制作完成！")
                
                # 展示结果
                st.image(final_canvas, caption=f"最终效果 ({selected_size_name})", use_container_width=True)
                
                # 准备下载
                buf = io.BytesIO()
                save_format = "PNG" if selected_color_name == "🏁 透明底 (PNG)" else "JPEG"
                final_canvas.save(buf, format=save_format, quality=100, subsampling=0)
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="⬇️ 保存高清证件照",
                    data=byte_im,
                    file_name=f"id_photo_{selected_size_name}.{save_format.lower()}",
                    mime=f"image/{save_format.lower()}"
                )
                
            except Exception as e:
                st.error(f"发生错误: {e}")
                st.warning("提示：如果是第一次运行，云端下载模型可能需要一点时间，请刷新页面重试。")
