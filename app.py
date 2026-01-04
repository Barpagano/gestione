import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="BAR PAGANO - GESTIONE", 
    page_icon="☕", 
    layout="wide"
)

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Pulsanti generali */
    div[data-testid="column"] button {
        width: 100% !important;
        font-weight: bold !important;
        border-radius: 8px !important;
    }
    
    /* Stile testo ordini */
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; font-style: italic; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; font-size: 16px; }
    
    /* TASTO PAGATO E CHIUDI (Sotto l'ordine) */
    div.stButton > button[kind="primary"] {
        background-color: #D32F2F !important;
        color: white !important;
        border: 2px solid #FF5252 !important;
        height: 55px !important;
        font-size: 18px !important;
        margin-top: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SERVIZIO ---
def get_ora_italiana():
    tz = pytz.timezone('Europe/Rome')
    return datetime.now(tz).strftime("%H:%M")

def suona_notifica():
    audio_html = '<audio autoplay style="display:none;"><source src="https://raw.githubusercontent.com/rafaelreis-hotmart/Audio-Files/main/notification.mp3" type="audio/mp3"></audio>'
    components.html(audio_html, height=0)

# --- GESTIONE DATABASE ---
DB_FILE = "ordini_bar_pagano.csv"
STOCK_FILE = "stock_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"
COLONNE_ORDINI = ["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]

def inizializza_file(file, colonne):
    if not os.path.exists(file) or os.stat(file).st_size <= 2:
        pd.DataFrame(columns=colonne).to_csv(file, index=False)

inizializza_file(DB_FILE, COLONNE_ORDINI)
inizializza_file(MENU_FILE, ["categoria", "prodotto", "prezzo"])
inizializza_file(STOCK_FILE, ["prodotto", "quantita"])

def carica_menu(): return pd.read_csv(MENU_FILE)
def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []
def salva_ordini(lista): pd.DataFrame(lista if lista else [], columns=COLONNE_ORDINI).to_csv(DB_FILE, index=False)
def carica_stock(): 
    df = pd.read_csv(STOCK_FILE)
    return df.set_index('prodotto')['quantita'].to_dict() if not df.empty else {}
def salva_stock(d): pd.DataFrame(list(d.items()), columns=['prodotto', 'quantita']).to_csv(STOCK_FILE, index=False)

# --- LOGICA CORE ---
st_autorefresh(interval=5000, key="refresh_globale")
menu_df = carica_menu()
ordini_attuali = carica_ordini()

# Gestione notifica sonora per nuovi ordini
if "ultimo_count" not in st.session_state: st.session_state.ultimo_count = len(ordini_attuali)
if len(ordini_attuali) > st.session_state.ultimo_count:
    suona_notifica()
st.session_state.ultimo_count = len(ordini_attuali)

st.markdown("<h1 style='text-align: center;'>☕ GESTIONE BAR PAGANO</h1>", unsafe_allow_html=True)

# Menu principale in Tab
tab_ordini, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI IN CORSO", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])

# --- TAB 1: ORDINI IN CORSO ---
with tab_ordini:
    if not ordini_attuali:
        st.info("Nessun ordine presente al momento.")
    else:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        cols = st.columns(3)
        
        for idx, t in enumerate(tavoli_attivi):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"🪑 Tavolo {t}")
                    items = [o for o in ordini_attuali if str(o['tavolo']) == str(t)]
                    
                    totale_tavolo = 0
                    for r in items:
                        totale_tavolo += float(r['prezzo'])
                        c_del, c_txt, c_ok = st.columns([0.5, 3, 1])
                        
                        # Tasto X per eliminare riga singola (errore)
                        if c_del.button("❌", key=f"del_{r['id_univoco']}"):
                            salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']])
                            st.rerun()
                            
                        # Testo Prodotto con orario
                        stile = "servito" if r['stato'] == "SI" else "da-servire"
                        c_txt.markdown(f"<span class='{stile}'>[{r.get('orario','')}] {r['prodotto']}</span>", unsafe_allow_html=True)
                        
                        # Tasto Ok per segnare come servito al banco
                        if r['stato'] == "NO" and c_ok.button("Ok", key=f"ok_{r['id_univoco']}"):
                            for o in ordini_attuali:
                                if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                            salva_ordini(ordini_attuali); st.rerun()
                    
                    st.divider()
                    st.write(f"**TOTALE CONTO: €{totale_tavolo:.2f}**")
                    
                    # TASTO PAGATO E CHIUDI (Sotto l'ordine del tavolo)
                    if st.button(f"PAGATO E CHIUDI TAVOLO {t}", key=f"chiusura_{t}", type="primary"):
                        nuovi_ordini = [o for o in ordini_attuali if str(o['tavolo']) != str(t)]
                        salva_ordini(nuovi_ordini)
                        st.toast(f"Tavolo {t} pagato e rimosso correttamente.")
                        time.sleep(0.5)
                        st.rerun()

# --- TAB 2: VETRINA (Sottrazione rapida stock) ---
with tab_vetrina:
    stk = carica_stock()
    cv = st.columns(4)
    for i, (p, q) in enumerate(stk.items()):
        if cv[i % 4].button(f"{p}\n({q})", key=f"vtr_{p}", disabled=(q <= 0)):
            stk[p] = max(0, q - 1); salva_stock(stk); st.rerun()

# --- TAB 3: GESTIONE STOCK ---
with tab_stock:
    stk = carica_stock()
    for p, q in stk.items():
        cx, cm, cq, cp, cd = st.columns([3, 1, 1, 1, 1])
        cx.write(f"**{p}**")
        if cm.button("➖", key=f"m_{p}"): stk[p] = max(0, q-1); salva_stock(stk); st.rerun()
        cq.write(f"**{q}**")
        if cp.button("➕", key=f"p_{p}"): stk[p] = q+1; salva_stock(stk); st.rerun()
        if cd.button("🗑️", key=f"d_{p}"): del stk[p]; salva_stock(stk); st.rerun()

# --- TAB 4: GESTIONE MENU (Prezzi e Prodotti) ---
with tab_menu:
    with st.form("nuovo_prodotto"):
        c1, c2 = st.columns(2)
        cat_e = c1.selectbox("Categoria Esistente", ["---"] + sorted(list(menu_df['categoria'].unique())) if not menu_df.empty else ["---"])
        cat_n = c2.text_input("Nuova Categoria")
        nome_n = st.text_input("Nome Prodotto")
        prez_n = st.number_input("Prezzo €", min_value=0.0, step=0.1)
        if st.form_submit_button("AGGIUNGI AL LISTINO"):
            cat_f = cat_n if cat_n.strip() != "" else cat_e
            if cat_f != "---" and nome_n:
                nuovo = pd.DataFrame([{"categoria": cat_f, "prodotto": nome_n, "prezzo": prez_n}])
                pd.concat([menu_df, nuovo], ignore_index=True).to_csv(MENU_FILE, index=False); st.rerun()
