import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO - GESTIONE", page_icon="☕", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    div[data-testid="column"] button { width: 100% !important; font-weight: bold !important; border-radius: 10px !important; }
    
    /* Stile testo ordini */
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; font-style: italic; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; font-size: 16px; }
    
    /* TASTO PAGATO E CHIUDI (ROSSO E GRANDE) */
    .stButton > button[kind="primary"] {
        background-color: #D32F2F !important;
        color: white !important;
        height: 65px !important;
        font-size: 22px !important;
        border: 2px solid #FF5252 !important;
        margin-top: 15px !important;
    }
    
    .selected-tavolo { 
        background-color: #2E7D32; color: white; padding: 10px; 
        border-radius: 10px; text-align: center; font-size: 20px; 
        font-weight: bold; margin-bottom: 10px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SERVIZIO ---
def get_ora_italiana():
    return datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")

def suona_notifica():
    audio_html = '<audio autoplay style="display:none;"><source src="https://raw.githubusercontent.com/rafaelreis-hotmart/Audio-Files/main/notification.mp3" type="audio/mp3"></audio>'
    components.html(audio_html, height=0)

# --- GESTIONE DATABASE ---
DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def inizializza_file(file, colonne):
    if not os.path.exists(file) or os.stat(file).st_size <= 2:
        pd.DataFrame(columns=colonne).to_csv(file, index=False)

inizializza_file(DB_FILE, ["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"])
inizializza_file(MENU_FILE, ["categoria", "prodotto", "prezzo"])

def carica_menu(): return pd.read_csv(MENU_FILE)
def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []
def salva_ordini(lista): 
    pd.DataFrame(lista if lista else [], columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)

# --- LOGICA CORE ---
ruolo = st.query_params.get("ruolo", "cliente")
menu_df = carica_menu()
ordini_attuali = carica_ordini()

# ---------------------------------------------------------
# INTERFACCIA BANCONE (Con Tasto Pagato sotto l'ordine)
# ---------------------------------------------------------
if ruolo == "banco":
    st_autorefresh(interval=5000, key="banco_refresh")
    st.markdown("<h1 style='text-align: center;'>☕ BANCONE BAR PAGANO</h1>", unsafe_allow_html=True)
    
    # Notifica sonora
    if "ultimo_count" not in st.session_state: st.session_state.ultimo_count = len(ordini_attuali)
    if len(ordini_attuali) > st.session_state.ultimo_count:
        suona_notifica()
    st.session_state.ultimo_count = len(ordini_attuali)

    if not ordini_attuali:
        st.info("In attesa di nuovi ordini...")
    else:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        # Griglia a 3 colonne per i tavoli
        cols = st.columns(3)
        for idx, t in enumerate(tavoli_attivi):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"🪑 Tavolo {t}")
                    items = [o for o in ordini_attuali if str(o['tavolo']) == str(t)]
                    totale_tavolo = 0
                    
                    # Lista prodotti del tavolo
                    for r in items:
                        totale_tavolo += float(r['prezzo'])
                        c_del, c_txt, c_ok = st.columns([0.6, 3, 1])
                        
                        # Tasto X (Elimina)
                        if c_del.button("❌", key=f"del_{r['id_univoco']}"):
                            salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                        
                        # Nome Prodotto
                        stile = "servito" if r['stato'] == "SI" else "da-servire"
                        c_txt.markdown(f"<span class='{stile}'>[{r.get('orario','')}] {r['prodotto']}</span>", unsafe_allow_html=True)
                        
                        # Tasto Ok (Servito)
                        if r['stato'] == "NO" and c_ok.button("Ok", key=f"ok_{r['id_univoco']}"):
                            for o in ordini_attuali:
                                if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                            salva_ordini(ordini_attuali); st.rerun()
                    
                    st.divider()
                    st.write(f"### TOTALE: €{totale_tavolo:.2f}")
                    
                    # TASTO CASSA: PAGATO E CHIUDI
                    if st.button(f"PAGATO E CHIUDI TAVOLO {t}", key=f"paga_{t}", type="primary"):
                        # Rimuove tutti gli ordini di questo tavolo
                        nuovi_ordini = [o for o in ordini_attuali if str(o['tavolo']) != str(t)]
                        salva_ordini(nuovi_ordini)
                        st.rerun()

# ---------------------------------------------------------
# INTERFACCIA CLIENTE
# ---------------------------------------------------------
else:
    st.markdown("<h2 style='text-align: center;'>☕ BENVENUTI AL BAR PAGANO</h2>", unsafe_allow_html=True)
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.write("### Seleziona il tuo tavolo per ordinare:")
        for i in range(0, 15, 5):
            cols = st.columns(5)
            for j in range(5):
                n = i + j + 1
                if cols[j].button(f"Tavolo {n}", key=f"t_{n}"):
                    st.session_state.tavolo = str(n); st.rerun()
    else:
        st.markdown(f"<div class='selected-tavolo'>ORDINAZIONE TAVOLO {st.session_state.tavolo}</div>", unsafe_allow_html=True)
        if st.button("⬅️ TORNA ALLA SCELTA TAVOLO"): st.session_state.tavolo = None; st.rerun()
        
        if not menu_df.empty:
            cat_list = sorted(menu_df['categoria'].unique())
            scelta_cat = st.radio("Scegli Categoria:", cat_list, horizontal=True)
            for _, r in menu_df[menu_df['categoria'] == scelta_cat].iterrows():
                if st.button(f"➕ {r['prodotto']} | €{r['prezzo']:.2f}", key=f"b_{r['prodotto']}"):
                    st.session_state.carrello.append(r.to_dict())
                    st.toast(f"Aggiunto: {r['prodotto']}")

        if st.session_state.carrello:
            st.divider()
            st.write("### 🛒 Riassunto Ordine")
            tot = sum(c['prezzo'] for c in st.session_state.carrello)
            for c in st.session_state.carrello:
                st.write(f"- {c['prodotto']} (€{c['prezzo']:.2f})")
            
            if st.button(f"🚀 INVIA ORDINE (€{tot:.2f})", type="primary", use_container_width=True):
                ora = get_ora_italiana()
                for c in st.session_state.carrello:
                    ordini_attuali.append({
                        "id_univoco": f"{time.time()}_{c['prodotto']}", 
                        "tavolo": st.session_state.tavolo,
                        "prodotto": c['prodotto'], "prezzo": c['prezzo'], "stato": "NO", "orario": ora
                    })
                salva_ordini(ordini_attuali)
                st.session_state.carrello = []
                st.success("Ordine inviato! Arriverà tra poco.")
                time.sleep(2); st.rerun()
