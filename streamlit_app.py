
import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.express as px

st.title("Gün Bazlı Üretim Çizelgeleme - Job-shop Optimizasyonu")

def kontrol_et_zaman(df, sayfa_adi):
    df['Başlangıç_Parsed'] = pd.to_datetime(df['Başlangıç'], errors='coerce')
    df['Bitiş_Parsed'] = pd.to_datetime(df['Bitiş'], errors='coerce')
    hatali = df[df['Başlangıç_Parsed'].isna() | df['Bitiş_Parsed'].isna()]
    
    if not hatali.empty:
        st.warning(f"⚠️ {sayfa_adi} sayfasında hatalı zaman formatı içeren {len(hatali)} satır bulundu. Bu satırlar atlanacaktır.")
        with st.expander(f"{sayfa_adi} sayfasındaki hatalı satırları göster"):
            st.dataframe(hatali[['Talep Numarası', 'Ürün Adı', 'Başlangıç', 'Bitiş']])

    df = df.dropna(subset=['Başlangıç_Parsed', 'Bitiş_Parsed']).copy()
    df['Başlangıç'] = df['Başlangıç_Parsed']
    df['Bitiş'] = df['Bitiş_Parsed']
    df.drop(columns=['Başlangıç_Parsed', 'Bitiş_Parsed'], inplace=True)
    return df

def hazirla(df, sayfa_adi, makina_kolonu):
    df = df[["Talep Numarası", "Ürün Adı", "Spesifikasyon", makina_kolonu, "Başlangıç", "Bitiş"]].dropna(subset=["Başlangıç", "Bitiş"])
    df.columns = ["Talep Numarası", "Ürün Adı", "Spesifikasyon", "Makine", "Başlangıç", "Bitiş"]
    df = kontrol_et_zaman(df, sayfa_adi)
    df["Süre (dk)"] = (df["Bitiş"] - df["Başlangıç"]).dt.total_seconds() / 60
    df["Süreç"] = sayfa_adi
    return df

uploaded_file = st.file_uploader("Excel dosyasını yükleyin (BASKI, LAMİNASYON, DİLME sayfaları içermeli)", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    baski = hazirla(xls.parse("BASKI"), "Baskı", "Makine")
    laminasyon = hazirla(xls.parse("LAMİNASYON"), "Laminasyon", "Makine No")
    dilme = hazirla(xls.parse("DİLME"), "Dilme", "Makine NO")

    tum_veri = pd.concat([baski, laminasyon, dilme], ignore_index=True)
    tum_veri["Gün"] = tum_veri["Başlangıç"].dt.date

    st.subheader("Gün Seç")
    secilen_gun = st.selectbox("İşlem yapılacak günü seçin:", sorted(tum_veri["Gün"].unique()))

    gunluk_veri = tum_veri[
    (tum_veri["Başlangıç"].dt.date == secilen_gun) &
    (tum_veri["Bitiş"].dt.date == secilen_gun)
].copy()
    gunluk_veri = gunluk_veri.sort_values(by=["Süreç", "Süre (dk)"])

    st.subheader(f"{secilen_gun} günü için optimizasyon sonucu")

    day_start = pd.Timestamp(f"{secilen_gun} 07:00:00")
    available_time = {m: day_start for m in gunluk_veri["Makine"].unique()}
    product_last_time = {}
    optimized_rows = []

    for _, row in gunluk_veri.iterrows():
        talep = row["Talep Numarası"]
        makine = row["Makine"]
        süre = timedelta(minutes=row["Süre (dk)"])
        süreç = row["Süreç"]

        if talep in product_last_time:
            ready_time = product_last_time[talep]
        else:
            ready_time = day_start

        start = max(available_time[makine], ready_time)
        end = start + süre

        available_time[makine] = end + timedelta(minutes=5)
        product_last_time[talep] = end + timedelta(minutes=5)

        optimized_rows.append({
            "Talep Numarası": talep,
            "Ürün Adı": row["Ürün Adı"],
            "Süreç": süreç,
            "Makine": makine,
            "Optimize Başlangıç": start,
            "Optimize Bitiş": end,
            "Süre (dk)": row["Süre (dk)"]
        })

    sonuc_df = pd.DataFrame(optimized_rows)
    st.dataframe(sonuc_df)

    makespan = (sonuc_df["Optimize Bitiş"].max() - day_start).total_seconds() / 60
    st.success(f"{secilen_gun} günü için Makespan: {makespan:.2f} dakika (~{makespan/60:.2f} saat)")

    if st.checkbox("Gantt grafiğini göster"):
        fig = px.timeline(sonuc_df, x_start="Optimize Başlangıç", x_end="Optimize Bitiş",
                          y="Ürün Adı", color="Süreç", title=f"{secilen_gun} Gantt Çizelgesi")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
