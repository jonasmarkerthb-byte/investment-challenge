import streamlit as st
import yfinance as yf
import pandas as pd
import os

# Layout auf Breitbild stellen
st.set_page_config(page_title="Investment-Challenge", layout="wide")

st.title("📈 Investment-Challenge Tracker")

CSV_FILE = "picks.csv"
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["Datum", "Ticker"]).to_csv(CSV_FILE, index=False)

df_picks = pd.read_csv(CSV_FILE)

if not df_picks.empty:
    df_picks['Datum'] = pd.to_datetime(df_picks['Datum'])
    
    # Benchmarks (ASHR ist der CSI 300 ETF)
    benchmarks = {'DAX': '^GDAXI', 'MSCI World': 'URTH', 'Nasdaq': '^IXIC', 'CSI 300': 'ASHR'}
    
    alle_ticker = df_picks['Ticker'].unique().tolist() + list(benchmarks.values())
    start_datum = df_picks['Datum'].min()
    
    with st.spinner("Lade Live-Kurse und generiere Auswertung..."):
        data = yf.download(alle_ticker, start=start_datum)['Close']
        data = data.ffill().bfill()
    
    heutiger_kurs = data.iloc[-1]
    chart_pct = pd.DataFrame(index=data.index)
    
    # Benchmarks berechnen
    start_kurse_indizes = data.iloc[0]
    perf_benchmarks = {}
    for b_name, b_ticker in benchmarks.items():
        chart_pct[b_name] = ((data[b_ticker] / start_kurse_indizes[b_ticker]) - 1) * 100
        perf_benchmarks[b_name] = chart_pct[b_name].iloc[-1]

    investiert_zeitverlauf = pd.Series(0.0, index=data.index)
    portfolio_wert_zeitverlauf = pd.Series(0.0, index=data.index)
    
    gesamt_investiert = 0
    aktueller_portfolio_wert = 0
    fehlerhafte_ticker = []
    einzel_picks_daten = []
    
    for _, row in df_picks.iterrows():
        kauf_tag = row['Datum'].strftime('%Y-%m-%d')
        ticker = row['Ticker']
        
        try:
            kurs_kauf_tag = data.loc[kauf_tag:, ticker].iloc[0]
            echtes_kaufdatum = data.loc[kauf_tag:].index[0]
            
            if pd.isna(heutiger_kurs[ticker]) or pd.isna(kurs_kauf_tag):
                fehlerhafte_ticker.append(ticker)
                continue
                
            gesamt_investiert += 100
            wert_der_tranche = 100 * (heutiger_kurs[ticker] / kurs_kauf_tag)
            aktueller_portfolio_wert += wert_der_tranche
            
            rendite_tranche = ((wert_der_tranche / 100) - 1) * 100
            einzel_picks_daten.append({
                "Kaufdatum": row['Datum'].strftime('%d.%m.%Y'),
                "Ticker": ticker,
                "Kaufkurs": round(kurs_kauf_tag, 2),
                "Aktueller Kurs": round(heutiger_kurs[ticker], 2),
                "Wert (in €)": round(wert_der_tranche, 2),
                "Rendite (%)": round(rendite_tranche, 2)
            })
            
            investiert_zeitverlauf.loc[echtes_kaufdatum:] += 100
            anteile = 100 / kurs_kauf_tag
            portfolio_wert_zeitverlauf.loc[echtes_kaufdatum:] += data.loc[echtes_kaufdatum:, ticker] * anteile
            
        except Exception:
            fehlerhafte_ticker.append(ticker)

    if fehlerhafte_ticker:
        st.error(f"🚨 Fehler bei folgenden Tickern (keine Daten): {', '.join(set(fehlerhafte_ticker))}. Sie wurden ignoriert.")

    # Gesamtrendite Kollege
    chart_pct['Portfolio Kollege'] = ((portfolio_wert_zeitverlauf / investiert_zeitverlauf.replace(0, pd.NA)) - 1) * 100
    chart_pct['Portfolio Kollege'] = chart_pct['Portfolio Kollege'].fillna(0)
    
    perf_kollege = ((aktueller_portfolio_wert / gesamt_investiert) - 1) * 100 if gesamt_investiert > 0 else 0

    # --- HALL OF FAME & SHAME ---
    if einzel_picks_daten:
        df_einzel = pd.DataFrame(einzel_picks_daten)
        beste_aktie = df_einzel.loc[df_einzel['Rendite (%)'].idxmax()]
        schlechteste_aktie = df_einzel.loc[df_einzel['Rendite (%)'].idxmin()]
        
        col_fame, col_shame = st.columns(2)
        with col_fame:
            st.success(f"🏆 **Hall of Fame:** {beste_aktie['Ticker']} mit **+{beste_aktie['Rendite (%)']}%**")
        with col_shame:
            st.error(f"🗑️ **Hall of Shame:** {schlechteste_aktie['Ticker']} mit **{schlechteste_aktie['Rendite (%)']}%**")

    # --- METRIKEN ---
    st.write("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Eingezahltes Kapital", f"{gesamt_investiert} €")
    with col2:
        st.metric("Aktueller Wert", f"{aktueller_portfolio_wert:.2f} €")
    with col3:
        st.metric("Performance Kollege", f"{perf_kollege:+.2f} %")

    # --- CHARTS & BENCHMARKS ---
    st.write("### 📊 Performance-Vergleich (in %)")
    st.line_chart(chart_pct, height=400)
    
    st.write("### 🏁 Die 4 Endgegner (Heute)")
    geschlagene_indizes = 0
    cols = st.columns(4)
    for i, (b_name, rendite) in enumerate(perf_benchmarks.items()):
        with cols[i]:
            st.metric(b_name, f"{rendite:+.2f} %")
        if perf_kollege > rendite:
            geschlagene_indizes += 1
            
    st.write("---")
    st.subheader(f"Zwischenstand: {geschlagene_indizes} von 4 Indizes geschlagen")
    
    if geschlagene_indizes == 0:
        st.error("🚨 Resultat: Kollege schuldet dir 2 XPeng Aktien!")
    elif geschlagene_indizes == 1:
        st.warning("⚠️ Resultat: Kollege schuldet dir 1 XPeng Aktie!")
    elif geschlagene_indizes == 2:
        st.info("🤝 Resultat: Unentschieden. Niemand schuldet etwas.")
    elif geschlagene_indizes == 3:
        st.success("🎉 Resultat: Du schuldest dem Kollegen 1 XPeng Aktie.")
    elif geschlagene_indizes == 4:
        st.success("🏆 Resultat: Du schuldest dem Kollegen 2 XPeng Aktien.")

    # --- TABELLE ---
    st.write("---")
    st.write("### 🔍 Einzelne Picks in der Übersicht")
    if einzel_picks_daten:
        st.dataframe(df_einzel, use_container_width=True)
else:
    st.info("Keine Daten gefunden. Bitte trage Picks in die picks.csv ein.")