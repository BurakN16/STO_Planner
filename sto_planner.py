import streamlit as st
import pandas as pd
import io
from solver import solve_assignment

st.set_page_config(layout="wide")
st.markdown("""
    <style>
        div[data-testid="stDataFrame"] div[role="gridcell"] {
            font-family: Calibri, sans-serif;
            font-size: 9pt;
        }
        .dataframe {
            font-family: Calibri, sans-serif;
            font-size: 9pt;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🚛 STO Araç Planlama")

uploaded_file = st.file_uploader("📤 Sipariş dosyasını yükleyin (Excel)", type=["xlsx"])

if uploaded_file:
    order_df = pd.read_excel(uploaded_file)
    st.subheader("📝 Yüklenen Sipariş Verisi")
    st.dataframe(order_df, use_container_width=True, height=400)

    expected_cols = ['Shipping Point/Receiving Pt', 'Ship-to party', 'CPallet', 'CPallet_M3', 'CPallet_Gross', 'PALTypeChoice']
    missing = [col for col in expected_cols if col not in order_df.columns]

    if missing:
        st.error(f"❌ Eksik kolon(lar): {missing}")
    else:
        # === PALTypeChoice eksik veri kontrolü ===
        st.subheader("📋 Palet Tipi Kontrolü")
        if order_df['PALTypeChoice'].isnull().any():
            st.error("❗ Material datasında eksiklik var. 'PALTypeChoice' sütununda boş değerler mevcut.")
            st.markdown("Boş değerli satır sayısı: **{}**".format(order_df['PALTypeChoice'].isnull().sum()))
        else:
            st.success("✅ Tüm sipariş satırlarında 'PALTypeChoice' bilgisi mevcut.")

        if st.button("✅ Araca Atamaları Yap"):
            try:
                assigned_df = solve_assignment(order_df)

                if assigned_df is None or assigned_df.empty:
                    st.warning("⚠️ Atama sonuçları boş. Verileri ve PALTypeChoice sütununu kontrol edin.")
                    st.write("🔍 PALTypeChoice örnekleri:", order_df['PALTypeChoice'].dropna().unique().tolist())
                    st.write("🔍 İlk 10 EffectivePallet:", order_df.get('EffectivePallet', 'Yok'))
                else:
                    st.subheader("🚚 Atama Sonuçları")
                    st.dataframe(assigned_df, use_container_width=True, height=500)

                    # === Araç Bazlı Özet ===
                    summary = assigned_df.groupby("Assigned_Truck").agg({
                        'CPallet': 'sum',
                        'CPallet_M3': 'sum',
                        'CPallet_Gross': 'sum',
                        'EffectivePallet': 'sum'
                    }).reset_index()

                    summary['DolulukOrani_Pallet'] = (summary['EffectivePallet'] / 33) * 100
                    summary['DolulukOrani_Volume'] = (summary['CPallet_M3'] / 82) * 100
                    summary['DolulukOrani_Weight'] = (summary['CPallet_Gross'] / 24000) * 100

                    def renk_kodla(deger):
                        if deger >= 95:
                            return 'background-color: lightgreen'
                        elif deger >= 70:
                            return 'background-color: yellow'
                        else:
                            return 'background-color: lightcoral'

                    styled_summary = summary.style \
                        .applymap(renk_kodla, subset=['DolulukOrani_Pallet']) \
                        .format({
                            'DolulukOrani_Pallet': "{:.1f}%",
                            'DolulukOrani_Volume': "{:.1f}%",
                            'DolulukOrani_Weight': "{:.1f}%"
                        })

                    st.subheader("📊 Araç Bazlı Özet")
                    st.dataframe(styled_summary, use_container_width=True, height=500)

                    # === Sipariş Bazlı Atama Özeti ===
                    try:
                        siparis_ozet = assigned_df.groupby([
                            'Assigned_Truck',
                            'Location of the ship-to party',
                            'Purchasing Document',
                            'Deliv. date(From/to)',
                            'Delivery',
                            'Temp_Type'
                        ]).agg({
                            'CPallet': 'sum',
                            'EffectivePallet': 'sum',
                            'CPallet_M3': 'sum'
                        }).reset_index()

                        siparis_ozet = siparis_ozet.rename(columns={
                            'CPallet': 'Sum of CPallet',
                            'EffectivePallet': 'Sum of EffectivePallet',
                            'CPallet_M3': 'Sum of CPallet_M3'
                        })

                        st.subheader("📦 Sipariş Bazlı Atama Özeti")
                        st.dataframe(siparis_ozet, use_container_width=True, height=500)
                    except KeyError as e:
                        st.warning(f"⚠️ Sipariş Bazlı Özeti oluşturmak için eksik sütun var: {e}")

                    # === Excel export ===
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        summary.to_excel(writer, sheet_name='Ozet', index=False)
                        assigned_df.to_excel(writer, sheet_name='Detay', index=False)
                        if 'siparis_ozet' in locals():
                            siparis_ozet.to_excel(writer, sheet_name='Siparis_Ozeti', index=False)
                    output.seek(0)

                    st.download_button(
                        label="📥 Özet ve Detay Excel Olarak İndir",
                        data=output,
                        file_name="arac_planlama_ozet_detay.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"🚨 Hata oluştu: {e}")
