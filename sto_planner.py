import streamlit as st
import pandas as pd
import io
from solver import solve_assignment, plot_truck_grid
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
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
        if order_df['PALTypeChoice'].isnull().any():
            st.error("❗ 'PALTypeChoice' sütununda boş değerler var.")
        else:
            st.success("✅ 'PALTypeChoice' bilgisi tam.")

            if st.button("✅ Araca Atamaları Yap"):
                try:
                    assigned_df = solve_assignment(order_df)
                    st.session_state['assigned_df'] = assigned_df  # Atama sonuçlarını session_state'de sakla
                except Exception as e:
                    st.error(f"🚨 Hata oluştu: {e}")

            if 'assigned_df' in st.session_state:
                assigned_df = st.session_state['assigned_df']

                if assigned_df.empty:
                    st.warning("⚠️ Atama sonuçları boş.")
                else:
                    st.subheader("🚚 Atama Sonuçları")
                    st.dataframe(assigned_df, use_container_width=True, height=500)

                    # Araç seçimi için dropdown
                    trucks = assigned_df['Assigned_Truck'].unique()
                    selected_truck = st.selectbox("🚛 Görüntülemek istediğiniz aracı seçin", trucks, key="selected_truck")

                    if selected_truck:
                        fig = plot_truck_grid(assigned_df, selected_truck)
                        st.pyplot(fig)

                    # Özet
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
                    st.dataframe(styled_summary, use_container_width=True, height=400)

                    # Excel indir
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        summary.to_excel(writer, sheet_name='Ozet', index=False)
                        assigned_df.to_excel(writer, sheet_name='Detay', index=False)
                    output.seek(0)

                    st.download_button(
                        label="📥 Özet ve Detay Excel Olarak İndir",
                        data=output,
                        file_name="arac_planlama_ozet_detay.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )