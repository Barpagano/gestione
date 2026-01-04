import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BANCONE BAR PAGANO", page_icon="☕", layout="wide")

# --- CSS PERSONALIZZATO (Tasto Pagato sotto l'ordine) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    div[data-testid="column"] button { width: 100% !important; font-weight: bold !important; border-radius: 8px !important; }
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; font-style: italic; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; font-size: 16px; }
    
    /* TASTO PAGATO ROSSO SOTTO OGNI TAVOLO */
    div.stButton > button[kind="primary"] {
        background-color: #D32F2F !important;
        color: white !important;
        height: 60px !important;
        font-size: 20px !important;
        margin-top: 10px !important;
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
STOCK_FILE = "stock_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def carica_ordini():
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []

def salva_ordini(lista):
    pd.DataFrame(lista if lista else [], columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)

# --- INTERFACCIA BANCONE ---
st_autorefresh(interval=5000, key="refresh_bancone")
ordini_attuali = carica_ordini()

# Notifica sonora nuovi ordini
if "ultimo_count" not in st.session_state: st.session_state.ultimo_count = len(ordini_attuali)
if len(ordini_attuali) > st.session_state.ultimo_count:
    suona_notifica()
st.session_state.ultimo_count = len(ordini_attuali)

st.title("👨‍🍳 CONSOLE BANCONE")

if not ordini_attuali:
    st.info("In attesa di ordini dai tavoli...")
else:
    # Mostra i tavoli in una griglia
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
                    
                    # 1. Tasto X per cancellare riga
                    if c_del.button("❌", key=f"del_{r['id_univoco']}"):
                        salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']])
                        st.rerun()
                    
                    # 2. Testo Prodotto
                    stile = "servito" if r['stato'] == "SI" else "da-servire"
                    c_txt.markdown(f"<span class='{stile}'>[{r.get('orario','')}] {r['prodotto']}</span>", unsafe_allow_html=True)
                    
                    # 3. Tasto OK per servito
                    if r['stato'] == "NO" and c_ok.button("Ok", key=f"ok_{r['id_univoco']}"):
                        for o in ordini_attuali:
                            if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                        salva_ordini(ordini_attuali); st.rerun()
                
                st.divider()
                st.markdown(f"### Totale: €{totale_tavolo:.2f}")
                
                # TASTO PAGATO E CHIUDI (Sotto l'ordine)
                if st.button(f"💰 PAGATO E CHIUDI TAVOLO {t}", key=f"paga_{t}", type="primary"):
                    nuovi_ordini = [o for o in ordini_attuali if str(o['tavolo']) != str(t)]
                    salva_ordini(nuovi_ordini)
                    st.rerun()
