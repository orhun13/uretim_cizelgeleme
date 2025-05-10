
import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.express as px

st.title("Akıllı Üretim Çizelgeleme - Job-Shop Optimizasyonu")

uploaded_file = st.file_uploader("Excel dosyasını yükleyin (BASKI, LAMİNASYON, DİLME sayfaları içermeli)", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    def hazirla(df, ad, makina_kolonu):
        df = df[["Talep Numarası", "Ürün Adı", "Spesifikasyon", makina_kolonu, "Başlangıç", "Bitiş"]].dropna()
        df.columns = ["Talep Numarası", "Ürün Adı", "Spesifikasyon", "Makine", "Başlangıç", "Bitiş"]
        df["Süre (dk)"] = (pd.to_datetime(df["Bitiş"]) - pd.to_datetime(df["Başlangıç"])).dt.total_seconds() / 60
        df["Süreç"] = ad
        return df

    baski = hazirla(xls.parse("BASKI"), "Baskı", "Makine")
    laminasyon = hazirla(xls.parse("LAMİNASYON"), "Laminasyon", "Makine No")
    dilme = hazirla(xls.parse("DİLME"), "Dilme", "Makine NO")

    tum_veri = pd.concat([baski, laminasyon, dilme], ignore_index=True)
    tum_veri = tum_veri.sort_values(by=["Süreç", "Süre (dk)"])

    st.subheader("Optimizasyon Sonucu")

    day_start = pd.Timestamp("2024-01-02 07:00:00")
    available_time = {m: day_start for m in tum_veri["Makine"].unique()}
    product_last_time = {}
    optimized_rows = []

    for _, row in tum_veri.iterrows():
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
    st.success(f"Toplam Makespan: {makespan:.2f} dakika (~{makespan/60:.2f} saat)")

    if st.checkbox("Gantt grafiğini göster"):
        fig = px.timeline(sonuc_df, x_start="Optimize Başlangıç", x_end="Optimize Bitiş",
                          y="Ürün Adı", color="Süreç", title="Gantt Çizelgesi")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
