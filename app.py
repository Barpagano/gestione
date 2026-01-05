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

# --- CSS PERSONALIZZATO (Ottimizzato per Smartphone) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Bottoni Generali */
    div[data-testid="column"] button {
        width: 100% !important;
        font-weight: bold !important;
        border-radius: 12px !important;
    }

    /* TASTI TAVOLI CLIENTE (Contrasto elevato per mobile) */
    .btn-tavolo > div[data-testid="stButton"] > button {
        background-color: #E0E0E0 !important; /* Grigio chiaro */
        color: #000000 !important;           /* Testo Nero */
        height: 80px !important;
        font-size: 24px !important;
        border: 3px solid #4CAF50 !important; /* Bordo verde per stacco */
        margin-bottom: 10px;
    }
    
    /* Stile Ordini nel Banco */
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; font-style: italic; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; font-size: 16px; }
    
    /* TASTO CHIUDI TAVOLO (BANCO) */
    div.stButton > button[kind="primary"] {
        background-color: #D32F2F !important;
        color: white !important;
        height: 60px !important;
        margin-top: 10px;
    }

    /* Tasto elimina nel carrello cliente */
    .btn-del-cart > div[data-testid="stButton"] > button {
        background-color: transparent !important;
        color: #FF5252 !important;
        border: 1px solid #FF5252 !important;
        font-size: 16px !important;
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

menu_df = carica_menu()
ordini_attuali = carica_ordini()

# --- REFRESH ---
st_autorefresh(interval=5000, key="global_refresh")
if "ultimo_count" not in st.session_state: st.session_state.ultimo_count = len(ordini_attuali)
if len(ordini_attuali) > st.session_state.ultimo_count:
    suona_notifica()
st.session_state.ultimo_count = len(ordini_attuali)

ruolo = st.query_params.get("ruolo", "cliente")

# =========================================================
# BANCONE (RUOLO=BANCO)
# =========================================================
if ruolo == "banco":
    st.title("👨‍🍳 BAR PAGANO - Gestione")
    tab_ordini, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI E CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])

    with tab_ordini:
        if not ordini_attuali: st.info("In attesa...")
        else:
            tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
            cols = st.columns(3)
            for idx, t in enumerate(tavoli_attivi):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.subheader(f"🪑 Tavolo {t}")
                        items = [o for o in ordini_attuali if str(o['tavolo']) == str(t)]
                        tot = sum(float(o['prezzo']) for o in items)
                        for r in items:
                            c1, c2 = st.columns([3, 1])
                            cl = "servito" if r['stato'] == "SI" else "da-servire"
                            c1.markdown(f"<span class='{cl}'>[{r.get('orario','')}] {r['prodotto']}</span>", unsafe_allow_html=True)
                            if r['stato'] == "NO" and c2.button("Ok", key=f"ok_{r['id_univoco']}"):
                                for o in ordini_attuali: 
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()
                        st.divider()
                        st.write(f"**Totale: €{tot:.2f}**")
                        if st.button(f"CHIUDI TAVOLO E PAGA", key=f"chiudi_{t}", type="primary"):
                            salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != str(t)]); st.rerun()

    with tab_vetrina:
        stk = carica_stock()
        cv = st.columns(4)
        for i, (p, q) in enumerate(stk.items()):
            if cv[i % 4].button(f"{p}\n({q})", key=f"vr_{p}", disabled=(q <= 0)):
                stk[p] = max(0, q - 1); salva_stock(stk); st.rerun()

    with tab_stock:
        stk = carica_stock()
        for p, q in stk.items():
            cx, cm, cq, cp, cd = st.columns([3, 1, 1, 1, 1])
            cx.write(f"**{p}**")
            if cm.button("➖", key=f"sm_{p}"): stk[p]=max(0,q-1); salva_stock(stk); st.rerun()
            cq.write(f"**{q}**")
            if cp.button("➕", key=f"sp_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()
            if cd.button("🗑️", key=f"sdel_{p}"): del stk[p]; salva_stock(stk); st.rerun()

    with tab_menu:
        with st.form("add_new"):
            c1, c2 = st.columns(2)
            cat_e = c1.selectbox("Categoria", ["---"] + sorted(list(menu_df['categoria'].unique())) if not menu_df.empty else ["---"])
            cat_n = c2.text_input("Nuova Categoria")
            nome_n, prez_n = st.text_input("Nome"), st.number_input("Prezzo", step=0.1)
            if st.form_submit_button("AGGIUNGI"):
                cat_f = cat_n if cat_n.strip() != "" else cat_e
                if cat_f != "---" and nome_n:
                    pd.concat([menu_df, pd.DataFrame([{"categoria": cat_f, "prodotto": nome_n, "prezzo": prez_n}])], ignore_index=True).to_csv(MENU_FILE, index=False); st.rerun()

# =========================================================
# CLIENTE (STILE TAVOLI CHIARI PER MOBILE)
# =========================================================
else:
    st.title("☕ BAR PAGANO")
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.subheader("Scegli il tuo Tavolo:")
        # Griglia 3x5 per smartphone per rendere i tasti più grandi
        for i in range(0, 15, 3):
            cols = st.columns(3)
            for j in range(3):
                n = i + j + 1
                if n <= 15:
                    st.markdown('<div class="btn-tavolo">', unsafe_allow_html=True)
                    if cols[j].button(f"{n}", key=f"t_{n}"):
                        st.session_state.tavolo = str(n); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.success(f"📍 Tavolo {st.session_state.tavolo}")
        if st.button("⬅️ CAMBIA TAVOLO"): st.session_state.tavolo = None; st.rerun()
        
        if not menu_df.empty:
            cat = st.radio("Menu:", sorted(menu_df['categoria'].unique()), horizontal=True)
            for _, r in menu_df[menu_df['categoria'] == cat].iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
                if c2.button("➕", key=f"add_{r['prodotto']}"):
                    item = r.to_dict(); item['temp_id'] = time.time()
                    st.session_state.carrello.append(item); st.rerun()

        if st.session_state.carrello:
            st.divider()
            st.subheader("🛒 Tuo Ordine:")
            tot = 0
            for i, item in enumerate(st.session_state.carrello):
                tot += item['prezzo']
                col_n, col_e = st.columns([4, 1])
                col_n.write(f"{item['prodotto']} (€{item['prezzo']:.2f})")
                st.markdown('<div class="btn-del-cart">', unsafe_allow_html=True)
                if col_e.button("❌", key=f"rm_{i}_{item['temp_id']}"):
                    st.session_state.carrello.pop(i); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.write(f"### Totale: €{tot:.2f}")
            if st.button(f"🚀 INVIA ORDINE", type="primary", use_container_width=True):
                for item in st.session_state.carrello:
                    ordini_attuali.append({"id_univoco": f"{time.time()}_{item['prodotto']}", "tavolo": st.session_state.tavolo, "prodotto": item['prodotto'], "prezzo": item['prezzo'], "stato": "NO", "orario": get_ora_italiana()})
                salva_ordini(ordini_attuali); st.session_state.carrello = []; st.success("Inviato!"); time.sleep(1); st.rerun()
