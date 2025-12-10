import streamlit as st
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px

# Setting API
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# Lấy thông tin đăng nhập từ secrets
USERNAME = st.secrets["login"]["username"]
PASSWORD = st.secrets["login"]["password"]

# ===== INIT SESSION =====
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ===== ONLY SHOW LOGIN IF NOT LOGGED =====
# ===== ONLY SHOW LOGIN IF NOT LOGGED =====
if not st.session_state.logged_in:

    # ===== CSS UI =====
    st.markdown("""
        <style>
        body {
            background: linear-gradient(135deg, #6366F1, #8B5CF6);
            height: 100vh;
        }
        .login-card {
            background: white;
            padding: 40px 35px;
            border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            max-width: 420px;
            margin: 80px auto;
            animation: fadeIn 0.5s ease-in-out;
        }
        @keyframes fadeIn {
            from {opacity:0; transform: translateY(15px);}
            to {opacity:1; transform: translateY(0);}
        }
        .title {
            font-size: 28px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 10px;
            color: #1F2937;
        }
        .subtitle {
            text-align: center;
            font-size: 15px;
            color: #6B7280;
            margin-bottom: 25px;
        }
        </style>
    """, unsafe_allow_html=True)

    # ===== LOGIN CARD WRAPPER =====
    st.markdown("<div class='title'>‼️Đăng nhập để truy cập App‼️",
                unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Welcome back! Please enter your details.</div>",
                unsafe_allow_html=True)

    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password",
                             placeholder="Enter your password")

    login_btn = st.button("Login", type="primary")

    st.markdown("</div>", unsafe_allow_html=True)

    # ===== LOGIN LOGIC =====
    if login_btn:
        if username == USERNAME and password == PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("❌ Incorrect username or password")

else:
    # ===== Sidebar Logout =====
    if st.session_state.logged_in:
        if st.sidebar.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

    try:
        creds_info = st.secrets["google"]

        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_info, scope
        )

        client = gspread.authorize(credentials)

        st.success("🔐 Đã đăng nhập và kết nối Google Sheets API thành công!")

    except Exception as e:

        st.error(f"❌ Lỗi khi kết nối Google Sheets API: {e}")

