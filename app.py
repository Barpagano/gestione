import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# --- CSS PER GRIGLIA TAVOLI 5x3 (OTTIMIZZATA PER SMARTPHONE) ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* FORZA 5 COLONNE AFFIANCATE ANCHE SU MOBILE */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0px !important;
        margin-bottom: 0px !important;
    }
    
    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important; /* Impedisce che vadano a capo */
        padding: 0px !important;
        margin: 0px !important;
    }

    /* TASTI TAVOLI: Grandi e baciati */
    .stButton > button {
        width: 100% !important;
        height: 90px !important; 
        border-radius: 0px !important;
        font-weight: 900 !important;
        font-size: 28px !important;
        margin: 0px !important;
        border: 0.5px solid #111111 !important;
    }

    /* COLORI TAVOLI */
    .btn-libero div[data-testid="stButton"] > button { background-color: #00FF00 !important; color: #000000 !important; }
    .btn-occupato div[data-testid="stButton"] > button { background-color: #FF0000 !important; color: #FFFFFF !important; }

    .logo-container { text-align: center; padding: 10px 0; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- INIZIALIZZAZIONE ---
DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"
STOCK_FILE = "stock_bar_pagano.csv"

def inizializza():
    if not os.path.exists(MENU_FILE):
        pd.DataFrame([{"categoria": "VETRINA", "prodotto": "Cornetto", "prezzo": 1.20}]).to_csv(MENU_FILE, index=False)
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=["id", "tavolo", "prodotto", "prezzo", "stato", "ora"]).to_csv(DB_FILE, index=False)
    if not os.path.exists(STOCK_FILE):
        pd.DataFrame(columns=["prodotto", "quantita"]).to_csv(STOCK_FILE, index=False)

inizializza()

# --- FUNZIONI DATI ---
def carica_menu(): return pd.read_csv(MENU_FILE)
def salva_menu(df): df.to_csv(MENU_FILE, index=False)
def carica_stock():
    try:
        df = pd.read_csv(STOCK_FILE)
        return {str(row['prodotto']).strip().lower(): int(row['quantita']) for _, row in df.iterrows()}
    except: return {}
def salva_stock(stk_dict):
    pd.DataFrame([{"prodotto": k, "quantita": v} for k, v in stk_dict.items()]).to_csv(STOCK_FILE, index=False)
def carica_ordini():
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []
def salva_ordini(lista): pd.DataFrame(lista).to_csv(DB_FILE, index=False)

st_autorefresh(interval=5000, key="refresh_global")
ordini = carica_ordini()
stock = carica_stock()
ruolo = st.query_params.get("ruolo", "cliente")

# --- LOGO/HEADER ---
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
if os.path.exists("logo.png"): st.image("logo.png", width=140)
else: st.markdown("<h1 style='color:#00FF00; font-size:35px; margin:0;'>BAR PAGANO</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BANCONE
# =========================================================
if ruolo == "banco":
    t1, t2, t3 = st.tabs(["📋 ORDINI", "🥐 STOCK", "⚙️ MENU"])
    with t1:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini)))
        for t in tavoli_attivi:
            with st.container(border=True):
                st.write(f"### Tavolo {t}")
                items = [o for o in ordini if str(o['tavolo']) == t]
                for r in items:
                    c1, c2 = st.columns([4, 1])
                    cl = "text-decoration: line-through; color:gray;" if r['stato'] == "SI" else ""
                    c1.markdown(f"<span style='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                    if r['stato'] == "NO" and c2.button("OK", key=f"ok_{r['id']}"):
                        for o in ordini: 
                            if o['id'] == r['id']: o['stato'] = "SI"
                        salva_ordini(ordini); st.rerun()
                if st.button(f"LIBERA {t}", key=f"lib_{t}", type="primary", use_container_width=True):
                    salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()
    with t2:
        m_df = carica_menu()
        p_sel = st.selectbox("Monitora prodotto:", m_df['prodotto'].unique())
        if st.button("Aggiungi"):
            stk = carica_stock(); stk[p_sel.strip().lower()] = 0; salva_stock(stk); st.rerun()
        for pk, q in list(stock.items()):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{pk.upper()}**")
            if c2.button("➖", key=f"m_{pk}"): stock[pk]=max(0,q-1); salva_stock(stock); st.rerun()
            c3.write(f"Qta: {q}")
            if c4.button("➕", key=f"p_{pk}"): stock[pk]=q+1; salva_stock(stock); st.rerun()
    with t3:
        n_prod = st.text_input("Nome Prodotto")
        n_pre = st.number_input("Prezzo", step=0.10)
        if st.button("Salva"):
            m_df = carica_menu()
            m_df = pd.concat([m_df, pd.DataFrame([{"categoria": "VETRINA", "prodotto": n_prod, "prezzo": n_pre}])], ignore_index=True)
            salva_menu(m_df); st.rerun()

# =========================================================
# CLIENTE (INTERFACCIA SMARTPHONE)
# =========================================================
else:
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.markdown("<p style='text-align:center; color:#888; margin-bottom:5px;'>SELEZIONA TAVOLO</p>", unsafe_allow_html=True)
        occupati = set(str(o['tavolo']) for o in ordini)
        
        # Genera 3 file da 5 colonne
        for riga in range(3):
            cols = st.columns(5)
            for col in range(5):
                n = str((riga * 5) + col + 1)
                cl = "btn-occupato" if n in occupati else "btn-libero"
                with cols[col]:
                    st.markdown(f'<div class="{cl}">', unsafe_allow_html=True)
                    if st.button(n, key=f"t_{n}", disabled=(n in occupati)):
                        st.session_state.tavolo = n; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        # MENU PRODOTTI
        st.markdown(f"<div style='background-color:#00FF00; color:black; text-align:center; padding:10px; font-weight:bold;'>TAVOLO {st.session_state.tavolo}</div>", unsafe_allow_html=True)
        if st.button("⬅️ CAMBIA TAVOLO", use_container_width=True): st.session_state.tavolo = None; st.rerun()
        
        m_df = carica_menu()
        for _, r in m_df.iterrows():
            pk = str(r['prodotto']).strip().lower()
            q_disp = stock.get(pk, 999)
            c1, c2 = st.columns([3, 1])
            testo = f"**{r['prodotto']}**\n€{r['prezzo']:.2f}"
            if q_disp <= 0: testo += " (FINE ❌)"
            c1.markdown(testo)
            if c2.button("➕", key=f"add_{pk}", disabled=(q_disp <= 0)):
                st.session_state.carrello.append(r.to_dict()); st.rerun()

        if st.session_state.carrello:
            st.divider()
            if st.button("🚀 INVIA ORDINE", type="primary", use_container_width=True):
                stk = carica_stock()
                for i in st.session_state.carrello:
                    pk = str(i['prodotto']).strip().lower()
                    if pk in stk: stk[pk] = max(0, stk[pk] - 1)
                    ordini.append({"id": time.time()+i['prezzo'], "tavolo": st.session_state.tavolo, "prodotto": i['prodotto'], "prezzo": i['prezzo'], "stato": "NO", "ora": datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")})
                salva_stock(stk); salva_ordini(ordini); st.session_state.carrello = []; st.rerun()
