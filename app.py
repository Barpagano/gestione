import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# --- CSS PERSONALIZZATO (GRIGLIA COMPATTA) ---
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

# --- INIZIALIZZAZIONE FILE ---
DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"
STOCK_FILE = "stock_bar_pagano.csv"

def inizializza_sistema():
    # Se non c'è il menu, ne creiamo uno base
    if not os.path.exists(MENU_FILE):
        df_menu = pd.DataFrame([
            {"categoria": "VETRINA", "prodotto": "Cornetto", "prezzo": 1.20},
            {"categoria": "CAFFETTERIA", "prodotto": "Caffè", "prezzo": 1.00},
            {"categoria": "BIBITE", "prodotto": "Acqua 0.5L", "prezzo": 1.00}
        ])
        df_menu.to_csv(MENU_FILE, index=False)
    
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=["id", "tavolo", "prodotto", "prezzo", "stato", "ora"]).to_csv(DB_FILE, index=False)
    
    if not os.path.exists(STOCK_FILE):
        pd.DataFrame(columns=["prodotto", "quantita"]).to_csv(STOCK_FILE, index=False)

inizializza_sistema()

# --- FUNZIONI DATI ---
def carica_menu(): return pd.read_csv(MENU_FILE)
def salva_menu(df): df.to_csv(MENU_FILE, index=False)

def carica_stock():
    try:
        df = pd.read_csv(STOCK_FILE)
        return {str(row['prodotto']).strip().lower(): int(row['quantita']) for _, row in df.iterrows()}
    except: return {}

def salva_stock(stk_dict):
    df = pd.DataFrame([{"prodotto": k, "quantita": v} for k, v in stk_dict.items()])
    df.to_csv(STOCK_FILE, index=False)

def carica_ordini():
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []

def salva_ordini(lista): pd.DataFrame(lista).to_csv(DB_FILE, index=False)

# Refresh automatico
st_autorefresh(interval=5000, key="refresh_global")
ordini = carica_ordini()
stock = carica_stock()
ruolo = st.query_params.get("ruolo", "cliente")

# --- HEADER ---
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
if os.path.exists("logo.png"): st.image("logo.png", width=180)
else: st.markdown("<h1 style='color:#00FF00; font-size:40px; margin:0;'>BAR PAGANO</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BANCONE (GESTIONE ORDINI, STOCK E MENU)
# =========================================================
if ruolo == "banco":
    t1, t2, t3 = st.tabs(["📋 ORDINI", "🥐 VETRINA/STOCK", "⚙️ MODIFICA MENU"])
    
    with t1:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini)))
        if not tavoli_attivi: st.info("Nessun ordine attivo")
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
                if st.button(f"LIBERA TAVOLO {t}", key=f"lib_{t}", type="primary", use_container_width=True):
                    salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()

    with t2:
        st.write("### Gestione Quantità Vetrina")
        m_df = carica_menu()
        p_sel = st.selectbox("Seleziona prodotto da monitorare:", m_df['prodotto'].unique())
        if st.button("Monitora questo prodotto"):
            chiave = p_sel.strip().lower()
            if chiave not in stock: stock[chiave] = 0
            salva_stock(stock); st.rerun()
        
        st.divider()
        for pk, q in list(stock.items()):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{pk.upper()}**")
            if c2.button("➖", key=f"m_{pk}"): stock[pk]=max(0,q-1); salva_stock(stock); st.rerun()
            c3.write(f"Qta: {q}")
            if c4.button("➕", key=f"p_{pk}"): stock[pk]=q+1; salva_stock(stock); st.rerun()

    with t3:
        st.write("### Aggiungi Nuovo Prodotto al Menu")
        with st.form("nuovo_prodotto"):
            n_cat = st.selectbox("Categoria", ["VETRINA", "CAFFETTERIA", "BIBITE", "FOOD", "ALCOOL"])
            n_prod = st.text_input("Nome Prodotto")
            n_prezzo = st.number_input("Prezzo", min_value=0.0, step=0.10)
            if st.form_submit_button("Aggiungi al Menu"):
                if n_prod:
                    m_df = carica_menu()
                    nuovo_r = pd.DataFrame([{"categoria": n_cat, "prodotto": n_prod, "prezzo": n_prezzo}])
                    m_df = pd.concat([m_df, nuovo_r], ignore_index=True)
                    salva_menu(m_df); st.success(f"{n_prod} aggiunto!"); st.rerun()

# =========================================================
# CLIENTE
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
                cl = "btn-occupato" if n in occupati else "btn-libero"
                with cols[colonna]:
                    st.markdown(f'<div class="{cl}">', unsafe_allow_html=True)
                    if st.button(n, key=f"t_{n}", disabled=(n in occupati)):
                        st.session_state.tavolo = n; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='background-color:#00FF00; color:black; text-align:center; padding:10px; font-weight:bold;'>TAVOLO {st.session_state.tavolo}</div>", unsafe_allow_html=True)
        if st.button("⬅️ TORNA AI TAVOLI", use_container_width=True): st.session_state.tavolo = None; st.rerun()
        
        m_df = carica_menu()
        cat = st.radio("Scegli:", sorted(m_df['categoria'].unique()), horizontal=True)
        for _, r in m_df[m_df['categoria'] == cat].iterrows():
            nome_p = str(r['prodotto']).strip().lower()
            q_disp = stock.get(nome_p, 999) 
            
            c1, c2 = st.columns([3, 1])
            testo = f"**{r['prodotto']}**\n€{r['prezzo']:.2f}"
            if q_disp <= 0: testo += " (ESAURITO ❌)"
            c1.markdown(testo)
            if c2.button("➕", key=f"add_{nome_p}", disabled=(q_disp <= 0)):
                st.session_state.carrello.append(r.to_dict()); st.rerun()

        if st.session_state.carrello:
            st.divider()
            if st.button("🚀 INVIA ORDINE", type="primary", use_container_width=True):
                stk_attuale = carica_stock()
                for item in st.session_state.carrello:
                    p_key = str(item['prodotto']).strip().lower()
                    if p_key in stk_attuale: stk_attuale[p_key] = max(0, stk_attuale[p_key] - 1)
                    
                    ordini.append({
                        "id": f"{time.time()}_{p_key}",
                        "tavolo": st.session_state.tavolo, "prodotto": item['prodotto'],
                        "prezzo": item['prezzo'], "stato": "NO", 
                        "ora": datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                    })
                salva_stock(stk_attuale); salva_ordini(ordini)
                st.session_state.carrello = []; st.success("Ordine inviato!"); time.sleep(1); st.rerun()
