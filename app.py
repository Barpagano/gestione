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
    page_title="PAGANOCAFE - GESTIONE", 
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
    .stButton > button { height: 80px; font-size: 20px; background-color: #d4af37; color: black; }
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
    try:
        df = pd.read_csv(DB_FILE)
        return df.to_dict('records') if not df.empty else []
    except: return []

def salva_ordini(lista): pd.DataFrame(lista if lista else [], columns=COLONNE_ORDINI).to_csv(DB_FILE, index=False)

def carica_stock(): 
    try:
        df = pd.read_csv(STOCK_FILE)
        return df.set_index('prodotto')['quantita'].to_dict() if not df.empty else {}
    except: return {}

def salva_stock(d): pd.DataFrame(list(d.items()), columns=['prodotto', 'quantita']).to_csv(STOCK_FILE, index=False)

# --- LOGICA ---
st_autorefresh(interval=5000, key="global_refresh")

menu_df = carica_menu()
ordini_attuali = carica_ordini()

# Notifica nuovi ordini
if "ultimo_count" not in st.session_state: st.session_state.ultimo_count = len(ordini_attuali)
if len(ordini_attuali) > st.session_state.ultimo_count:
    suona_notifica()
st.session_state.ultimo_count = len(ordini_attuali)

# Controllo Ruolo
admin_mode = st.query_params.get("admin") == "si"

if admin_mode:
    st.title("☕ PAGANOCAFE - Console Unificata")
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs([
        "📋 ORDINI (Banco)", "💰 CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"
    ])

    with tab_ordini:
        if not ordini_attuali: st.info("In attesa di nuovi ordini...")
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
                            if c1.button("❌", key=f"del_{r['id_univoco']}"):
                                salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                            cl = "servito" if r['stato'] == "SI" else "da-servire"
                            c2.markdown(f"<span class='{cl}'>[{r.get('orario','')}] {r['prodotto']}</span>", unsafe_allow_html=True)
                            if r['stato'] == "NO" and c3.button("Ok", key=f"ok_{r['id_univoco']}"):
                                for o in ordini_attuali: 
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()

    with tab_cassa:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        if not tavoli_attivi: st.info("Nessun conto aperto.")
        else:
            for t in tavoli_attivi:
                with st.container(border=True):
                    items = [o for o in ordini_attuali if str(o['tavolo']) == str(t)]
                    totale = sum(float(x['prezzo']) for x in items)
                    st.write(f"### Tavolo {t} - Totale: €{totale:.2f}")
                    if st.button(f"PAGATO E CHIUDI TAVOLO {t}", key=f"pay_{t}", type="primary"):
                        salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != str(t)]); st.rerun()

    with tab_vetrina:
        stk = carica_stock()
        st.write("Scarico rapido vetrina:")
        cv = st.columns(4)
        for i, (p, q) in enumerate(stk.items()):
            if cv[i % 4].button(f"{p}\n({q})", key=f"vr_{p}"):
                stk[p] = max(0, q - 1); salva_stock(stk); st.rerun()

    with tab_stock:
        stk = carica_stock()
        with st.expander("➕ Aggiungi prodotto allo stock"):
            if not menu_df.empty:
                prod_selezionato = st.selectbox("Seleziona prodotto dal menu", menu_df['prodotto'].unique())
                if st.button("AGGIUNGI"):
                    if prod_selezionato not in stk: stk[prod_selezionato] = 0; salva_stock(stk); st.rerun()
        for p, q in stk.items():
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{p}**")
            if c2.button("➖", key=f"m_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
            c3.write(f"{q}")
            if c4.button("➕", key=f"p_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()

    with tab_menu:
        st.subheader("⚙️ Modifica Menu")
        with st.form("add_new"):
            c1, c2 = st.columns(2)
            cat_n = c1.text_input("Categoria")
            nome_n = c2.text_input("Nome Prodotto")
            prez_n = st.number_input("Prezzo (€)", step=0.1)
            if st.form_submit_button("AGGIUNGI"):
                nuovo = pd.DataFrame([{"categoria": cat_n, "prodotto": nome_n, "prezzo": prez_n}])
                pd.concat([menu_df, nuovo]).to_csv(MENU_FILE, index=False); st.rerun()

else:
    # --- LATO CLIENTE ---
    st.markdown("<h1 style='text-align:center;'>🥐 PAGANOCAFE</h1>", unsafe_allow_html=True)
    tavolo_sel = st.selectbox("Seleziona Tavolo:", ["---"] + [str(i) for i in range(1, 16)])
    
    if tavolo_sel != "---":
        cat_sel = st.radio("Scegli:", menu_df['categoria'].unique(), horizontal=True)
        stk = carica_stock()
        
        prodotti = menu_df[menu_df['categoria'] == cat_sel]
        for _, r in prodotti.iterrows():
            c1, c2 = st.columns([3, 1])
            q_disp = stk.get(r['prodotto'], 999)
            c1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
            if q_disp > 0:
                if c2.button("ORDINA", key=f"ord_{r['prodotto']}"):
                    # SCALO STOCK AUTOMATICO
                    if r['prodotto'] in stk:
                        stk[r['prodotto']] -= 1
                        salva_stock(stk)
                    # SALVO ORDINE
                    nuovo_o = {
                        "id_univoco": str(time.time()), "tavolo": tavolo_sel, 
                        "prodotto": r['prodotto'], "prezzo": r['prezzo'], 
                        "stato": "NO", "orario": get_ora_italiana()
                    }
                    ordini_attuali.append(nuovo_o)
                    salva_ordini(ordini_attuali)
                    st.success("Inviato!"); time.sleep(1); st.rerun()
            else:
                c2.error("ESAURITO")
