import streamlit as st
import pandas as pd

# Konfigurasi halaman agar tampilan lebar (Wide Mode)
st.set_page_config(page_title="Inventarisasi BMN Sekretariat Badan Pengembangan dan Pembinaan Bahasa", layout="wide")

# URL Google Sheet BARU yang diarahkan khusus untuk mengekspor tab/sheet "slims"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/17QsetCX0AX_u4w4fQbCxH6yOXXuinAfeVfe9acvkHiE/export?format=csv&sheet=slims"

# Fungsi memuat data master dari Google Sheets lewat internet
@st.cache_data(ttl=600)  # Data disimpan di cache selama 10 menit
def load_data():
    try:
        # Membaca data langsung dari URL ekspor CSV Google Sheet Baru (Tab: slims)
        df = pd.read_csv(SHEET_CSV_URL, dtype=str, on_bad_lines='skip', encoding='utf-8')
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.str.contains('^Unnamed:|^\s*$', case=False, na=True)]
        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari Sheet 'slims': {e}")
        return None

# Memuat database master
df = load_data()

if df is not None:
    st.title("Sistem Inventarisasi Buku Perpustakaan Badan Bahasa 2026")
    st.write("Sistem pencarian buku di seluruh kolom Google Sheet Baru (Tab: slims)")
    
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
            
            # Membuat mask/filter untuk memeriksa semua kolom pada sheet slims
            mask = pd.Series(False, index=df.index)
            for col in df.columns:
                col_clean = df[col].astype(str).str.replace(" ", "", regex=False).str.replace(".", "", regex=False).str.lower()
                mask = mask | col_clean.str.contains(query_clean, na=False)
            
            # Mengambil baris data yang lolos filter mask
            hasil_filter = df[mask].copy()
            
            if not hasil_filter.empty:
                # Mengubah nama kolom 'Merk' menjadi 'Judul' jika ada (untuk estetika tampilan)
                if 'Merk' in hasil_filter.columns:
                    hasil_filter = hasil_filter.rename(columns={'Merk': 'Judul'})
                
                # Menentukan kolom yang akan ditampilkan
                kolom_tampil = []
                
                # Cek ketersediaan kolom Judul / Merk / nama kolom alternatif yang mirip
                if 'Judul' in hasil_filter.columns:
                    kolom_tampil.append('Judul')
                elif 'Merk' in hasil_filter.columns:
                    kolom_tampil.append('Merk')
                else:
                    kolom_judul_alt = [c for c in hasil_filter.columns if 'judul' in c.lower() or 'nama' in c.lower()]
                    if kolom_judul_alt:
                        hasil_filter = hasil_filter.rename(columns={kolom_judul_alt[0]: 'Judul'})
                        kolom_tampil.append('Judul')
                
                # Cek ketersediaan kolom Klasifikasi
                if 'Klasifikasi' in hasil_filter.columns:
                    kolom_tampil.append('Klasifikasi')
                else:
                    kolom_klasifikasi_alt = [c for c in hasil_filter.columns if 'klasifikasi' in c.lower() or 'kode' in c.lower()]
                    if kolom_klasifikasi_alt:
                        hasil_filter = hasil_filter.rename(columns={kolom_klasifikasi_alt[0]: 'Klasifikasi'})
                        kolom_tampil.append('Klasifikasi')
                    else:
                        # Jika benar-benar tidak ada, buat kolom kosong agar tidak error
                        hasil_filter['Klasifikasi'] = "-"
                        kolom_tampil.append('Klasifikasi')
                
                # Memotong dataframe berdasarkan kolom yang valid ditemukan
                st.session_state.df_tabel = hasil_filter[kolom_tampil]
                st.session_state.kata_kunci = search_query
            else:
                st.session_state.df_tabel = "KOSONG"
        else:
            st.warning("Silakan masukkan kata kunci pencarian terlebih dahulu!")
            st.session_state.df_tabel = None

    # 3. Tampilkan Hasil Pencarian (Hanya Judul dan Klasifikasi secara Read-Only)
    if st.session_state.df_tabel is not None:
        if isinstance(st.session_state.df_tabel, str) and st.session_state.df_tabel == "KOSONG":
            st.error("Data tidak ditemukan di kolom manapun pada sheet 'slims'.")
        elif isinstance(st.session_state.df_tabel, pd.DataFrame):
            
            st.success(f"Ditemukan {len(st.session_state.df_tabel)} baris data yang mengandung kata kunci '{st.session_state.kata_kunci}'")
            
            # Jika kolom Klasifikasi terpaksa di-generate manual karena tidak ada kecocokan nama kolom asli
            if 'Klasifikasi' in st.session_state.df_tabel.columns and (st.session_state.df_tabel['Klasifikasi'] == "-").all() and 'Klasifikasi' not in df.columns:
                st.warning("Catatan: Kolom Klasifikasi / Kode tidak terdeteksi secara otomatis di sheet 'slims'.")

            # Tampilkan tabel data hasil filter
            st.dataframe(
                st.session_state.df_tabel,
                use_container_width=True,
                hide_index=True
            )
