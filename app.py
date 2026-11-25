import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO

# ---------------------- KONFIGURASI ----------------------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1dvBa8cxSOsagz_nLJl8qp1rGO7mPHg1_Sn22HXwa2xE/edit?usp=sharing"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ---------------------- FUNGSI KONEKSI ----------------------
# ---------------------- FUNGSI KONEKSI ----------------------
@st.cache_resource(show_spinner="Menghubungkan ke Google Sheet...")
def connect_to_sheets():
    try:
        # Cek apakah berjalan di Streamlit Cloud
        if "private_key" in st.secrets:
            # Bangun kredensial dari Secrets
            credentials_dict = {
                "type": st.secrets["type"],
                "project_id": st.secrets["project_id"],
                "private_key_id": st.secrets["private_key_id"],
                "private_key": st.secrets["private_key"].replace("\\n", "\n"),
                "client_email": st.secrets["client_email"],
                "client_id": st.secrets["client_id"],
                "auth_uri": st.secrets["auth_uri"],
                "token_uri": st.secrets["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["client_x509_cert_url"],
                "universe_domain": st.secrets["universe_domain"]
            }
            credentials = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        else:
            # Baca dari file lokal untuk pengembangan di komputer
            credentials = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        
        gc = gspread.authorize(credentials)
        sht = gc.open_by_url(SPREADSHEET_URL)
        worksheet = sht.sheet1
        return worksheet
    except Exception as e:
        st.error(f"❌ Gagal terhubung ke Google Sheet: {e}")
        return None


# ---------------------- FUNGSI DATA ----------------------
def load_transactions(worksheet):
    try:
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["tanggal", "in_out", "type_cost", "wbs_cost", "uraian", "rupiah", "keterangan"])
        df = pd.DataFrame(data)
        if "rupiah" in df.columns:
            df["rupiah"] = pd.to_numeric(df["rupiah"], errors="coerce")
        return df
    except Exception as e:
        return pd.DataFrame(columns=["tanggal", "in_out", "type_cost", "wbs_cost", "uraian", "rupiah", "keterangan"])

def save_transaction(worksheet, tanggal, in_out, type_cost, wbs_cost, uraian, rupiah, keterangan):
    try:
        header = worksheet.row_values(1)
        if not header or header == []:
            worksheet.append_row(["tanggal", "in_out", "type_cost", "wbs_cost", "uraian", "rupiah", "keterangan"])
        
        worksheet.append_row([tanggal, in_out, type_cost, wbs_cost, uraian, rupiah, keterangan])
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")
        return False

# ---------------------- FUNGSI: TAMPILKAN LOGO POJOK KANAN ATAS ----------------------
def add_logo_to_header(logo_path, width_scale=2.0):
    """Menampilkan logo di pojok kanan atas halaman"""
    try:
        logo = Image.open(logo_path)
        # Konversi ke base64 untuk tampil di HTML
        buffered = BytesIO()
        logo.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Hitung lebar logo — sekitar 2x ukuran ikon teks
        logo_width_px = int(40 * width_scale)  # 24px = kira-kira ukuran ikon emoji
        
        # Tampilkan logo di kanan atas menggunakan CSS
        st.markdown(f"""
            <style>
                .header-container {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    width: 100%;
                }}
                .logo-img {{
                    width: {logo_width_px}px;
                    height: auto;
                }}
            </style>
            <div class="header-container">
                <h1>📒 Jurnal Kas — Usaha Mitra Matera</h1>
                <img src="data:image/png;base64,{img_str}" class="logo-img" alt="Logo Mitra Matera">
            </div>
            <hr>
        """, unsafe_allow_html=True)
    except FileNotFoundError:
        # Jika file logo tidak ditemukan, tampilkan judul biasa
        st.title("📒 Jurnal Kas — Usaha Mitra Matera")
        st.markdown("---")
        st.warning("⚠️ File `logo.png` tidak ditemukan di folder proyek — logo tidak ditampilkan")

# ---------------------- HALAMAN UTAMA ----------------------
st.set_page_config(page_title="Mitra Matera - Jurnal Kas", page_icon="💰", layout="wide")

# Tampilkan Judul + Logo
add_logo_to_header("logo.png", width_scale=2.0)

worksheet = connect_to_sheets()
if not worksheet:
    st.stop()

tab1, tab2 = st.tabs(["✏️ Catat Transaksi", "📊 Dashboard"])

