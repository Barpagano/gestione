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
    div[data-testid="column"] button {
        width: 100% !important;
        font-weight: bold !important;
        border-radius: 12px !important;
    }
    /* Stile pulsanti grandi del tavolo */
    .stButton > button { height: 80px; font-size: 20px; }
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; font-style: italic; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; font-size: 16px; }
    .prezzo-cassa { color: #4CAF50; font-weight: bold; }
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

# Caricamento dati
menu_df = carica_menu()
ordini_attuali = carica_ordini()

# --- LOGICA UNIFICATA (BANCONE + CASSA) ---
st_autorefresh(interval=5000, key="global_refresh")

# Notifica nuovi ordini
if "ultimo_count" not in st.session_state: st.session_state.ultimo_count = len(ordini_attuali)
if len(ordini_attuali) > st.session_state.ultimo_count:
    suona_notifica()
st.session_state.ultimo_count = len(ordini_attuali)

st.title("☕ BAR PAGANO - Console Unificata")

# Divisione in Tab per separare le operazioni
tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs([
    "📋 ORDINI (Banco)", "💰 CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"
])

# --- TAB 1: ORDINI (BANCONE) ---
with tab_ordini:
    if not ordini_attuali: 
        st.info("In attesa di nuovi ordini...")
    else:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        cols = st.columns(3)
        for idx, t in enumerate(tavoli_attivi):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"🪑 Tavolo {t}")
                    items = [o for o in ordini_attuali if str(o['tavolo']) == str(t)]
                    for r in items:
                        c1, c2, c3 = st.columns([0.6, 3, 1])
                        # Elimina riga singola
                        if c1.button("❌", key=f"del_{r['id_univoco']}"):
                            salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                        # Testo prodotto
                        cl = "servito" if r['stato'] == "SI" else "da-servire"
                        c2.markdown(f"<span class='{cl}'>[{r.get('orario','')}] {r['prodotto']}</span>", unsafe_allow_html=True)
                        # Segna come servito
                        if r['stato'] == "NO" and c3.button("Ok", key=f"ok_{r['id_univoco']}"):
                            for o in ordini_attuali: 
                                if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                            salva_ordini(ordini_attuali); st.rerun()

# --- TAB 2: CASSA ---
with tab_cassa:
    tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
    if not tavoli_attivi:
        st.info("Nessun conto aperto.")
    else:
        cols_c = st.columns(2)
        for idx, t in enumerate(tavoli_attivi):
            with cols_c[idx % 2]:
                with st.container(border=True):
                    items = [o for o in ordini_attuali if str(o['tavolo']) == str(t)]
                    totale = sum(float(x['prezzo']) for x in items)
                    st.markdown(f"### Tavolo {t}")
                    for r in items:
                        st.markdown(f"• {r['prodotto']} <span class='prezzo-cassa'>€{float(r['prezzo']):.2f}</span>", unsafe_allow_html=True)
                    st.divider()
                    st.write(f"#### TOTALE: €{totale:.2f}")
                    if st.button(f"PAGATO E CHIUDI TAVOLO {t}", key=f"pay_{t}", type="primary"):
                        salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != str(t)])
                        st.rerun()

# --- TAB 3: VETRINA (SCALCO RAPIDO) ---
with tab_vetrina:
    stk = carica_stock()
    st.write("Sottrai velocemente i prodotti dalla vetrina:")
    cv = st.columns(4)
    for i, (p, q) in enumerate(stk.items()):
        if cv[i % 4].button(f"{p}\n({q})", key=f"vr_{p}", disabled=(q <= 0)):
            stk[p] = max(0, q - 1); salva_stock(stk); st.rerun()

# --- TAB 4: GESTIONE STOCK ---
with tab_stock:
    stk = carica_stock()
    with st.expander("➕ Aggiungi prodotto al monitoraggio stock"):
        if not menu_df.empty:
            c1, c2 = st.columns(2)
            cat_stk = c1.selectbox("Filtra Categoria", sorted(menu_df['categoria'].unique()), key="stk_cat")
            prod_filtrati = menu_df[menu_df['categoria'] == cat_stk]['prodotto'].unique()
            nuovo_s = c2.selectbox("Prodotto", prod_filtrati, key="stk_prod")
            if st.button("AGGIUNGI ALLO STOCK ✅", use_container_width=True):
                if nuovo_s not in stk: stk[nuovo_s] = 0; salva_stock(stk); st.rerun()
    
    st.divider()
    for p, q in stk.items():
        cx, cm, cq, cp, cd = st.columns([3, 1, 1, 1, 1])
        cx.write(f"**{p}**")
        if cm.button("➖", key=f"sm_{p}"): stk[p] = max(0, q-1); salva_stock(stk); st.rerun()
        cq.write(f"**{q}**")
        if cp.button("➕", key=f"sp_{p}"): stk[p] = q+1; salva_stock(stk); st.rerun()
        if cd.button("🗑️", key=f"sdel_{p}"): del stk[p]; salva_stock(stk); st.rerun()

# --- TAB 5: GESTIONE MENU ---
with tab_menu:
    st.subheader("⚙️ Modifica Listino Prezzi")
    with st.form("add_new"):
        c1, c2 = st.columns(2)
        cat_e = c1.selectbox("Categoria Esistente", ["---"] + sorted(list(menu_df['categoria'].unique())) if not menu_df.empty else ["---"])
        cat_n = c2.text_input("O Nuova Categoria")
        nome_n = st.text_input("Nome Prodotto")
        prez_n = st.number_input("Prezzo (€)", min_value=0.0, step=0.1, format="%.2f")
        if st.form_submit_button("AGGIUNGI AL MENU"):
            cat_f = cat_n if cat_n.strip() != "" else cat_e
            if cat_f != "---" and nome_n:
                nuovo = pd.DataFrame([{"categoria": cat_f, "prodotto": nome_n, "prezzo": prez_n}])
                pd.concat([menu_df, nuovo], ignore_index=True).to_csv(MENU_FILE, index=False); st.rerun()
