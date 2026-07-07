import streamlit as st
import pandas as pd
import numpy as np

# Konfigurasi halaman agar tampilan lebar (Wide Mode)
st.set_page_config(page_title="Inventarisasi BMN Sekretariat Badan Pengembangan dan Pembinaan Bahasa", layout="wide")

# URL Google Sheet Baru yang diarahkan khusus untuk mengekspor tab/sheet "slims"
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
    st.write("Sistem pencarian cepat buku di seluruh kolom Google Sheet (Tab: slims)")
    
    # Inisialisasi session state untuk menyimpan data pencarian
    if "df_tabel" not in st.session_state:
        st.session_state.df_tabel = None
    if "kata_kunci" not in st.session_state:
        st.session_state.kata_kunci = ""

    # 1. Menggunakan st.form untuk Input Pencarian
    with st.form(key="search_form", clear_on_submit=False):
        search_query = st.text_input("Input pencarian (NUP, Judul, Kode, ISBN, Barcode, dll):", autocomplete="off").strip()
        submit_button = st.form_submit_button(label="🔍 Cari Data", type="primary")

    # 2. Proses Pencarian Vektor (Super Cepat)
    if submit_button:
        if search_query:
            query_clean = search_query.replace(" ", "").replace(".", "").lower()
            
            # 1. Buat replika dataframe yang sudah bersih untuk dicocokkan (Matriks)
            df_cleaned = df.astype(str).apply(lambda s: s.str.replace(" ", "", regex=False).str.replace(".", "", regex=False).str.lower())
            
            # 2. Cari sel mana saja yang mengandung kata kunci
            mask_match = df_cleaned.apply(lambda s: s.str.contains(query_clean, na=False))
            
            # 3. Ambil baris mana saja yang minimal ada 1 sel cocok
            rows_matched = mask_match.any(axis=1)
            
            if rows_matched.any():
                # Filter data asli berdasarkan baris yang cocok
                hasil_filter = df[rows_matched].copy()
                mask_match_filtered = mask_match[rows_matched]
                
                # 4. Ambil nilai sel asli pertama yang cocok pada tiap baris menggunakan numpy
                col_indices = mask_match_filtered.values.argmax(axis=1)
                matched_values = hasil_filter.values[np.arange(len(hasil_filter)), col_indices]
                hasil_filter['Kata yang Dicari'] = matched_values
                
                # --- PROSES STANDARISASI KOLOM JUDUL ---
                kolom_judul_asli = None
                for c in hasil_filter.columns:
                    if c.lower() in ['merk', 'judul'] or 'judul' in c.lower() or 'nama' in c.lower():
                        kolom_judul_asli = c
                        break
                
                if kolom_judul_asli:
                    hasil_filter['Judul'] = hasil_filter[kolom_judul_asli]
                else:
                    hasil_filter['Judul'] = "Kolom Judul Tidak Terdeteksi"

                # --- PROSES STANDARISASI KOLOM KODEFIKASI ---
                kolom_kode_asli = None
                for c in hasil_filter.columns:
                    if c.lower() in ['klasifikasi', 'kode', 'kodefikasi'] or 'klasifikasi' in c.lower() or 'kode' in c.lower():
                        kolom_kode_asli = c
                        break
                
                if kolom_kode_asli:
                    hasil_filter['Kodefikasi'] = hasil_filter[kolom_kode_asli]
                else:
                    hasil_filter['Kodefikasi'] = "-"

                # --- PROSES STANDARISASI KOLOM TAHUN TERBIT ---
                kolom_tahun_asli = None
                for c in hasil_filter.columns:
                    if 'tahun' in c.lower() or 'terbit' in c.lower() or 'thn' in c.lower():
                        kolom_tahun_asli = c
                        break
                
                if kolom_tahun_asli:
                    hasil_filter['Tahun Terbit'] = hasil_filter[kolom_tahun_asli]
                else:
                    hasil_filter['Tahun Terbit'] = "-"

                # --- PACKING 4 KOLOM UTAMA YANG DIMINTA ---
                df_final = hasil_filter[['Judul', 'Kodefikasi', 'Tahun Terbit', 'Kata yang Dicari']].copy()
                
                # Simpan ke session state
                st.session_state.df_tabel = df_final
                st.session_state.kata_kunci = search_query
            else:
                st.session_state.df_tabel = "KOSONG"
        else:
            st.warning("Silakan masukkan kata kunci pencarian terlebih dahulu!")
            st.session_state.df_tabel = None

    # 3. Tampilkan Empat Kolom Hasil Pencarian secara Read-Only
    if st.session_state.df_tabel is not None:
        if isinstance(st.session_state.df_tabel, str) and st.session_state.df_tabel == "KOSONG":
            st.error("Data tidak ditemukan di kolom manapun pada sheet 'slims'.")
        elif isinstance(st.session_state.df_tabel, pd.DataFrame):
            
            st.success(f"Ditemukan {len(st.session_state.df_tabel)} baris data yang mengandung kata kunci '{st.session_state.kata_kunci}'")
            
            # Menampilkan tabel final berisi 4 kolom
            st.dataframe(
                st.session_state.df_tabel,
                use_container_width=True,
                hide_index=True
            )