# ====================== TAB 1: CATAT TRANSAKSI ======================
with tab1:
    st.subheader("Catat Transaksi Baru")
    
    with st.form("form_transaksi", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            tanggal = st.date_input("Tanggal Transaksi", value=datetime.today())
            in_out = st.radio("Jenis Transaksi", ["MASUK", "KELUAR"])
            type_cost = st.selectbox("Jenis Biaya (type_cost)", [
                "Peralatan", "Bahan Masakan Pokok", "Bahan Masakan Pendukung", 
                "Transportasi", "Ongkos Jasa"
            ])
        
        with col2:
            wbs_cost = st.selectbox("Kategori (wbs_cost)", ["Operasional", "Aset", "Infrastruktur"])
            rupiah = st.number_input("Nilai Transaksi (Rp)", min_value=0, step=1000)
        
        uraian = st.text_input("Uraian / Penjelasan")
        keterangan = st.text_area("Keterangan Tambahan (opsional)")
        
        submit = st.form_submit_button("💾 Simpan Transaksi", type="primary")
        
        if submit:
            if rupiah <= 0:
                st.error("❌ Nilai transaksi harus lebih dari 0!")
            elif not uraian:
                st.warning("⚠️ Mohon isi uraian transaksi")
            else:
                tanggal_str = tanggal.strftime("%Y-%m-%d")
                berhasil = save_transaction(
                    worksheet, tanggal_str, in_out, type_cost, 
                    wbs_cost, uraian, rupiah, keterangan
                )
                if berhasil:
                    st.success("✅ Transaksi berhasil disimpan!")
                    st.balloons()
                    st.cache_resource.clear()

# ====================== TAB 2: DASHBOARD ======================
with tab2:
    st.subheader("📊 Dashboard Data Transaksi")
    
    df = load_transactions(worksheet)
    
    if df.empty:
        st.info("📭 Belum ada data transaksi. Silakan catat transaksi pertama Anda di tab 'Catat Transaksi'!")
    else:
        # ---------------- FILTER ----------------
        st.markdown("### 🔍 Filter Data")
        
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        # Filter In/Out
        with col_f1:
            filter_inout = st.selectbox("Transaksi", ["Semua", "MASUK", "KELUAR"])
        
        # Filter Tanggal
        with col_f2:
            if "tanggal" in df.columns and not df["tanggal"].isna().all():
                df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
                min_tgl = df["tanggal"].min().date()
                max_tgl = df["tanggal"].max().date()
                tgl_mulai = st.date_input("Tanggal Mulai", value=min_tgl, min_value=min_tgl, max_value=max_tgl)
                tgl_akhir = st.date_input("Tanggal Akhir", value=max_tgl, min_value=min_tgl, max_value=max_tgl)
            else:
                tgl_mulai = st.date_input("Tanggal Mulai", value=datetime.today())
                tgl_akhir = st.date_input("Tanggal Akhir", value=datetime.today())
        
        # Filter type_cost
        with col_f3:
            daftar_type = ["Semua"] + sorted(df["type_cost"].dropna().unique().tolist())
            filter_type = st.selectbox("Jenis Biaya", daftar_type)
        
        # Filter wbs_cost
        with col_f4:
            daftar_wbs = ["Semua"] + sorted(df["wbs_cost"].dropna().unique().tolist())
            filter_wbs = st.selectbox("Kategori", daftar_wbs)
        
        # Terapkan Filter
        df_filtered = df.copy()
        
        if filter_inout != "Semua":
            df_filtered = df_filtered[df_filtered["in_out"] == filter_inout]
        
        if "tanggal" in df.columns:
            tgl_mulai_str = tgl_mulai.strftime("%Y-%m-%d")
            tgl_akhir_str = tgl_akhir.strftime("%Y-%m-%d")
            df_filtered = df_filtered[
                (df_filtered["tanggal"] >= tgl_mulai_str) & 
                (df_filtered["tanggal"] <= tgl_akhir_str)
            ]
        
        if filter_type != "Semua":
            df_filtered = df_filtered[df_filtered["type_cost"] == filter_type]
        
        if filter_wbs != "Semua":
            df_filtered = df_filtered[df_filtered["wbs_cost"] == filter_wbs]
        
        # ---------------- RINGKASAN ANGKA ----------------
        st.markdown("---")
        st.markdown("### 📈 Ringkasan")
        
        total_masuk = df_filtered[df_filtered["in_out"] == "MASUK"]["rupiah"].sum()
        total_keluar = df_filtered[df_filtered["in_out"] == "KELUAR"]["rupiah"].sum()
        saldo = total_masuk - total_keluar
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Total Masuk", f"Rp {total_masuk:,.0f}")
        c2.metric("💸 Total Keluar", f"Rp {total_keluar:,.0f}")
        c3.metric("🏦 Saldo", f"Rp {saldo:,.0f}", 
                  delta=("Positif" if saldo >=0 else "Negatif"),
                  delta_color="normal" if saldo >=0 else "inverse")
        
        # ---------------- TABEL DATA ----------------
        st.markdown("---")
        st.markdown(f"### 📋 Daftar Transaksi — {len(df_filtered)} data ditemukan")
        
        tampil_kolom = ["tanggal", "in_out", "type_cost", "wbs_cost", "uraian", "rupiah", "keterangan"]
        st.dataframe(df_filtered[tampil_kolom], width="stretch", hide_index=True)
        
        # ---------------- GRAFIK ----------------
        st.markdown("---")
        st.markdown("### 📊 Grafik")
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("Berdasarkan Jenis Biaya")
            df_chart1 = df_filtered.groupby("type_cost")["rupiah"].sum().reset_index()
            if not df_chart1.empty:
                st.bar_chart(df_chart1, x="type_cost", y="rupiah", width="stretch")
            else:
                st.info("Tidak ada data")
        
        with col_g2:
            st.subheader("Berdasarkan Kategori")
            df_chart2 = df_filtered.groupby("wbs_cost")["rupiah"].sum().reset_index()
            if not df_chart2.empty:
                st.bar_chart(df_chart2, x="wbs_cost", y="rupiah", color="#e74c3c", width="stretch")
            else:
                st.info("Tidak ada data")

# ---------------------- FOOTER ----------------------
st.markdown("---")
st.caption("🔄 Data disimpan di Google Sheet: MtrJurnalCash | Aplikasi Pembukuan Mitra Matera")
