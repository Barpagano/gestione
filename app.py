import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAGANOCAFE", page_icon="☕", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton > button { height: 40px !important; font-size: 13px !important; border-radius: 8px !important; }
    .stButton > button[kind="secondary"] { background-color: #d4af37; color: black; }
    .quantita-display { 
        font-size: 18px !important; font-weight: bold !important; color: #00FF00 !important; 
        text-align: center; background-color: #1E2127; padding: 5px; border-radius: 5px; border: 1px solid #333;
    }
    .carrello-box {
        background-color: #1E2127; padding: 15px; border-radius: 10px; border: 2px solid #d4af37; margin-bottom: 20px;
    }
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

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
def salva_ordini(lista): pd.DataFrame(lista, columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)
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
admin_mode = st.query_params.get("admin") == "si"

# Inizializzazione carrello temporaneo nella sessione
if "carrello" not in st.session_state:
    st.session_state.carrello = []

if admin_mode:
    # --- PARTE BANCONE (IDENTICA A PRIMA) ---
    st.title("☕ PAGANOCAFE - Gestione")
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "💰 CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])
    # ... (Il codice del bancone rimane lo stesso per brevità, focalizziamoci sul cliente)
    with tab_ordini:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        cols = st.columns(4)
        for idx, t in enumerate(tavoli):
            with cols[idx % 4]:
                with st.container(border=True):
                    st.write(f"**Tavolo {t}**")
                    items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                    for r in items:
                        c1, c2, c3 = st.columns([0.6, 3, 1])
                        if c1.button("❌", key=f"del_o_{r['id_univoco']}"):
                            salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                        cl = "servito" if r['stato'] == "SI" else "da-servire"
                        c2.markdown(f"<span class='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                        if r['stato'] == "NO" and c3.button("Ok", key=f"ok_o_{r['id_univoco']}"):
                            for o in ordini_attuali: 
                                if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                            salva_ordini(ordini_attuali); st.rerun()
    with tab_cassa:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        for t in tavoli:
            with st.container(border=True):
                items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                totale = sum(float(x['prezzo']) for x in items)
                c1, c2 = st.columns([2, 1])
                c1.write(f"**Tavolo {t}** - €{totale:.2f}")
                if c2.button(f"CHIUDI {t}", key=f"pay_{t}"):
                    salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != t]); st.rerun()
    with tab_vetrina:
        stk = carica_stock()
        cv = st.columns(6)
        for i, (p, q) in enumerate(stk.items()):
            if cv[i % 6].button(f"{p} ({q})", key=f"vr_{p}"):
                stk[p] += 1; salva_stock(stk); st.rerun()
    with tab_stock:
        stk = carica_stock()
        for p, q in stk.items():
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{p}**")
            if c2.button("➖", key=f"m_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
            c3.markdown(f"<div class='quantita-display'>{q}</div>", unsafe_allow_html=True)
            if c4.button("➕", key=f"p_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()
    with tab_menu:
        st.subheader("➕ Aggiungi")
        with st.form("new_prod"):
            c1, c2, c3 = st.columns(3)
            f_cat, f_prod, f_prez = c1.text_input("Categoria"), c2.text_input("Nome"), c3.number_input("Prezzo (€)", step=0.1)
            if st.form_submit_button("AGGIUNGI"):
                nuovo = pd.DataFrame([{"categoria": f_cat.upper(), "prodotto": f_prod, "prezzo": f_prez}])
                pd.concat([menu_df, nuovo]).to_csv(MENU_FILE, index=False); st.rerun()
        st.divider()
        for i, r in menu_df.iterrows():
            mc1, mc2, mc3, mc4 = st.columns([2, 3, 1, 1])
            mc1.write(r['categoria']); mc2.write(r['prodotto']); mc3.write(f"€{r['prezzo']:.2f}")
            if mc4.button("🗑️", key=f"del_prod_{i}"):
                menu_df.drop(i).to_csv(MENU_FILE, index=False); st.rerun()

# ==========================================
# SEZIONE CLIENTE (CON REVISIONE ORDINE)
# ==========================================
else:
    st.markdown("<h1 style='text-align:center;'>🥐 PAGANOCAFE</h1>", unsafe_allow_html=True)
    tavolo_sel = st.selectbox("Seleziona il tuo Tavolo:", ["---"] + [str(i) for i in range(1, 21)])
    
    if tavolo_sel != "---":
        stk = carica_stock()

        # --- 1. CARRELLO DI REVISIONE ---
        if st.session_state.carrello:
            st.markdown(f"<div class='carrello-box'>", unsafe_allow_html=True)
            st.subheader(f"📝 Revisione Ordine - Tavolo {tavolo_sel}")
            
            tot_provvisorio = 0
            for idx, item in enumerate(st.session_state.carrello):
                col_n, col_p, col_del = st.columns([3, 1, 1])
                col_n.write(f"• {item['prodotto']}")
                col_p.write(f"€{item['prezzo']:.2f}")
                if col_del.button("Rimuovi", key=f"rem_temp_{idx}"):
                    st.session_state.carrello.pop(idx)
                    st.rerun()
                tot_provvisorio += item['prezzo']
            
            st.divider()
            st.write(f"**TOTALE DA INVIARE: €{tot_provvisorio:.2f}**")
            
            col_invio, col_svuota = st.columns(2)
            if col_invio.button("✅ INVIA ORDINE AL BANCO", type="primary", use_container_width=True):
                # Trasferiamo gli ordini dal carrello al database
                nuovi_da_salvare = ordini_attuali.copy()
                ora = datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                
                for item in st.session_state.carrello:
                    nuovo_o = {
                        "id_univoco": f"{time.time()}_{item['prodotto']}",
                        "tavolo": tavolo_sel,
                        "prodotto": item['prodotto'],
                        "prezzo": item['prezzo'],
                        "stato": "NO",
                        "orario": ora
                    }
                    nuovi_da_salvare.append(nuovo_o)
                
                salva_ordini(nuovi_da_salvare)
                st.session_state.carrello = [] # Svuota carrello
                st.success("Ordine inviato con successo!")
                time.sleep(1)
                st.rerun()
            
            if col_svuota.button("🗑️ Svuota tutto"):
                st.session_state.carrello = []
                st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

        # --- 2. SELEZIONE PRODOTTI ---
        st.subheader("🍽️ Scegli i prodotti:")
        if not menu_df.empty:
            cat_list = menu_df['categoria'].unique()
            scelta = st.radio("Categoria:", cat_list, horizontal=True)
            
            for _, r in menu_df[menu_df['categoria'] == scelta].iterrows():
                c1, c2 = st.columns([3, 1])
                q = stk.get(r['prodotto'], 999)
                
                c1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
                
                # Verifica se il prodotto è già stato "prenotato" nel carrello per scalare lo stock visivo
                nel_carrello = len([i for i in st.session_state.carrello if i['prodotto'] == r['prodotto']])
                q_effettiva = q - nel_carrello

                if q_effettiva > 0:
                    if c2.button("AGGIUNGI", key=f"add_car_{r['prodotto']}"):
                        # Aggiunge al carrello temporaneo (non ancora al DB)
                        st.session_state.carrello.append({
                            "prodotto": r['prodotto'],
                            "prezzo": r['prezzo']
                        })
                        # Per i prodotti dello stock (vetrina), scaliamo lo stock reale SUBITO 
                        # per evitare che altri clienti ordinino la stessa cosa mentre io sto decidendo
                        if r['prodotto'] in stk:
                            stk[r['prodotto']] -= 1
                            salva_stock(stk)
                        st.rerun()
                else:
                    c2.error("ESAURITO")
        
        # --- 3. ORDINI GIÀ IN PREPARAZIONE (Storico) ---
        miei_in_corso = [o for o in ordini_attuali if str(o['tavolo']) == tavolo_sel]
        if miei_in_corso:
            with st.expander("🕒 Stato dei tuoi ordini precedenti"):
                for mo in miei_in_corso:
                    st.write(f"{'✅' if mo['stato']=='SI' else '⏳'} {mo['prodotto']} - {mo['orario']}")