# ===== KHỞI TẠO SESSION STATE =====
    st.session_state.setdefault("processing", False)
    st.session_state.setdefault("show_warning", True)
    st.session_state.setdefault("income", None)
    st.session_state.setdefault("show_config_ui", True)

    # ===== SETUP GIAO DIỆN =====
    st.set_page_config(page_title="Tool Report Income",
                       layout="centered", page_icon="📊")
    # ===== CSS tuỳ chỉnh =====
    st.markdown(
        """
        <style>
            /* Tổng thể */
            html, body, [class*="css"] {
                font-family: 'Segoe UI', sans-serif;
            }
            h1, h3, h4 {
                color: #333333;
            }
            .centered {
                text-align: center;
            }
            .upload-box {
                border: 2px dashed #cccccc;
                padding: 20px;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style='display: flex; justify-content: center; align-items: center; gap: 10px;'>
            <img src='https://img.icons8.com/?size=100&id=118638&format=png&color=000000' width='40'/>
            <h1 style='margin: 0;'>BÁO CÁO DOANH THU TIKTOK</h1>
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<hr style='margin-top: 10px; margin-bottom: 30px;'>", unsafe_allow_html=True
    )

    def clean_value(x):
        if pd.isna(x):
            return ""
        elif isinstance(x, (int, float)):
            return x  # giữ nguyên kiểu số
        elif isinstance(x, str):
            return x.replace("'", "''")  # escape dấu nháy đơn nếu có
        else:
            return str(x)

    def read_incomedata(df_income, df_all):
        df_income.columns = df_income.columns.str.strip()
        special_map = {
            "Total fees": "Total Fees",
            "Total revenue": "Total Revenue",
            "Order Settled Time": "Order settled Time",
        }

        df_income = df_income.rename(columns=special_map, errors="ignore")
        df_income["Classify"] = (
            df_income["Related order ID"]
            .duplicated(keep=False)
            .map({True: "Duplicate", False: "Not Duplicate"})
        )
        df_income["Paydouble"] = df_income.duplicated(
            subset=["Related order ID", "Order/adjustment ID"], keep=False
        ).map({True: "Yes", False: "No"})

        df_income["Order/adjustment ID"] = df_income["Order/adjustment ID"].astype(
            str)
        df_income["Related order ID"] = df_income["Related order ID"].astype(
            str)
        # Bước 1: Đánh dấu cờ để xử lý
        df_income["OID_start7"] = (
            df_income["Order/adjustment ID"].astype(str).str.startswith("7")
        )
        df_income["Not_Order_Type"] = df_income["Type"].astype(str) != "Order"

        # Bước 2: Đếm số lần xuất hiện của Related order ID
        df_income["RID_count"] = df_income.groupby("Related order ID")[
            "Related order ID"
        ].transform("count")

        # Bước 3: Xác định loại đơn theo logic
        grouped = df_income.groupby("Related order ID")
        is_compensation = grouped["OID_start7"].transform("any") | grouped[
            "Not_Order_Type"
        ].transform("any")
        is_doublepaid = (df_income["RID_count"] > 1) & ~is_compensation

        # Bước 4: Gán nhãn
        df_income["Actually Order Type"] = "Normal"  # Mặc định là Normal
        df_income.loc[is_compensation, "Actually Order Type"] = "Compensation"
        df_income.loc[is_doublepaid, "Actually Order Type"] = "DoublePaid"

        # Bước 5: Xoá cột phụ nếu muốn
        df_income.drop(
            columns=["OID_start7", "Not_Order_Type", "RID_count"], inplace=True)

        # Data all
        df_all["Order ID"] = df_all["Order ID"].astype(str)

        # Chuẩn hóa cột Province và Country cho df_all
        df_all["Province"] = df_all["Province"].str.replace(
            r"^(Tỉnh |Tinh )", "", regex=True
        )
        df_all["Province"] = df_all["Province"].str.replace(
            r"^(Thanh pho |Thành phố |Thành Phố )", "", regex=True
        )

        df_all["Country"] = df_all["Country"].replace(
            {
                "Viêt Nam",
                "Vietnam",
                "The Socialist Republic of Viet Nam",
                "Socialist Republic of Vietnam",
            },
            "Việt Nam",
        )

        df_all["Province"] = df_all["Province"].replace(
            {
                "Ba Ria– Vung Tau": "Bà Rịa - Vũng Tàu",
                "Bà Rịa-Vũng Tàu": "Bà Rịa - Vũng Tàu",
                "Ba Ria - Vung Tau": "Bà Rịa - Vũng Tàu",
                "Bac Giang": "Bắc Giang",
                "Bac Lieu": "Bạc Liêu",
                "Bac Ninh": "Bắc Ninh",
                "Ben Tre": "Bến Tre",
                "Binh Dinh": "Bình Định",
                "Binh Duong": "Bình Dương",
                "Binh Duong Province": "Bình Dương",
                "Binh Phuoc": "Bình Phước",
                "Binh Thuan": "Bình Thuận",
                "Ca Mau": "Cà Mau",
                "Ca Mau Province": "Cà Mau",
                "Can Tho": "Cần Thơ",
                "Phố Cần Thơ": "Cần Thơ",
                "Da Nang": "Đà Nẵng",
                "Da Nang City": "Đà Nẵng",
                "Phố Đà Nẵng": "Đà Nẵng",
                "Dak Lak": "Đắk Lắk",
                "Đắc Lắk": "Đắk Lắk",
                "Ðắk Nông": "Đắk Nông",
                "Đắk Nông": "Đắk Nông",
                "Dak Nong": "Đắk Nông",
                "Dong Nai": "Đồng Nai",
                "Dong Nai Province": "Đồng Nai",
                "Dong Thap": "Đồng Tháp",
                "Dong Thap Province": "Đồng Tháp",
                "Ha Nam": "Hà Nam",
                "Ha Noi": "Hà Nội",
                "Ha Noi City": "Hà Nội",
                "Phố Hà Nội": "Hà Nội",
                "Hai Phong": "Hải Phòng",
                "Phố Hải Phòng": "Hải Phòng",
                "Ha Tinh": "Hà Tĩnh",
                "Hau Giang": "Hậu Giang",
                "Hô-Chi-Minh-Ville": "Hồ Chí Minh",
                "Ho Chi Minh": "Hồ Chí Minh",
                "Ho Chi Minh City": "Hồ Chí Minh",
                "Kota Ho Chi Minh": "Hồ Chí Minh",
                "Hoa Binh": "Hòa Bình",
                "Hoà Bình": "Hòa Bình",
                "Hung Yen": "Hưng Yên",
                "Khanh Hoa": "Khánh Hòa",
                "Khanh Hoa Province": "Khánh Hòa",
                "Khánh Hoà": "Khánh Hòa",
                "Kien Giang": "Kiên Giang",
                "Kiến Giang": "Kiên Giang",
                "Long An Province": "Long An",
                "Nam Dinh": "Nam Định",
                "Nghe An": "Nghệ An",
                "Ninh Binh": "Ninh Bình",
                "Ninh Thuan": "Ninh Thuận",
                "Quang Binh": "Quảng Bình",
                "Quang Tri": "Quảng Trị",
                "Quang Nam": "Quảng Nam",
                "Quang Ngai": "Quảng Ngãi",
                "Quang Ninh": "Quảng Ninh",
                "Quang Ninh Province": "Quảng Ninh",
                "Soc Trang": "Sóc Trăng",
                "Tay Ninh": "Tây Ninh",
                "Thai Binh": "Thái Bình",
                "Thanh Hoa": "Thanh Hóa",
                "Thanh Hoá": "Thanh Hóa",
                "Hai Duong": "Hải Dương",
                "Thừa Thiên Huế": "Thừa Thiên-Huế",
                "Thua Thien Hue": "Thừa Thiên-Huế",
                "Vinh Long": "Vĩnh Long",
                "Tra Vinh": "Trà Vinh",
                "Vinh Phuc": "Vĩnh Phúc",
                "Cao Bang": "Cao Bằng",
                "Lai Chau": "Lai Châu",
                "Ha Giang": "Hà Giang",
                "Lam Dong": "Lâm Đồng",
                "Lao Cai": "Lào Cai",
                "Phu Tho": "Phu Tho",
                "Phu Yen": "Phú Yên",
                "Thai Nguyen": "Thái Nguyên",
                "Son La": "Sơn La",
                "Tuyen Quang": "Tuyên Quang",
                "Yen Bai": "Yên Bái",
                "Dien Bien": "Điện Biên",
                "Tien Giang": "Tiền Giang",
            }
        )
        df_all["SKU Category"] = df_all["Seller SKU"].copy()

        Total_revenue = df_income["Total Revenue"].sum()
        Total_fees = df_income["Total Fees"].sum()
        Total_settlement = df_income["Total settlement amount"].sum()

        # Bảng số lượng bán ra cho từng SKU (tổng quát 100%)

        df_merged = pd.merge(
            df_income,
            df_all,
            how="left",
            right_on="Order ID",
            left_on="Related order ID",
        )

        sku_quantity = df_merged.groupby(["Seller SKU", "Product Name"]).agg(
            Total_Quantity=("Quantity", "sum"),
            Total_Orders=("Order ID", "nunique")
        ).reset_index()
        # Revenue theo SKU
        revenue_by_sku = df_merged.groupby(["Seller SKU", "Product Name"]).agg(
            Total_Revenue=("Total Revenue", "sum"),
            Total_Fees=("Total Fees", "sum"),
            Total_Settlement=("Total settlement amount", "sum")
        ).reset_index()

        # Final Report
        sku_report = sku_quantity.merge(
            revenue_by_sku,
            on=["Seller SKU", "Product Name"],
            how="left"
        )

        return df_income, df_all, Total_revenue, Total_fees, Total_settlement, df_merged, sku_report

    def SumQuantityForSKU(df, sku_category):
        # ---- Hoàn thành ----
        df_hoan_thanh = df[
            (df["SKU Category"] == sku_category)
            & (df["Total Revenue"] > 0)
            & (df["Actually Order Type"] == "Normal")
        ]

        # ---- Đền bù ----
        df_den_bu = df[
            (df["SKU Category"] == sku_category)
            & (df["Type"].isin(["Logistics reimbursement", "Platform reimbursement"]))
        ]

        # ---- Hoàn trả ----
        df_hoan_tra = df[
            (df["SKU Category"] == sku_category)
            & (df["Type"] == "Order")
            & (df["Sku Quantity of return"] != 0)
            & (df["Cancelation/Return Type"].isin(["Return/Refund", ""]))
            & (df["Classify"] == "Not Duplicate")
        ]

        # ---- Boom ----
        df_boom = df[
            (df["SKU Category"] == sku_category)
            & (df["Type"] == "Order")
            & (df["Cancelation/Return Type"] == "Cancel")
            & (df["Total Revenue"] <= 0)
        ]

        # ---- Kết quả ----
        return {
            "sku": sku_category,
            "hoan_thanh": df_hoan_thanh["Quantity"].sum(),
            "den_bu": df_den_bu["Sku Quantity of return"].sum(),
            "hoan_tra": df_hoan_tra["Sku Quantity of return"].sum(),
            "boom": df_boom["Quantity"].sum(),
        }

    # ===== SIDEBAR =====
    st.markdown("""
        <style>
        /* Sidebar responsive */
        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                width: 100% !important;
            }
            [data-testid="stSidebar"] > div:first-child {
                width: 100% !important;
            }
        }
        @media (min-width: 769px) {
            [data-testid="stSidebar"] {
                width: 420px !important;
            }
            [data-testid="stSidebar"] > div:first-child {
                width: 420px !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)

    st.sidebar.markdown("### 📤 Tải lên dữ liệu doanh thu bán hàng theo ngày")
    df_income_file = st.sidebar.file_uploader(
        "Upload file Income",
        type=["xlsx", "xls"],
        key="income_file"
    )

    # ===== CẢNH BÁO NẾU CHƯA UPLOAD FILE =====
    if st.session_state.show_warning and df_income_file is None:
        st.markdown("""
            <div style="
                padding: 12px;
                border-radius: 10px;
                background: #FFF4E5;
                border-left: 5px solid #FFA726;
                color: #5A3800;
                font-size: 15px;
                margin: 10px 0;
            ">
                ⚠️ <b>Vui lòng input file trước khi xử lý.</b>
            </div>
        """, unsafe_allow_html=True)

    # ===== BUTTON =====
    if df_income_file is not None:
        df_income = pd.read_excel(df_income_file)
        df_income.columns = df_income.columns.str.strip()

        df_income["Order created time"] = pd.to_datetime(
            df_income["Order created time"]
        )

        date_min = df_income["Order created time"].min()
        date_max = df_income["Order created time"].max()

        st.write("Tải file All Orders từ ngày bắt đầu là:", date_min.date())
        st.write("Tải file All Orders đến ngày kết thúc là:", date_max.date())

        df_all_file = st.sidebar.file_uploader(
            "Upload file All Order",
            type=["csv"],
            key="all_file"
        )

        if df_all_file is not None:
            df_all = pd.read_csv(df_all_file)
            df_all.columns = df_all.columns.str.strip()
            df_all["SKU Category"] = df_all["Seller SKU"].copy()
            list_sku = sorted(df_all["SKU Category"].dropna().unique())

            if st.session_state.show_config_ui:
                sku_info = {}
                for sku in list_sku:
                    cost = st.number_input(
                        f"Giá vốn cho SKU **{sku}**",
                        min_value=0,
                        step=1000,
                        key=f"cost_{sku}",
                    )
                    sku_info[sku] = cost

        # ===== CHI PHÍ & HOA HỒNG =====

            commission_rate = st.sidebar.number_input(
                "📊 Tỷ lệ hoa hồng (%)",
                min_value=0.0, max_value=100.0, value=7.0, step=0.5, format="%.2f"
            )
            st.sidebar.markdown("### ⚙️ Xử lý dữ liệu")

            # ===== XỬ LÝ DỮ LIỆU =====
            process_btn = st.sidebar.button(
                "🔍 Xử lý dữ liệu", disabled=st.session_state.processing)

            if process_btn:
                # Khóa UI NGAY — QUAN TRỌNG
                st.session_state.processing = True
                st.session_state.show_config_ui = False
                with st.spinner("⏳ Đang xử lý dữ liệu..."):
                    df_income, df_all, Total_revenue, Total_fees, Total_settlement, df_merged, sku_report = read_incomedata(
                        df_income, df_all)

                ket_qua = []

                for sku in df_merged["SKU Category"].unique():
                    record = SumQuantityForSKU(df_merged, sku)
                    ket_qua.append(record)

                df_ket_qua = pd.DataFrame(ket_qua)
                df_ket_qua["Gia_von"] = df_ket_qua["sku"].map(sku_info)
                df_ket_qua["Total_Cost"] = df_ket_qua["Gia_von"] * \
                    df_ket_qua["hoan_thanh"]

                st.session_state.income = df_income
                st.session_state.df_merged = df_merged
                st.session_state.df_ket_qua = df_ket_qua
                st.rerun()

                st.success("✔️ Xử lý dữ liệu thành công!")

            # ===== RESET NÚT =====
            reset_btn = st.sidebar.button("🔁 Reset")
            if reset_btn:
                st.session_state.income = None
                st.session_state.processing = False
                st.session_state.show_warning = True
                st.session_state.show_config_ui = True
                st.success(
                    "♻️ Dữ liệu đã được xóa. Bạn có thể upload file khác.")

    # ===== XỬ LÝ DỮ LIỆU =====
    if st.session_state.processing:

        report_container = st.container()
        result_box = st.empty()

        with report_container:
            # Lấy dữ liệu đã xử lý từ session state
            df_income = st.session_state.income
            df_merged = st.session_state.df_merged
            # ---- Tính toán các chỉ số chính ----
            total_revenue = df_income["Total Revenue"].sum()
            total_settlement = df_income["Total settlement amount"].sum()
            total_fees = df_income["Total Fees"].sum()
            total_VAT = df_income['VAT withheld by TikTok Shop'].sum()
            total_GTGT = df_income['PIT withheld by TikTok Shop'].sum()

            extra_cost = st.session_state.df_ket_qua["Total_Cost"].sum()

            profit = total_settlement - extra_cost

            total_commission = profit * (commission_rate/100)

            day_of_data = df_income["Order settled time"][0]
            df_income["Substatus"] = np.where(
                df_income["Type"] != "Order",
                df_income["Type"],
                np.where(
                    (df_income["Total Revenue"] < 0) & (
                        df_income["Total settlement amount"] < 0),
                    "Returned",
                    np.where(
                        df_income["Total Revenue"] > 0,
                        "Completed",
                        "Canceled"
                    )
                )
            )

            st.info(f"📅 Ngày quyết toán: **{day_of_data}**")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(
                    f"""
                    <div style="background-color:#e0f7fa; padding:20px; border-radius:10px; text-align:center; box-shadow:2px 2px 10px rgba(0,0,0,0.1);">
                        <div style="font-size:14px; color:#00796b; font-weight:bold;">📝 Tổng doanh thu từ sàn</div>
                        <div style="font-size:26px; font-weight:bold; color:#004d40;">{total_revenue:,.0f} ₫</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f"""
                    <div style="background-color:#fff3e0; padding:20px; border-radius:10px; text-align:center; box-shadow:2px 2px 10px rgba(0,0,0,0.1);">
                        <div style="font-size:14px; color:#ef6c00; font-weight:bold;">💰 Tổng quyết toán từ sàn</div>
                        <div style="font-size:26px; font-weight:bold; color:#e65100;">{total_settlement:,.0f} ₫</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col3:
                st.markdown(
                    f"""
                    <div style="background-color:#ffebee; padding:20px; border-radius:10px; text-align:center; box-shadow:2px 2px 10px rgba(0,0,0,0.1);">
                        <div style="font-size:14px; color:#c62828; font-weight:bold;">📌 Tổng chi phí từ sàn</div>
                        <div style="font-size:26px; font-weight:bold; color:#b71c1c;">{total_fees:,.0f} ₫</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            colfk1, col6, col7, colfk2 = st.columns([0.3, 1, 1, 0.3])

            with col6:
                st.markdown(
                    f"""
                    <div style="background-color:#e0f2f1; padding:20px; border-radius:10px; text-align:center; box-shadow:2px 2px 10px rgba(0,0,0,0.1); margin-top:20px;">
                        <div style="font-size:14px; color:#00695c; font-weight:bold;">‼️ Thuế VAT đã đóng cho sàn </div>
                        <div style="font-size:26px; font-weight:bold; color:#004d40;">{total_VAT:,.0f} ₫</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col7:
                st.markdown(
                    f"""
                    <div style="background-color:#fce4ec; padding:20px; border-radius:10px; text-align:center; box-shadow:2px 2px 10px rgba(0,0,0,0.1); margin-top:20px;">
                        <div style="font-size:14px; color:#d81b60; font-weight:bold;">↗️ Thuế GTGT đã đóng cho sàn </div>
                        <div style="font-size:26px; font-weight:bold; color:#c2185b;">{total_GTGT:,.0f} ₫</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            col45, col4, col5 = st.columns(3)

            with col45:
                st.markdown(
                    f"""
                    <div style="background-color: #990033 ; padding:20px; border-radius:10px; text-align:center; box-shadow:2px 2px 10px rgba(0,0,0,0.1); margin-top:40px;">
                        <div style="font-size:18px; color:white; font-weight:bold;">♾️ Chi phí sản xuất</div>
                        <div style="font-size:26px; font-weight:bold; color:white;">{extra_cost:,.0f} ₫</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col4:
                st.markdown(
                    f"""
                    <div style="background-color: #339933 ; padding:20px; border-radius:10px; text-align:center; box-shadow:2px 2px 10px rgba(0,0,0,0.1); margin-top:40px;">
                        <div style="font-size:18px; color:white; font-weight:bold;">💵 Lợi nhuận ròng</div>
                        <div style="font-size:26px; font-weight:bold; color:white;">{profit:,.0f} ₫</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col5:
                st.markdown(
                    f"""
                    <div style="background-color:#003399; padding:20px; border-radius:10px; text-align:center; box-shadow:2px 2px 10px rgba(0,0,0,0.1); margin-top:40px;">
                        <div style="font-size:18px; color:white; font-weight:bold;">🌹Chi phí hoa hồng</div>
                        <div style="font-size:26px; font-weight:bold; color:white;">{total_commission:,.0f} ₫</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<br><br>", unsafe_allow_html=True)

            # ---- VẼ BIỂU ĐỒ ----
            # ---- TÍNH TOÁN DỮ LIỆU ----
            order_col = "Order/adjustment ID"
            chart_df = (
                df_income.groupby("Substatus")[order_col]
                .nunique()
                .reset_index()
                .rename(columns={order_col: "Đơn hàng (không trùng)"})
            )
            # Tính tổng đơn ban đầu
            total_orders = chart_df["Đơn hàng (không trùng)"].sum()
            chart_df["Phần trăm"] = round(
                chart_df["Đơn hàng (không trùng)"] / total_orders * 100, 1)
            fig = px.pie(
                chart_df,
                names="Substatus",
                values="Đơn hàng (không trùng)",
                color="Substatus",
                color_discrete_map={
                    "Completed": "#009933",
                    "Canceled": "#FF3333",
                    "Returned": "#F8CB00",
                },
                hole=0.35
            )
            fig.update_traces(
                text=[f"{p:.0f}%" for p in chart_df["Phần trăm"]],
                textinfo="label+text",
                textfont_size=14,
                pull=[0.02 if s == "Returned" else 0 for s in chart_df["Substatus"]],
                hovertemplate="%{label}: %{value} đơn<br>Phần trăm: %{text}<extra></extra>"
            )
            fig.update_layout(
                title_text=" ",
                title_font_size=16,
                legend_title_text="Substatus",
                legend_font_size=14,
                margin=dict(t=120, b=40, l=40, r=40),
                width=300,
                height=450
            )

            # ---- Các chi phí trên Sàn TikTok ----
            fee_cols = [
                "Transaction fee", "TikTok Shop commission fee",
                "Seller shipping fee", "Actual shipping fee",
                "Platform shipping fee discount", "Customer shipping fee",
                "Actual return shipping fee", "Refunded customer shipping fee",
                "SFR reimbursement", "Failed delivery subsidy", "Shipping subsidy",
                "Affiliate Commission", "Affiliate commission before PIT (personal income tax)",
                "Personal income tax withheld from affiliate commission",
                "Affiliate Shop Ads commission", "Affiliate Shop Ads commission before PIT",
                "Personal income tax withheld from affiliate Shop Ads commission",
                "Affiliate partner commission", "Affiliate commission deposit",
                "Affiliate commission refund", "Affiliate Partner shop ads commission",
                "SFP service fee", "Bonus cashback service fee",
                "LIVE Specials service fee", "Voucher Xtra service fee",
                "Order processing fee", "EAMS Program service fee",
                "Flash Sale service fee", "VAT withheld by TikTok Shop",
                "PIT withheld by TikTok Shop", "TikTok PayLater program fee",
                "Campaign resource fee", "SFR service fee", "Ajustment amount"
            ]

            fee_sums = df_income[fee_cols].sum().reset_index()
            fee_sums.columns = ["Loại chi phí", "Tổng tiền"]
            fee_sums = fee_sums[fee_sums["Tổng tiền"] != 0]
            fig_fee = px.bar(
                fee_sums,
                x="Tổng tiền",
                y="Loại chi phí",
                orientation="h",
                title="📦 Tổng hợp chi phí theo loại (Các loại chi phí khác 0)",
                labels={
                    "Tổng tiền": "Tổng tiền (₫)", "Loại chi phí": "Danh mục chi phí"},
            )
            fig_fee.update_layout(
                height=900,  # Cho 34 cột nhìn dễ
                xaxis_tickformat=",",
            )

            # ---- Biểu đồ số lượng hoàn thành ----
            df_chart = st.session_state.df_ket_qua.copy()
            fig_completed = px.bar(
                df_chart,
                x="sku",
                y="hoan_thanh",
                title="Số lượng hoàn thành theo từng SKU",
                color="sku",
                labels={"sku": "SKU", "hoan_thanh": "Số lượng"},
                text_auto=True
            )
            fig_completed.update_layout(
                xaxis_tickangle=-45,
                height=500,
                margin=dict(t=50, b=50)
            )

            # ---- Biểu đồ theo khu vực ----
            region_df = (
                df_merged.groupby("Province")["Order/adjustment ID"]
                .nunique()
                .reset_index()
                .rename(columns={"Order/adjustment ID": "Đơn hàng"})
            )
            fig_pie = px.pie(
                region_df,
                names="Province",
                values="Đơn hàng",
                title="Tỷ lệ đơn hàng theo tỉnh",
                hole=0.35,
            )
            fig_pie.update_traces(
                textinfo="percent+label",
                pull=[0.03]*len(region_df),
            )
            fig_pie.update_layout(
                height=480,
                margin=dict(t=120, b=80),
            )

            # 🔥 Lấy Top 10 Buyer nhiều đơn nhất
            buyer_df = (
                df_merged.groupby("Buyer Username")["Order/adjustment ID"]
                .nunique()
                .reset_index()
                .rename(columns={"Order/adjustment ID": "Đơn hàng"})
            )
            buyer_top10 = buyer_df.nlargest(10, "Đơn hàng")
            fig_buyer_10 = px.bar(
                buyer_top10,
                x="Buyer Username",
                y="Đơn hàng",
                title="Số lượng đơn theo từng Buyer",
                color="Buyer Username",
                labels={"Buyer Username": "Khách mua", "Đơn hàng": "Số đơn"},
                text_auto=True
            )
            fig_buyer_10.update_layout(
                xaxis_tickangle=-45,
                height=500,
                margin=dict(t=50, b=50)
            )

            # ---- Biểu đồ số lượng đơn theo Buyer ----
            st.markdown("### 📊 Phân bố trạng thái đơn hàng")
            st.plotly_chart(fig)

            st.markdown("### 📊 Biểu đồ số lượng sản phẩm hoàn thành")
            st.plotly_chart(fig_completed)

            st.markdown("### 🥧 Biểu đồ tỷ lệ đơn hàng theo khu vực")
            st.plotly_chart(fig_pie)

            st.markdown("### 📊 Biểu đồ số lượng đơn của Khách mua")
            st.plotly_chart(fig_buyer_10)

            st.plotly_chart(fig_fee, use_container_width=True)

            # ---- Lấy thông tin ghi vafp GGSHEET ----
            fill_ggsheet = pd.DataFrame([{
                "Ngày thanh toán": day_of_data,
                "Tổng doanh thu": total_revenue,
                "Tổng quyết toán": total_settlement,
                "Tổng chi phí sàn": total_fees,
                "Thuế VAT đã đóng": total_VAT,
                "Thuế GTGT đã đóng": total_GTGT,
                "Chi phí khác": extra_cost,
                "Lợi nhuận ròng": profit,
                "Chi phí hoa hồng": total_commission,
            }])

            st.session_state["fill_ggsheet"] = (fill_ggsheet)

            st.markdown("### 📄 Bảng thống kê SKU")
            st.dataframe(st.session_state.df_ket_qua)

            st.markdown("### 📄 Danh sách đơn hàng")
            st.dataframe(st.session_state.df_merged)

        if st.button("📤 Ghi dữ liệu doanh thu vào Google Sheet"):
            with result_box:
                with st.spinner("⏳ Đang ghi dữ liệu..."):
                    spreadsheet = client.open_by_url(
                        "https://docs.google.com/spreadsheets/d/1NVQBCT3wt-F7XC9SeMuYvKiOibzaRBg0ZivH8sORW2E/edit?usp=sharing"
                    )
                    worksheet = spreadsheet.worksheet("Trang tính1")
                    existing_data = worksheet.get_all_values()
                    next_row_index = None
                    for i in range(1, len(existing_data)):
                        if all(cell.strip() == "" for cell in existing_data[i]):
                            next_row_index = i + 1
                            break
                    if next_row_index is None:
                        next_row_index = len(existing_data) + 1

                    from gspread_dataframe import set_with_dataframe
                    df_to_write = pd.DataFrame([{
                        col: clean_value(val)
                        for col, val in zip(
                            st.session_state["fill_ggsheet"].columns,
                            st.session_state["fill_ggsheet"].iloc[0]
                        )
                    }])

                    set_with_dataframe(
                        worksheet, df_to_write,
                        row=next_row_index,
                        include_column_header=False
                    )

            with result_box:
                st.success("✅ Dữ liệu đã được ghi vào Google Sheet!")
