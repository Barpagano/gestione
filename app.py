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

# --- CSS PERSONALIZZATO (DARK MODE & GRID COMPATTA) ---
st.markdown("""
    <style>
    /* Dark Mode Totale */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Rimuove i margini standard di Streamlit per avvicinare i tasti */
    [data-testid="column"] { 
        padding: 1px !important; 
        margin: 0px !important;
    }
    
    /* Contenitore Flex per i tavoli (li mette vicini) */
    .tavoli-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 5px; /* Spazio minimo tra i tasti */
        padding: 10px;
    }

    /* STILE BASE TASTI TAVOLI */
    .stButton > button {
        width: 100% !important;
        height: 80px !important;
        border-radius: 8px !important;
        font-weight: 900 !important;
        font-size: 24px !important;
        border: none !important;
        transition: 0.3s;
    }

    /* TAVOLO LIBERO: Verde Fluo / Testo Nero */
    .btn-libero div[data-testid="stButton"] > button {
        background-color: #00FF00 !important;
        color: #000000 !important;
        box-shadow: inset 0px 0px 10px rgba(0,0,0,0.5);
    }

    /* TAVOLO OCCUPATO: Rosso / Testo Bianco */
    .btn-occupato div[data-testid="stButton"] > button {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
        opacity: 1 !important;
    }

    /* CATEGORIE MENU */
    div[data-testid="stMarkdownContainer"] h3 { color: #00FF00; }
    
    /* Logo Centrato */
    .logo-img { display: block; margin-left: auto; margin-right: auto; width: 150px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SERVIZIO ---
def get_ora_italiana():
    tz = pytz.timezone('Europe/Rome')
    return datetime.now(tz).strftime("%H:%M")

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

menu_df = carica_menu()
ordini_attuali = carica_ordini()

# --- REFRESH ---
st_autorefresh(interval=5000, key="global_refresh")
ruolo = st.query_params.get("ruolo", "cliente")

# --- LOGO ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=180)
else:
    st.markdown("<h1 style='text-align: center; color: #00FF00;'>BAR PAGANO</h1>", unsafe_allow_html=True)

# =========================================================
# SCHERMATA GESTIONE (BANCO)
# =========================================================
if ruolo == "banco":
    tab_ordini, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])
    
    with tab_ordini:
        if not ordini_attuali: st.info("Nessun ordine attivo")
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
                            cl = "text-decoration: line-through; color: gray;" if r['stato'] == "SI" else "color: white; font-weight: bold;"
                            c1, c2 = st.columns([3, 1])
                            c1.markdown(f"<span style='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                            if r['stato'] == "NO" and c2.button("Ok", key=f"ok_{r['id_univoco']}"):
                                for o in ordini_attuali: 
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()
                        st.write(f"**Totale: €{tot:.2f}**")
                        if st.button(f"PAGATO E CHIUDI", key=f"pay_{t}"):
                            salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != str(t)]); st.rerun()

# =========================================================
# SCHERMATA CLIENTE (OTTIMIZZATA MOBILE)
# =========================================================
else:
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.markdown("<h3 style='text-align: center;'>SELEZIONA TAVOLO</h3>", unsafe_allow_html=True)
        tavoli_occupati = set(str(o['tavolo']) for o in ordini_attuali)
        
        # Griglia compatta 3 colonne
        for i in range(0, 15, 3):
            cols = st.columns(3)
            for j in range(3):
                n = i + j + 1
                if n <= 15:
                    t_str = str(n)
                    if t_str in tavoli_occupati:
                        st.markdown('<div class="btn-occupato">', unsafe_allow_html=True)
                        cols[j].button(f"{n}\nOCC", key=f"t_{n}", disabled=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="btn-libero">', unsafe_allow_html=True)
                        if cols[j].button(f"{n}", key=f"t_{n}"):
                            st.session_state.tavolo = t_str
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Intestazione Tavolo Selezionato
        st.markdown(f"<div style='background-color: #00FF00; color: black; text-align: center; padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 20px;'>ORDINANDO AL TAVOLO {st.session_state.tavolo}</div>", unsafe_allow_html=True)
        if st.button("⬅️ CAMBIA TAVOLO", use_container_width=True): st.session_state.tavolo = None; st.rerun()
        
        if not menu_df.empty:
            categorie = sorted(menu_df['categoria'].unique())
            scelta = st.pills("Categorie:", categorie) if hasattr(st, "pills") else st.radio("Menu:", categorie, horizontal=True)
            
            st.markdown("---")
            prodotti = menu_df[menu_df['categoria'] == scelta] if scelta else menu_df
            for _, r in prodotti.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{r['prodotto']}**\n\n€{r['prezzo']:.2f}")
                if c2.button("➕", key=f"add_{r['prodotto']}"):
                    item = r.to_dict(); item['temp_id'] = time.time()
                    st.session_state.carrello.append(item); st.rerun()

        if st.session_state.carrello:
            st.markdown("<div style='background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #00FF00;'>", unsafe_allow_html=True)
            st.subheader("🛒 CARRELLO")
            tot = 0
            for i, item in enumerate(st.session_state.carrello):
                tot += item['prezzo']
                col_n, col_e = st.columns([4, 1])
                col_n.write(f"{item['prodotto']} (€{item['prezzo']:.2f})")
                if col_e.button("❌", key=f"rm_{i}"):
                    st.session_state.carrello.pop(i); st.rerun()
            
            st.markdown(f"### TOTALE: €{tot:.2f}")
            if st.button("🚀 INVIA ORDINE", type="primary", use_container_width=True):
                ora = get_ora_italiana()
                for item in st.session_state.carrello:
                    ordini_attuali.append({"id_univoco": f"{time.time()}_{item['prodotto']}", "tavolo": st.session_state.tavolo, "prodotto": item['prodotto'], "prezzo": item['prezzo'], "stato": "NO", "orario": ora})
                salva_ordini(ordini_attuali); st.session_state.carrello = []; st.success("Ordine Inviato!"); time.sleep(1); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
