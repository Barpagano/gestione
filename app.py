import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", page_icon="☕", layout="wide")

# --- CSS PERSONALIZZATO (GRIGLIA COMPATTA 5 COLONNE) ---
st.markdown("""
    <style>
    /* Dark Mode Totale */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Forza i contenitori delle colonne a stare vicini */
    [data-testid="stHorizontalBlock"] {
        gap: 2px !important; /* Spazio minimo tra le colonne */
    }
    
    [data-testid="column"] {
        padding: 0px !important;
        margin: 0px !important;
    }

    /* STILE TASTI TAVOLI */
    .stButton > button {
        width: 100% !important;
        height: 70px !important;
        border-radius: 4px !important;
        font-weight: 900 !important;
        font-size: 22px !important;
        border: 1px solid #333333 !important;
        transition: 0.2s;
        margin: 0px !important;
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

    /* Logo e Intestazioni */
    .logo-text { text-align: center; color: #00FF00; font-weight: bold; font-size: 40px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SERVIZIO ---
def get_ora_italiana():
    tz = pytz.timezone('Europe/Rome')
    return datetime.now(tz).strftime("%H:%M")

# --- GESTIONE DATABASE ---
DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"
COLONNE_ORDINI = ["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]

def inizializza_file(file, colonne):
    if not os.path.exists(file) or os.stat(file).st_size <= 2:
        pd.DataFrame(columns=colonne).to_csv(file, index=False)

inizializza_file(DB_FILE, COLONNE_ORDINI)
inizializza_file(MENU_FILE, ["categoria", "prodotto", "prezzo"])

def carica_menu(): return pd.read_csv(MENU_FILE)
def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []
def salva_ordini(lista): pd.DataFrame(lista if lista else [], columns=COLONNE_ORDINI).to_csv(DB_FILE, index=False)

menu_df = carica_menu()
ordini_attuali = carica_ordini()

# --- REFRESH ---
st_autorefresh(interval=5000, key="global_refresh")
ruolo = st.query_params.get("ruolo", "cliente")

# --- LOGO / TITOLO ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=200)
else:
    st.markdown("<div class='logo-text'>BAR PAGANO</div>", unsafe_allow_html=True)

# =========================================================
# BANCONE (RUOLO=BANCO)
# =========================================================
if ruolo == "banco":
    st.subheader("Gestione Ordini")
    if not ordini_attuali: st.info("In attesa di ordini...")
    else:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        cols = st.columns(3)
        for idx, t in enumerate(tavoli_attivi):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"### 🪑 Tavolo {t}")
                    items = [o for o in ordini_attuali if str(o['tavolo']) == str(t)]
                    tot = sum(float(o['prezzo']) for o in items)
                    for r in items:
                        cl = "text-decoration: line-through; color: gray;" if r['stato'] == "SI" else "color: white;"
                        c1, c2 = st.columns([4, 1])
                        c1.markdown(f"<span style='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                        if r['stato'] == "NO" and c2.button("Ok", key=f"ok_{r['id_univoco']}"):
                            for o in ordini_attuali: 
                                if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                            salva_ordini(ordini_attuali); st.rerun()
                    st.write(f"**Totale: €{tot:.2f}**")
                    if st.button(f"CHIUDI TAVOLO", key=f"pay_{t}", type="primary"):
                        salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != str(t)]); st.rerun()

# =========================================================
# CLIENTE (FILA DA 5 TASTI)
# =========================================================
else:
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.markdown("<p style='text-align:center;'>SELEZIONA TAVOLO</p>", unsafe_allow_html=True)
        tavoli_occupati = set(str(o['tavolo']) for o in ordini_attuali)
        
        # LOGICA FILA DA 5
        for i in range(0, 15, 5):
            cols = st.columns(5) # Forza 5 colonne
            for j in range(5):
                n = i + j + 1
                if n <= 15:
                    t_str = str(n)
                    is_occ = t_str in tavoli_occupati
                    classe = "btn-occupato" if is_occ else "btn-libero"
                    
                    with cols[j]:
                        st.markdown(f'<div class="{classe}">', unsafe_allow_html=True)
                        if st.button(f"{n}", key=f"t_{n}", disabled=is_occ):
                            st.session_state.tavolo = t_str
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # MENU ORDINAZIONE
        st.markdown(f"<h2 style='text-align:center; color:#00FF00;'>TAVOLO {st.session_state.tavolo}</h2>", unsafe_allow_html=True)
        if st.button("⬅️ CAMBIA TAVOLO", use_container_width=True):
            st.session_state.tavolo = None
            st.rerun()
        
        if not menu_df.empty:
            categorie = sorted(menu_df['categoria'].unique())
            scelta = st.radio("Scegli:", categorie, horizontal=True)
            st.divider()
            
            prodotti = menu_df[menu_df['categoria'] == scelta]
            for _, r in prodotti.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
                if c2.button("➕", key=f"add_{r['prodotto']}"):
                    item = r.to_dict(); item['temp_id'] = time.time()
                    st.session_state.carrello.append(item); st.rerun()

        if st.session_state.carrello:
            st.markdown("---")
            st.subheader("🛒 CARRELLO")
            tot = sum(item['prezzo'] for item in st.session_state.carrello)
            for i, item in enumerate(st.session_state.carrello):
                c_n, c_e = st.columns([4, 1])
                c_n.write(f"{item['prodotto']} (€{item['prezzo']:.2f})")
                if c_e.button("❌", key=f"rm_{i}"):
                    st.session_state.carrello.pop(i); st.rerun()
            
            st.write(f"### TOTALE: €{tot:.2f}")
            if st.button("🚀 INVIA ORDINE", type="primary", use_container_width=True):
                ora = get_ora_italiana()
                for item in st.session_state.carrello:
                    ordini_attuali.append({"id_univoco": f"{time.time()}_{item['prodotto']}", "tavolo": st.session_state.tavolo, "prodotto": item['prodotto'], "prezzo": item['prezzo'], "stato": "NO", "orario": ora})
                salva_ordini(ordini_attuali)
                st.session_state.carrello = []
                st.success("Ordine Inviato!")
                time.sleep(1); st.rerun()
