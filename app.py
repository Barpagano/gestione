import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    .tavoli-wrapper { max-width: 400px; margin: 0 auto; padding: 10px; }
    [data-testid="stHorizontalBlock"] { gap: 0px !important; margin-bottom: 0px !important; }
    [data-testid="column"] { padding: 0px !important; margin: 0px !important; }
    .stButton > button {
        width: 100% !important; height: 80px !important; 
        border-radius: 0px !important; font-weight: 900 !important;
        font-size: 28px !important; margin: 0px !important;
        border: 1px solid #111111 !important;
    }
    .btn-libero div[data-testid="stButton"] > button { background-color: #00FF00 !important; color: #000000 !important; }
    .btn-occupato div[data-testid="stButton"] > button { background-color: #FF0000 !important; color: #FFFFFF !important; }
    .logo-container { display: flex; justify-content: center; padding: 20px 0; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- FILE DI SISTEMA ---
DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"
STOCK_FILE = "stock_bar_pagano.csv"

# --- FUNZIONI DI GESTIONE DATI ---
def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []

def salva_ordini(lista): 
    pd.DataFrame(lista).to_csv(DB_FILE, index=False)

def carica_stock():
    if not os.path.exists(STOCK_FILE):
        return {}
    try:
        df = pd.read_csv(STOCK_FILE)
        # Normalizziamo le chiavi: tutto minuscolo e senza spazi
        return {str(row['prodotto']).strip().lower(): int(row['quantita']) for _, row in df.iterrows()}
    except: return {}

def salva_stock(stk_dict):
    # Salviamo mantenendo i nomi originali ma puliti
    df = pd.DataFrame([{"prodotto": k, "quantita": v} for k, v in stk_dict.items()])
    df.to_csv(STOCK_FILE, index=False)

# Refresh automatico ogni 5 secondi
st_autorefresh(interval=5000, key="refresh_global")
ordini = carica_ordini()
stock = carica_stock()
ruolo = st.query_params.get("ruolo", "cliente")

# --- HEADER / LOGO ---
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
if os.path.exists("logo.png"): st.image("logo.png", width=180)
else: st.markdown("<h1 style='color:#00FF00; font-size:40px; margin:0;'>BAR PAGANO</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BANCONE (GESTIONE ORDINI E CARICO VETRINA)
# =========================================================
if ruolo == "banco":
    t1, t2 = st.tabs(["📋 ORDINI IN ARRIVO", "🥐 GESTIONE VETRINA"])
    
    with t1:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini)))
        if not tavoli_attivi: st.info("In attesa di ordini...")
        for t in tavoli_attivi:
            with st.container(border=True):
                st.write(f"### Tavolo {t}")
                items = [o for o in ordini if str(o['tavolo']) == t]
                for r in items:
                    c1, c2 = st.columns([4, 1])
                    cl = "text-decoration: line-through; color: gray;" if r['stato'] == "SI" else "color: white;"
                    c1.markdown(f"<span style='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                    if r['stato'] == "NO" and c2.button("OK", key=f"ok_{r['id']}"):
                        for o in ordini: 
                            if o['id'] == r['id']: o['stato'] = "SI"
                        salva_ordini(ordini); st.rerun()
                if st.button(f"LIBERA TAVOLO {t}", key=f"lib_{t}", type="primary", use_container_width=True):
                    salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()

    with t2:
        st.write("### Carica Prodotti in Vetrina")
        if os.path.exists(MENU_FILE):
            m_df = pd.read_csv(MENU_FILE)
            p_selezionato = st.selectbox("Seleziona prodotto dal menu:", m_df['prodotto'].unique())
            if st.button("Aggiungi a monitoraggio stock"):
                chiave = p_selezionato.strip().lower()
                if chiave not in stock: stock[chiave] = 0
                salva_stock(stock); st.rerun()
        
        st.divider()
        for prod_key, qta in list(stock.items()):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{prod_key.upper()}**")
            if c2.button("➖", key=f"minus_{prod_key}"):
                stock[prod_key] = max(0, qta - 1); salva_stock(stock); st.rerun()
            c3.write(f"Qta: {qta}")
            if c4.button("➕", key=f"plus_{prod_key}"):
                stock[prod_key] = qta + 1; salva_stock(stock); st.rerun()

# =========================================================
# CLIENTE (SCALAMENTO AUTOMATICO)
# =========================================================
else:
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.markdown('<div class="tavoli-wrapper">', unsafe_allow_html=True)
        occupati = set(str(o['tavolo']) for o in ordini)
        for riga in range(3):
            cols = st.columns(5)
            for colonna in range(5):
                n = str((riga * 5) + colonna + 1)
                is_occ = n in occupati
                classe = "btn-occupato" if is_occ else "btn-libero"
                with cols[colonna]:
                    st.markdown(f'<div class="{classe}">', unsafe_allow_html=True)
                    if st.button(n, key=f"t_{n}", disabled=is_occ):
                        st.session_state.tavolo = n; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='background-color:#00FF00; color:black; text-align:center; padding:10px; font-weight:bold; font-size:22px;'>TAVOLO {st.session_state.tavolo}</div>", unsafe_allow_html=True)
        if st.button("⬅️ TORNA AI TAVOLI", use_container_width=True): st.session_state.tavolo = None; st.rerun()
        
        if os.path.exists(MENU_FILE):
            menu_df = pd.read_csv(MENU_FILE)
            cat = st.radio("Menu:", sorted(menu_df['categoria'].unique()), horizontal=True)
            for _, r in menu_df[menu_df['categoria'] == cat].iterrows():
                # CONTROLLO DISPONIBILITÀ (Normalizzato)
                p_nome = str(r['prodotto']).strip().lower()
                q_disp = stock.get(p_nome, 999) # Se non è monitorato, è sempre disponibile
                
                c1, c2 = st.columns([3, 1])
                testo_p = f"**{r['prodotto']}**\n€{r['prezzo']:.2f}"
                if q_disp <= 0: testo_p += " (ESAURITO ❌)"
                c1.markdown(testo_p)
                
                if c2.button("➕", key=f"add_{p_nome}", disabled=(q_disp <= 0)):
                    st.session_state.carrello.append(r.to_dict()); st.rerun()

        if st.session_state.carrello:
            st.divider()
            tot = sum(i['prezzo'] for i in st.session_state.carrello)
            st.write(f"### Totale: €{tot:.2f}")
            if st.button("🚀 INVIA ORDINE ORA", type="primary", use_container_width=True):
                ora = datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                
                # RICARICA STOCK PRIMA DI SCALARE (per evitare errori di contemporaneità)
                stk_attuale = carica_stock()
                
                for item in st.session_state.carrello:
                    p_chiave = str(item['prodotto']).strip().lower()
                    
                    # LOGICA DI SCALAMENTO
                    if p_chiave in stk_attuale:
                        stk_attuale[p_chiave] = max(0, stk_attuale[p_chiave] - 1)
                    
                    ordini.append({
                        "id": f"{time.time()}_{p_chiave}",
                        "tavolo": st.session_state.tavolo, "prodotto": item['prodotto'],
                        "prezzo": item['prezzo'], "stato": "NO", "ora": ora
                    })
                
                salva_stock(stk_attuale) # Salva lo stock ridotto
                salva_ordini(ordini)
                st.session_state.carrello = []
                st.success("Ordine inviato e Vetrina scaricata!"); time.sleep(1); st.rerun()
