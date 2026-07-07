import streamlit as st
import pandas as pd
import requests

# Konfigurasi halaman agar tampilan lebar (Wide Mode)
st.set_page_config(page_title="Inventarisasi BMN Sekretariat Badan Pengembangan dan Pembinaan Bahasa", layout="wide")

# URL WEB APP GOOGLE APPS SCRIPT yang sudah Anda sesuaikan untuk POSTING data
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyVCt37xvsX_oiNsw-AX99RW2SC4gU0K0qOMJvcY0909zqGMC1J1eaUbZOMrRI1oOXh/exec"

# URL Google Sheet untuk MENAMPILKAN/MEMBACA data master (format ekspor ke CSV berdasarkan gid=772361074)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1X28Tqn3724QfoEy4quaFQa6Gy90CH4YK4cXfToaCMec/export?format=csv&gid=772361074"

# Fungsi memuat data master dari Google Sheets lewat internet
@st.cache_data(ttl=600)  # Data disimpan di cache selama 10 menit
def load_data():
    try:
        # Membaca data langsung dari URL ekspor CSV Google Sheet
        df = pd.read_csv(SHEET_CSV_URL, dtype=str, on_bad_lines='skip', encoding='utf-8')
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.str.contains('^Unnamed:|^\s*$', case=False, na=True)]
        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets: {e}")
        return None

# Fungsi posting data langsung via Web App URL
def simpan_ke_google_sheets(nup, merk):
    if "PASANG_URL" in WEB_APP_URL:
        st.error("Masukkan URL Web App dari Google Apps Script terlebih dahulu di dalam kode!")
        return False
    try:
        payload = {"nup": nup, "merk": merk}
        response = requests.post(WEB_APP_URL, json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Terjadi kesalahan koneksi ke Google Sheets saat menyimpan: {e}")
        return False

# Memuat database master
df = load_data()

if df is not None:
    st.title("Sistem Inventarisasi Buku Perpustakaan Badan Bahasa 2026")
    st.write("Sistem pencarian buku di seluruh kolom Google Sheet")
    
    # Inisialisasi session state untuk menyimpan data pencarian
    if "df_tabel" not in st.session_state:
        st.session_state.df_tabel = None
    if "kata_kunci" not in st.session_state:
        st.session_state.kata_kunci = ""

    # 1. Menggunakan st.form untuk Input Pencarian
    with st.form(key="search_form", clear_on_submit=False):
        search_query = st.text_input("Input pencarian (NUP, Judul, Kode, ISBN, Barcode, dll):", autocomplete="off").strip()
        submit_button = st.form_submit_button(label="🔍 Cari Data", type="primary")

    # 2. Proses Pencarian di Semua Kolom
    if submit_button:
        if search_query:
            query_clean = search_query.replace(" ", "").replace(".", "").lower()
            
            # Membuat mask/filter untuk memeriksa semua kolom
            # Mengabaikan spasi, titik, dan perbedaan huruf besar/kecil (case-insensitive)
            mask = pd.Series(False, index=df.index)
            for col in df.columns:
                col_clean = df[col].astype(str).str.replace(" ", "", regex=False).str.replace(".", "", regex=False).str.lower()
                mask = mask | col_clean.str.contains(query_clean, na=False)
            
            # Mengambil baris data yang lolos filter mask
            hasil_filter = df[mask].copy()
            
            if not hasil_filter.empty:
                # Menambahkan kolom interaksi 'Kirim' di baris paling akhir
                hasil_filter['Kirim'] = False
                st.session_state.df_tabel = hasil_filter
                st.session_state.kata_kunci = search_query
            else:
                st.session_state.df_tabel = "KOSONG"
        else:
            st.warning("Silakan masukkan kata kunci pencarian terlebih dahulu!")
            st.session_state.df_tabel = None

    # 3. Tampilkan dan Proses Hasil Pencarian
    if st.session_state.df_tabel is not None:
        if isinstance(st.session_state.df_tabel, str) and st.session_state.df_tabel == "KOSONG":
            st.error("Data tidak ditemukan di kolom manapun.")
        elif isinstance(st.session_state.df_tabel, pd.DataFrame):
            
            st.success(f"Ditemukan {len(st.session_state.df_tabel)} baris data yang mengandung kata kunci '{st.session_state.kata_kunci}'")
            
            # Tentukan kolom mana saja yang tidak boleh diedit (selain kolom 'Kirim')
            kolom_terkunci = [col for col in st.session_state.df_tabel.columns if col != 'Kirim']
            
            # Tampilkan seluruh kolom baris data asli secara interaktif
            edited_df = st.data_editor(
                st.session_state.df_tabel,
                use_container_width=True,
                hide_index=True,
                disabled=kolom_terkunci,
                key="editor_buku"
            )
            
            # Pemicu deteksi perubahan tombol centang 'Kirim'
            fitur_ditekan = False
            for i in range(len(edited_df)):
                if edited_df.iloc[i]["Kirim"] == True and st.session_state.df_tabel.iloc[i]["Kirim"] == False:
                    # Mengambil nilai NUP dan Merk/Judul secara dinamis. 
                    # Jika nama kolom di sheet Anda bervariasi, pastikan kolom 'NUP' dan 'Merk' ada di sheet Anda.
                    nup_terpilih = edited_df.iloc[i].get("NUP", "Tanpa NUP")
                    judul_terpilih = edited_df.iloc[i].get("Merk", edited_df.iloc[i].get("Judul", "Tanpa Judul"))
                    
                    # Kunci status di session state agar tidak terkirim ganda
                    st.session_state.df_tabel.at[i, "Kirim"] = True
                    fitur_ditekan = True
                    
                    # Kirim data ke Google Sheets via Apps Script Web App
                    sukses = simpan_ke_google_sheets(nup_terpilih, judul_terpilih)
                    
                    if sukses:
                        st.toast(f"🚀 Terposting ke Google Sheets! NUP: {nup_terpilih} | Item: {judul_terpilih}")
                        
            # Rerun ringan untuk sinkronisasi tampilan checklist setelah diklik
            if fitur_ditekan:
                st.rerun()
