import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# --- CSS PER DARK MODE, LOGO E TASTI ATTACCATI (FILE DA 5) ---
st.markdown("""
    <style>
    /* Sfondo nero assoluto */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Forza la fila da 5 e rimuove spazi tra le colonne */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0px !important;
    }
    
    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
        padding: 0px !important;
        margin: 0px !important;
    }

    /* TASTI TAVOLI: Grandi, senza arrotondamenti e attaccati */
    .stButton > button {
        width: 100% !important;
        height: 80px !important; 
        border-radius: 0px !important;
        font-weight: 900 !important;
        font-size: 24px !important;
        border: 0.5px solid #111111 !important;
        margin: 0px !important;
    }

    /* TAVOLO LIBERO: Verde Fluo / Testo Nero (Massimo Contrasto) */
    .btn-libero div[data-testid="stButton"] > button {
        background-color: #00FF00 !important;
        color: #000000 !important;
    }

    /* TAVOLO OCCUPATO: Rosso / Testo Bianco */
    .btn-occupato div[data-testid="stButton"] > button {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
        opacity: 1 !important;
    }

    /* Logo Centrato */
    .logo-box { text-align: center; padding: 10px; }
    
    /* Nasconde menu Streamlit per pulizia */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SERVIZIO ---
def get_ora():
    return datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")

DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def inizializza_files():
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=["id", "tavolo", "prodotto", "prezzo", "stato", "ora"]).to_csv(DB_FILE, index=False)
    if not os.path.exists(MENU_FILE):
        pd.DataFrame({"categoria": ["Caffetteria"], "prodotto": ["Espresso"], "prezzo": [1.0]}).to_csv(MENU_FILE, index=False)

inizializza_files()

def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []

def salva_ordini(lista): 
    pd.DataFrame(lista if lista else [], columns=["id", "tavolo", "prodotto", "prezzo", "stato", "ora"]).to_csv(DB_FILE, index=False)

# Auto-refresh ogni 5 secondi per vedere i nuovi ordini
st_autorefresh(interval=5000, key="refresh_global")
ordini = carica_ordini()
ruolo = st.query_params.get("ruolo", "cliente")

# --- LOGO ---
st.markdown('<div class="logo-box">', unsafe_allow_html=True)
if os.path.exists("logo.png"):
    st.image("logo.png", width=180) # Assicurati di caricare il file logo.png su GitHub
else:
    st.markdown("<h1 style='color: #00FF00; margin:0;'>BAR PAGANO</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BANCONE (GESTIONE) - link: ?ruolo=banco
# =========================================================
if ruolo == "banco":
    st.markdown("<h3 style='text-align:center;'> Pannello Comande</h3>", unsafe_allow_html=True)
    tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini)))
    
    if not tavoli_attivi:
        st.info("Nessun ordine in sospeso")
    else:
        for t in tavoli_attivi:
            with st.container(border=True):
                st.write(f"### Tavolo {t}")
                items = [o for o in ordini if str(o['tavolo']) == t]
                totale = 0
                for r in items:
                    totale += float(r['prezzo'])
                    c1, c2 = st.columns([4, 1])
                    cl = "text-decoration: line-through; color: gray;" if r['stato'] == "SI" else "color: white;"
                    c1.markdown(f"<span style='{cl}'>{r['prodotto']} ({r['ora']})</span>", unsafe_allow_html=True)
                    if r['stato'] == "NO" and c2.button("OK", key=f"ok_{r['id']}"):
                        for o in ordini: 
                            if o['id'] == r['id']: o['stato'] = "SI"
                        salva_ordini(ordini); st.rerun()
                st.write(f"**Totale: €{totale:.2f}**")
                if st.button(f"LIBERA TAVOLO {t}", key=f"pay_{t}", type="primary"):
                    salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()

# =========================================================
# CLIENTE (INTERFACCIA SMARTPHONE)
# =========================================================
else:
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.markdown("<p style='text-align:center;'>TOCCA IL TUO TAVOLO</p>", unsafe_allow_html=True)
        occupati = set(str(o['tavolo']) for o in ordini)
        
        # Griglia 15 tavoli, file da 5, zero spazio
        for i in range(0, 15, 5):
            cols = st.columns(5)
            for j in range(5):
                n = str(i + j + 1)
                is_occ = n in occupati
                classe = "btn-occupato" if is_occ else "btn-libero"
                
                with cols[j]:
                    st.markdown(f'<div class="{classe}">', unsafe_allow_html=True)
                    if st.button(n, key=f"t_{n}", disabled=is_occ):
                        st.session_state.tavolo = n
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        # MENU PRODOTTI
        st.markdown(f"<div style='background-color:#00FF00; color:black; text-align:center; padding:10px; font-weight:bold; font-size:20px; border-radius:5px; margin-bottom:10px;'>TAVOLO {st.session_state.tavolo}</div>", unsafe_allow_html=True)
        if st.button("⬅️ CAMBIA TAVOLO", use_container_width=True):
            st.session_state.tavolo = None; st.rerun()
        
        menu_df = pd.read_csv(MENU_FILE)
        categorie = sorted(menu_df['categoria'].unique())
        scelta = st.radio("Scegli:", categorie, horizontal=True)
        
        st.markdown("---")
        prodotti = menu_df[menu_df['categoria'] == scelta]
        for _, r in prodotti.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{r['prodotto']}**\n€{r['prezzo']:.2f}")
            if c2.button("➕", key=f"add_{r['prodotto']}"):
                item = r.to_dict()
                item['temp_id'] = time.time()
                st.session_state.carrello.append(item); st.rerun()

        # CARRELLO
        if st.session_state.carrello:
            st.markdown("<div style='background-color:#111111; padding:10px; border-radius:10px; margin-top:20px;'>", unsafe_allow_html=True)
            st.subheader("🛒 Carrello")
            tot = 0
            for i, item in enumerate(st.session_state.carrello):
                tot += item['prezzo']
                cn, ce = st.columns([4, 1])
                cn.write(f"{item['prodotto']} (€{item['prezzo']:.2f})")
                if ce.button("❌", key=f"rm_{i}"):
                    st.session_state.carrello.pop(i); st.rerun()
            
            st.write(f"### TOTALE: €{tot:.2f}")
            if st.button("🚀 INVIA ORDINE ORA", type="primary", use_container_width=True):
                ora_attuale = get_ora()
                for item in st.session_state.carrello:
                    ordini.append({
                        "id": f"{time.time()}_{item['prodotto']}",
                        "tavolo": st.session_state.tavolo, "prodotto": item['prodotto'],
                        "prezzo": item['prezzo'], "stato": "NO", "ora": ora_attuale
                    })
                salva_ordini(ordini)
                st.session_state.carrello = []
                st.success("Inviato al banco!"); time.sleep(1); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
