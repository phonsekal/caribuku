import streamlit as st
import pandas as pd

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
    st.write("Sistem pencarian buku di seluruh kolom Google Sheet (Tab: slims)")
    
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
            
            matched_indices = []
            matched_column_names = []
            
            # Cari kata kunci di setiap baris dan kolom
            for idx, row in df.iterrows():
                for col in df.columns:
                    val_clean = str(row[col]).replace(" ", "").replace(".", "").lower()
                    if query_clean in val_clean:
                        matched_indices.append(idx)
                        matched_column_names.append(col)
                        break  # Stop cari di kolom lain untuk baris ini jika sudah ketemu
            
            # Jika data ditemukan
            if matched_indices:
                hasil_filter = df.loc[matched_indices].copy()
                
                # Tambahkan kolom pencocokan kata secara paksa
                hasil_filter['Tempat Ditemukan (Kolom)'] = matched_column_names
                
                # --- PROSES STANDARISASI KOLOM JUDUL ---
                # Cari kolom asli yang bernama 'Merk' atau 'Judul' atau mengandung unsur kata tersebut
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
                # Cari kolom asli yang bernama 'Klasifikasi', 'Kode', atau mengandung kata tersebut
                kolom_kode_asli = None
                for c in hasil_filter.columns:
                    if c.lower() in ['klasifikasi', 'kode', 'kodefikasi'] or 'klasifikasi' in c.lower() or 'kode' in c.lower():
                        kolom_kode_asli = c
                        break
                
                if kolom_kode_asli:
                    hasil_filter['Kodefikasi'] = hasil_filter[kolom_kode_asli]
                else:
                    # Jika di sheet slims tidak ada kolom klasifikasi khusus, kita isi dengan tanda '-'
                    hasil_filter['Kodefikasi'] = "-"

                # --- PACKING 3 KOLOM UTAMA YANG DIMINTA ---
                # Kita buat struktur dataframe baru yang isinya HANYA 3 kolom ini secara mutlak
                df_final = hasil_filter[['Judul', 'Kodefikasi', 'Tempat Ditemukan (Kolom)']].copy()
                
                # Simpan ke session state
                st.session_state.df_tabel = df_final
                st.session_state.kata_kunci = search_query
            else:
                st.session_state.df_tabel = "KOSONG"
        else:
            st.warning("Silakan masukkan kata kunci pencarian terlebih dahulu!")
            st.session_state.df_tabel = None

    # 3. Tampilkan Tiga Kolom Hasil Pencarian secara Read-Only
    if st.session_state.df_tabel is not None:
        if isinstance(st.session_state.df_tabel, str) and st.session_state.df_tabel == "KOSONG":
            st.error("Data tidak ditemukan di kolom manapun pada sheet 'slims'.")
        elif isinstance(st.session_state.df_tabel, pd.DataFrame):
            
            st.success(f"Ditemukan {len(st.session_state.df_tabel)} baris data yang mengandung kata kunci '{st.session_state.kata_kunci}'")
            
            # Menampilkan tabel final yang dijamin berisi 3 kolom
            st.dataframe(
                st.session_state.df_tabel,
                use_container_width=True,
                hide_index=True
            )
