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
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; font-style: italic; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; font-size: 16px; }
    .prezzo-cassa { color: #4CAF50; font-weight: bold; }
    /* Stile per il tasto chiusura tavolo */
    .stButton > button[kind="primary"] {
        background-color: #D32F2F !important;
        margin-top: 10px;
    }
    /* Stile per i tavoli del cliente */
    .btn-tavolo > div[data-testid="stButton"] > button {
        background-color: #1E1E1E !important;
        height: 70px !important;
        font-size: 20px !important;
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

# Caricamento dati
menu_df = carica_menu()
ordini_attuali = carica_ordini()

# --- LOGICA DI REFRESH ---
st_autorefresh(interval=5000, key="global_refresh")

# Controllo se è arrivato un nuovo ordine per la notifica
if "ultimo_count" not in st.session_state: st.session_state.ultimo_count = len(ordini_attuali)
if len(ordini_attuali) > st.session_state.ultimo_count:
    suona_notifica()
st.session_state.ultimo_count = len(ordini_attuali)

# --- DISTINZIONE RUOLI ---
ruolo = st.query_params.get("ruolo", "cliente")

# =========================================================
# SCHERMATA GESTIONE (BANCO)
# =========================================================
if ruolo == "banco":
    st.title("👨‍🍳 BAR PAGANO - Gestione Unificata")

    tab_ordini, tab_vetrina, tab_stock, tab_menu = st.tabs([
        "📋 ORDINI E CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"
    ])

    # --- TAB 1: ORDINI E CHIUDI TAVOLO ---
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
                        
                        totale_tavolo = 0
                        for r in items:
                            totale_tavolo += float(r['prezzo'])
                            c1, c2 = st.columns([3, 1])
                            
                            cl = "servito" if r['stato'] == "SI" else "da-servire"
                            c1.markdown(f"<span class='{cl}'>[{r.get('orario','')}] {r['prodotto']}</span>", unsafe_allow_html=True)
                            
                            if r['stato'] == "NO" and c2.button("Ok", key=f"ok_{r['id_univoco']}"):
                                for o in ordini_attuali: 
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()
                        
                        st.divider()
                        st.write(f"**Totale: €{totale_tavolo:.2f}**")
                        
                        if st.button(f"CHIUDI TAVOLO E PAGA", key=f"chiudi_{t}", type="primary"):
                            nuovi_ordini = [o for o in ordini_attuali if str(o['tavolo']) != str(t)]
                            salva_ordini(nuovi_ordini)
                            st.success(f"Tavolo {t} pagato!")
                            time.sleep(1)
                            st.rerun()

    # --- TAB 2: VETRINA ---
    with tab_vetrina:
        stk = carica_stock()
        cv = st.columns(4)
        for i, (p, q) in enumerate(stk.items()):
            if cv[i % 4].button(f"{p}\n({q})", key=f"vr_{p}", disabled=(q <= 0)):
                stk[p] = max(0, q - 1); salva_stock(stk); st.rerun()

    # --- TAB 3: STOCK ---
    with tab_stock:
        stk = carica_stock()
        with st.expander("➕ Monitora nuovo prodotto"):
            if not menu_df.empty:
                c1, c2 = st.columns(2)
                cat_stk = c1.selectbox("Categoria", sorted(menu_df['categoria'].unique()))
                nuovo_s = c2.selectbox("Prodotto", menu_df[menu_df['categoria'] == cat_stk]['prodotto'].unique())
                if st.button("AGGIUNGI"):
                    if nuovo_s not in stk: stk[nuovo_s] = 0; salva_stock(stk); st.rerun()
        st.divider()
        for p, q in stk.items():
            cx, cm, cq, cp, cd = st.columns([3, 1, 1, 1, 1])
            cx.write(f"**{p}**")
            if cm.button("➖", key=f"sm_{p}"): stk[p] = max(0, q-1); salva_stock(stk); st.rerun()
            cq.write(f"**{q}**")
            if cp.button("➕", key=f"sp_{p}"): stk[p] = q+1; salva_stock(stk); st.rerun()
            if cd.button("🗑️", key=f"sdel_{p}"): del stk[p]; salva_stock(stk); st.rerun()

    # --- TAB 4: MENU ---
    with tab_menu:
        st.subheader("⚙️ Listino Prezzi")
        with st.form("add_new"):
            c1, c2 = st.columns(2)
            cat_e = c1.selectbox("Categoria", ["---"] + sorted(list(menu_df['categoria'].unique())) if not menu_df.empty else ["---"])
            cat_n = c2.text_input("Nuova Categoria")
            nome_n = st.text_input("Nome")
            prez_n = st.number_input("Prezzo", min_value=0.0, step=0.1)
            if st.form_submit_button("AGGIUNGI"):
                cat_f = cat_n if cat_n.strip() != "" else cat_e
                if cat_f != "---" and nome_n:
                    nuovo = pd.DataFrame([{"categoria": cat_f, "prodotto": nome_n, "prezzo": prez_n}])
                    pd.concat([menu_df, nuovo], ignore_index=True).to_csv(MENU_FILE, index=False); st.rerun()

# =========================================================
# SCHERMATA CLIENTE (ORDINAZIONI)
# =========================================================
else:
    st.title("☕ BENVENUTI AL BAR PAGANO")
    
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.subheader("Seleziona il tuo tavolo:")
        for i in range(0, 15, 5):
            cols = st.columns(5)
            for j in range(5):
                n = i + j + 1
                st.markdown('<div class="btn-tavolo">', unsafe_allow_html=True)
                if cols[j].button(f"Tavolo {n}", key=f"t_{n}"):
                    st.session_state.tavolo = str(n); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.success(f"📍 Ordinando per il **Tavolo {st.session_state.tavolo}**")
        if st.button("⬅️ CAMBIA TAVOLO"): 
            st.session_state.tavolo = None
            st.rerun()
        
        if menu_df.empty:
            st.warning("Menu in fase di aggiornamento...")
        else:
            categorie = sorted(menu_df['categoria'].unique())
            scelta = st.radio("Scegli Categoria:", categorie, horizontal=True)
            
            prodotti_cat = menu_df[menu_df['categoria'] == scelta]
            for _, row in prodotti_cat.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['prodotto']}** - €{row['prezzo']:.2f}")
                if c2.button("Aggiungi", key=f"add_{row['prodotto']}"):
                    st.session_state.carrello.append(row.to_dict())
                    st.toast(f"Aggiunto: {row['prodotto']}")

        if st.session_state.carrello:
            st.divider()
            st.subheader("🛒 Il tuo ordine")
            tot = sum(c['prezzo'] for c in st.session_state.carrello)
            for c in st.session_state.carrello:
                st.write(f"- {c['prodotto']} (€{c['prezzo']:.2f})")
            
            if st.button(f"🚀 INVIA ORDINE (€{tot:.2f})", type="primary", use_container_width=True):
                ora = get_ora_italiana()
                for item in st.session_state.carrello:
                    ordini_attuali.append({
                        "id_univoco": f"{time.time()}_{item['prodotto']}",
                        "tavolo": st.session_state.tavolo,
                        "prodotto": item['prodotto'],
                        "prezzo": item['prezzo'],
                        "stato": "NO",
                        "orario": ora
                    })
                salva_ordini(ordini_attuali)
                st.session_state.carrello = []
                st.success("Ordine inviato con successo!")
                time.sleep(1)
                st.rerun()
