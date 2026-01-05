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
    
    /* TASTO PAGATO E CHIUDI (ROSSO) */
    .btn-paga > div[data-testid="stButton"] > button {
        background-color: #D32F2F !important;
        color: white !important;
        height: 60px !important;
        font-size: 20px !important;
        border: 2px solid #FF5252 !important;
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

def inizializza_file(file, colonne):
    if not os.path.exists(file) or os.stat(file).st_size <= 2:
        pd.DataFrame(columns=colonne).to_csv(file, index=False)

inizializza_file(DB_FILE, ["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"])
inizializza_file(MENU_FILE, ["categoria", "prodotto", "prezzo"])
inizializza_file(STOCK_FILE, ["prodotto", "quantita"])

def carica_menu(): return pd.read_csv(MENU_FILE)
def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []
def salva_ordini(lista): pd.DataFrame(lista if lista else [], columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)
def carica_stock(): 
    df = pd.read_csv(STOCK_FILE)
    return df.set_index('prodotto')['quantita'].to_dict() if not df.empty else {}
def salva_stock(d): pd.DataFrame(list(d.items()), columns=['prodotto', 'quantita']).to_csv(STOCK_FILE, index=False)

# --- LOGICA CORE ---
ruolo = st.query_params.get("ruolo", "cliente")
menu_df = carica_menu()
ordini_attuali = carica_ordini()

# ---------------------------------------------------------
# INTERFACCIA BANCONE
# ---------------------------------------------------------
if ruolo == "banco":
    st_autorefresh(interval=5000, key="banco_refresh")
    st.title("👨‍🍳 CONSOLE BANCONE - BAR PAGANO")
    
    if "ultimo_count" not in st.session_state: st.session_state.ultimo_count = len(ordini_attuali)
    if len(ordini_attuali) > st.session_state.ultimo_count:
        suona_notifica()
    st.session_state.ultimo_count = len(ordini_attuali)

    tab_ordini, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])
    
    with tab_ordini:
        if not ordini_attuali:
            st.info("In attesa di ordini...")
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
                            c_del, c_txt, c_ok = st.columns([0.6, 3, 1])
                            if c_del.button("❌", key=f"del_{r['id_univoco']}"):
                                salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                            stile = "servito" if r['stato'] == "SI" else "da-servire"
                            c_txt.markdown(f"<span class='{stile}'>[{r.get('orario','')}] {r['prodotto']}</span>", unsafe_allow_html=True)
                            if r['stato'] == "NO" and c_ok.button("Ok", key=f"ok_{r['id_univoco']}"):
                                for o in ordini_attuali:
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()
                        
                        st.divider()
                        st.write(f"### TOTALE: €{totale_tavolo:.2f}")
                        
                        # TASTO PAGATO E CHIUDI INTEGRATO SOTTO L'ORDINE
                        st.markdown('<div class="btn-paga">', unsafe_allow_html=True)
                        if st.button(f"PAGATO E CHIUDI {t}", key=f"paga_{t}", type="primary"):
                            salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != str(t)])
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

    with tab_vetrina:
        stk = carica_stock()
        cv = st.columns(4)
        for i, (p, q) in enumerate(stk.items()):
            if cv[i % 4].button(f"{p}\n({q})", key=f"vtr_{p}", disabled=(q <= 0)):
                stk[p] = max(0, q - 1); salva_stock(stk); st.rerun()

    with tab_stock:
        stk = carica_stock()
        for p, q in stk.items():
            cx, cm, cq, cp, cd = st.columns([3, 1, 1, 1, 1])
            cx.write(f"**{p}**")
            if cm.button("➖", key=f"m_{p}"): stk[p]=max(0,q-1); salva_stock(stk); st.rerun()
            cq.write(f"**{q}**")
            if cp.button("➕", key=f"p_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()
            if cd.button("🗑️", key=f"d_{p}"): del stk[p]; salva_stock(stk); st.rerun()

    with tab_menu:
        with st.form("new_p"):
            c1, c2, c3 = st.columns(3)
            cat = c1.text_input("Categoria")
            prod = c2.text_input("Prodotto")
            prezzo = c3.number_input("Prezzo", step=0.1)
            if st.form_submit_button("AGGIUNGI"):
                nuovo = pd.DataFrame([{"categoria": cat, "prodotto": prod, "prezzo": prezzo}])
                pd.concat([menu_df, nuovo]).to_csv(MENU_FILE, index=False); st.rerun()

# ---------------------------------------------------------
# INTERFACCIA CLIENTE
# ---------------------------------------------------------
else:
    st.markdown("<h2 style='text-align: center;'>☕ BAR PAGANO</h2>", unsafe_allow_html=True)
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.write("### Seleziona il tuo tavolo:")
        for i in range(0, 15, 5):
            cols = st.columns(5)
            for j in range(5):
                n = i + j + 1
                if cols[j].button(f"{n}", key=f"t_{n}"):
                    st.session_state.tavolo = str(n); st.rerun()
    else:
        st.write(f"### Tavolo {st.session_state.tavolo}")
        if st.button("⬅️ CAMBIA TAVOLO"): st.session_state.tavolo = None; st.rerun()
        
        if not menu_df.empty:
            cat_s = st.radio("Menu:", sorted(menu_df['categoria'].unique()), horizontal=True)
            for _, r in menu_df[menu_df['categoria'] == cat_s].iterrows():
                if st.button(f"➕ {r['prodotto']} | €{r['prezzo']:.2f}", key=f"b_{r['prodotto']}"):
                    st.session_state.carrello.append(r.to_dict())
                    st.toast(f"Aggiunto: {r['prodotto']}")

        if st.session_state.carrello:
            st.divider()
            tot = sum(c['prezzo'] for c in st.session_state.carrello)
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
                st.success("Ordine inviato!"); time.sleep(1); st.rerun()
