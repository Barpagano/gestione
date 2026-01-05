import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# --- CSS PER GRIGLIA COMPATTA 3x5 SENZA SPAZI ---
st.markdown("""
    <style>
    /* Sfondo nero assoluto e testo bianco */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* RIMUOVE SPAZI TRA RIGHE E COLONNE */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        margin-bottom: 0px !important;
    }
    
    [data-testid="column"] {
        padding: 0px !important;
        margin: 0px !important;
    }

    /* TASTI TAVOLI: Grandi, quadrati e senza bordi */
    .stButton > button {
        width: 100% !important;
        height: 90px !important; /* Molto alto per touch facile */
        border-radius: 0px !important; /* Angoli vivi per unirli */
        font-weight: 900 !important;
        font-size: 26px !important;
        margin: 0px !important;
        border: 1px solid #111111 !important; /* Sottile linea di separazione */
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* TAVOLO LIBERO: Verde Fluo / Testo Nero */
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

    /* Centra Logo e Titolo */
    .header-box { text-align: center; padding: 10px; }
    
    /* Pulizia Interfaccia */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATI ---
def get_ora():
    return datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")

DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def inizializza_files():
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=["id", "tavolo", "prodotto", "prezzo", "stato", "ora"]).to_csv(DB_FILE, index=False)
    if not os.path.exists(MENU_FILE):
        # Menu di esempio se il file non esiste
        pd.DataFrame({
            "categoria": ["Caffetteria", "Caffetteria", "Drink"],
            "prodotto": ["Espresso", "Cappuccino", "Spritz"],
            "prezzo": [1.0, 1.5, 5.0]
        }).to_csv(MENU_FILE, index=False)

inizializza_files()

def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []

def salva_ordini(lista): 
    pd.DataFrame(lista if lista else [], columns=["id", "tavolo", "prodotto", "prezzo", "stato", "ora"]).to_csv(DB_FILE, index=False)

# Refresh automatico ogni 5 secondi
st_autorefresh(interval=5000, key="refresh_global")
ordini = carica_ordini()
ruolo = st.query_params.get("ruolo", "cliente")

# --- INTESTAZIONE ---
st.markdown('<div class="header-box">', unsafe_allow_html=True)
st.markdown("<h1 style='color: #00FF00; margin:0;'>BAR PAGANO</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BANCONE (GESTIONE)
# =========================================================
if ruolo == "banco":
    st.markdown("<h3 style='text-align:center;'> Pannello Comande</h3>", unsafe_allow_html=True)
    tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini)))
    
    if not tavoli_attivi:
        st.info("In attesa di comande...")
    else:
        for t in tavoli_attivi:
            with st.container(border=True):
                st.write(f"### 🪑 Tavolo {t}")
                items = [o for o in ordini if str(o['tavolo']) == t]
                totale = sum(float(o['prezzo']) for o in items)
                for r in items:
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
# CLIENTE (GRIGLIA COMPATTA 3x5)
# =========================================================
else:
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.markdown("<p style='text-align:center; font-weight:bold;'>TOCCA IL TUO TAVOLO</p>", unsafe_allow_html=True)
        occupati = set(str(o['tavolo']) for o in ordini)
        
        # COSTRUZIONE GRIGLIA 3 RIGHE x 5 COLONNE
        for riga in range(3): # 3 righe
            cols = st.columns(5) # 5 colonne per riga
            for colonna in range(5):
                n = str((riga * 5) + colonna + 1)
                is_occ = n in occupati
                classe = "btn-occupato" if is_occ else "btn-libero"
                
                with cols[colonna]:
                    st.markdown(f'<div class="{classe}">', unsafe_allow_html=True)
                    if st.button(n, key=f"t_{n}", disabled=is_occ):
                        st.session_state.tavolo = n
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        # MENU ORDINAZIONE
        st.markdown(f"<div style='background-color:#00FF00; color:black; text-align:center; padding:10px; font-weight:bold; font-size:22px;'>TAVOLO {st.session_state.tavolo}</div>", unsafe_allow_html=True)
        if st.button("⬅️ CAMBIA TAVOLO", use_container_width=True):
            st.session_state.tavolo = None; st.rerun()
        
        menu_df = pd.read_csv(MENU_FILE)
        categorie = sorted(menu_df['categoria'].unique())
        scelta = st.radio("Scegli Categoria:", categorie, horizontal=True)
        
        st.markdown("---")
        prodotti_filtrati = menu_df[menu_df['categoria'] == scelta]
        for _, r in prodotti_filtrati.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{r['prodotto']}**\n€{r['prezzo']:.2f}")
            if c2.button("➕", key=f"add_{r['prodotto']}"):
                st.session_state.carrello.append(r.to_dict())
                st.rerun()

        # CARRELLO
        if st.session_state.carrello:
            st.markdown("<div style='background-color:#111111; padding:15px; border-radius:10px; margin-top:20px; border:1px solid #333;'>", unsafe_allow_html=True)
            st.subheader("🛒 Riepilogo Carrello")
            tot = sum(i['prezzo'] for i in st.session_state.carrello)
            for i, item in enumerate(st.session_state.carrello):
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
                        "tavolo": st.session_state.tavolo, 
                        "prodotto": item['prodotto'],
                        "prezzo": item['prezzo'], 
                        "stato": "NO", 
                        "ora": ora_attuale
                    })
                salva_ordini(ordini)
                st.session_state.carrello = []
                st.success("Inviato!"); time.sleep(1); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
