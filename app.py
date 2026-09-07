import streamlit as st
import yfinance as yf
import pandas as pd
import os

st.title("📈 Investment-Challenge Tracker")

# CSV initialisieren
CSV_FILE = "picks.csv"
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["Datum", "Ticker"]).to_csv(CSV_FILE, index=False)

# 1. Neuer Pick Eintrag
st.subheader("Neuen Pick eintragen")
col1, col2 = st.columns(2)
with col1:
    datum = st.date_input("Kaufdatum (Donnerstag)")
with col2:
    ticker = st.text_input("Ticker (z.B. AAPL oder SOL-USD für Krypto)")

if st.button("Pick speichern"):
    neuer_eintrag = pd.DataFrame([{"Datum": datum, "Ticker": ticker.upper()}])
    neuer_eintrag.to_csv(CSV_FILE, mode="a", header=False, index=False)
    st.success(f"{ticker.upper()} für {datum} gespeichert!")
    st.rerun()

# Picks verwalten
st.write("---")
st.subheader("🗑️ Picks verwalten")
df_picks = pd.read_csv(CSV_FILE)

if not df_picks.empty:
    zu_loeschen = st.selectbox(
        "Fehlerhaften Pick entfernen:", 
        df_picks.index, 
        format_func=lambda x: f"{df_picks.loc[x, 'Datum']} - {df_picks.loc[x, 'Ticker']}"
    )
    if st.button("Eintrag endgültig löschen"):
        df_picks = df_picks.drop(zu_loeschen)
        df_picks.to_csv(CSV_FILE, index=False)
        st.rerun()

# 2. Auswertung in Prozent
st.write("---")
st.subheader("📊 Aktueller Stand (Prozentuale Performance)")
df_picks = pd.read_csv(CSV_FILE)

if not df_picks.empty:
    df_picks['Datum'] = pd.to_datetime(df_picks['Datum'])
    
    # Benchmarks (ASHR ist der CSI 300 ETF, verhindert NaN Fehler)
    benchmarks = {'DAX': '^GDAXI', 'MSCI World': 'URTH', 'Nasdaq': '^IXIC', 'CSI 300': 'ASHR'}
    
    alle_ticker = df_picks['Ticker'].unique().tolist() + list(benchmarks.values())
    start_datum = df_picks['Datum'].min()
    
    with st.spinner("Lade Live-Kurse von Yahoo Finance..."):
        # bfill() und ffill() füllen Lücken an Feiertagen auf und verhindern NaN
        data = yf.download(alle_ticker, start=start_datum)['Close']
        data = data.ffill().bfill()
    
    heutiger_kurs = data.iloc[-1]
    
    # --- BERECHNUNG: INDIZES (Von Tag 1 bis Heute) ---
    start_kurse_indizes = data.loc[start_datum.strftime('%Y-%m-%d'):].iloc[0]
    perf_benchmarks = {}
    for b_name, b_ticker in benchmarks.items():
        rendite = ((heutiger_kurs[b_ticker] / start_kurse_indizes[b_ticker]) - 1) * 100
        perf_benchmarks[b_name] = rendite

    # --- BERECHNUNG: KOLLEGE (Wöchentliche 100€ Tranchen) ---
    gesamt_investiert = len(df_picks) * 100
    aktueller_portfolio_wert = 0
    
    for _, row in df_picks.iterrows():
        kauf_tag = row['Datum'].strftime('%Y-%m-%d')
        try:
            kurs_kauf_tag = data.loc[kauf_tag:].iloc[0]
            wert_der_tranche = 100 * (heutiger_kurs[row['Ticker']] / kurs_kauf_tag[row['Ticker']])
            aktueller_portfolio_wert += wert_der_tranche
        except Exception:
            st.error(f"Fehler bei {row['Ticker']}. Krypto braucht '-USD' (z.B. BTC-USD). Bitte löschen und neu anlegen.")

    # Gesamtrendite des Kollegen in Prozent
    perf_kollege = ((aktueller_portfolio_wert / gesamt_investiert) - 1) * 100

    # --- ANZEIGE ---
    colA, colB = st.columns(2)
    with colA:
        st.metric("Eingezahltes Kapital", f"{gesamt_investiert} €")
    with colB:
        st.metric("Aktueller Wert", f"{aktueller_portfolio_wert:.2f} €")

    st.markdown(f"### Performance Kollege: **{perf_kollege:+.2f} %**")
    
    st.write("### Die 4 Endgegner (Performance seit Tag 1)")
    geschlagene_indizes = 0
    
    cols = st.columns(4)
    for i, (b_name, rendite) in enumerate(perf_benchmarks.items()):
        with cols[i]:
            st.metric(b_name, f"{rendite:+.2f} %")
        if perf_kollege > rendite:
            geschlagene_indizes += 1
            
    st.write("---")
    st.subheader(f"Geschlagene Indizes: {geschlagene_indizes} von 4")
    
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