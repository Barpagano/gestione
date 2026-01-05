import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAGANOCAFE", page_icon="☕", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    div[data-testid="column"] button { width: 100% !important; border-radius: 12px !important; }
    .stButton > button { height: 70px; font-weight: bold; background-color: #d4af37; color: black; }
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; }
    .prezzo-cassa { color: #4CAF50; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIONE DATABASE (PULIZIA ERRORI) ---
DB_FILE = "ordini_bar_pagano.csv"
STOCK_FILE = "stock_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def inizializza_file(file, colonne):
    if not os.path.exists(file) or os.stat(file).st_size <= 2:
        pd.DataFrame(columns=colonne).to_csv(file, index=False)

inizializza_file(DB_FILE, ["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"])
inizializza_file(MENU_FILE, ["categoria", "prodotto", "prezzo"])
inizializza_file(STOCK_FILE, ["prodotto", "quantita"])

def carica_menu(): 
    try: return pd.read_csv(MENU_FILE)
    except: return pd.DataFrame(columns=["categoria", "prodotto", "prezzo"])

def carica_ordini(): 
    try:
        df = pd.read_csv(DB_FILE)
        return df.to_dict('records') if not df.empty else []
    except: return []

def salva_ordini(lista): 
    pd.DataFrame(lista, columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)

def carica_stock(): 
    try:
        df = pd.read_csv(STOCK_FILE)
        return df.set_index('prodotto')['quantita'].to_dict() if not df.empty else {}
    except: return {}

def salva_stock(d): 
    pd.DataFrame(list(d.items()), columns=['prodotto', 'quantita']).to_csv(STOCK_FILE, index=False)

# --- LOGICA ---
st_autorefresh(interval=5000, key="global_refresh")
menu_df = carica_menu()
ordini_attuali = carica_ordini()
admin_mode = st.query_params.get("admin") == "si"

# ==========================================
# SEZIONE BANCONE (ADMIN)
# ==========================================
if admin_mode:
    st.title("☕ PAGANOCAFE - Console Unificata")
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs([
        "📋 ORDINI", "💰 CASSA", "⚡ VETRINA (+1)", "📦 STOCK", "⚙️ MENU"
    ])

    with tab_ordini:
        if not ordini_attuali: st.info("Nessun ordine presente.")
        else:
            tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
            cols = st.columns(3)
            for idx, t in enumerate(tavoli):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.subheader(f"Tavolo {t}")
                        items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                        for r in items:
                            c1, c2, c3 = st.columns([1, 4, 2])
                            if c1.button("❌", key=f"del_{r['id_univoco']}"):
                                salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                            cl = "servito" if r['stato'] == "SI" else "da-servire"
                            c2.markdown(f"<span class='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                            if r['stato'] == "NO" and c3.button("Ok", key=f"ok_{r['id_univoco']}"):
                                for o in ordini_attuali: 
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()

    with tab_cassa:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        for t in tavoli:
            with st.container(border=True):
                items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                totale = sum(float(x['prezzo']) for x in items)
                st.write(f"### Tavolo {t} - Totale: €{totale:.2f}")
                if st.button(f"CHIUDI E LIBERA {t}", key=f"pay_{t}"):
                    salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != t]); st.rerun()

    with tab_vetrina:
        stk = carica_stock()
        st.write("Rifornimento veloce (+1):")
        cv = st.columns(4)
        for i, (p, q) in enumerate(stk.items()):
            if cv[i % 4].button(f"{p}\n({q})", key=f"vr_{p}"):
                stk[p] += 1; salva_stock(stk); st.rerun()

    with tab_stock:
        stk = carica_stock()
        with st.expander("Aggiungi prodotto da monitorare"):
            p_sel = st.selectbox("Scegli dal menu", menu_df['prodotto'].unique()) if not menu_df.empty else None
            if st.button("AGGIUNGI") and p_sel:
                stk[p_sel] = 0; salva_stock(stk); st.rerun()
        for p, q in stk.items():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{p}** (Disp: {q})")
            if c2.button("➖", key=f"m_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
            if c3.button("➕", key=f"p_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()

    with tab_menu:
        with st.form("new"):
            c1, c2, c3 = st.columns(3)
            cat = c1.text_input("Categoria")
            prod = c2.text_input("Prodotto")
            prez = c3.number_input("Prezzo", step=0.1)
            if st.form_submit_button("SALVA NEL MENU"):
                nuovo = pd.DataFrame([{"categoria": cat, "prodotto": prod, "prezzo": prez}])
                pd.concat([menu_df, nuovo]).to_csv(MENU_FILE, index=False); st.rerun()

# ==========================================
# SEZIONE CLIENTE
# ==========================================
else:
    st.markdown("<h1 style='text-align:center;'>🥐 PAGANOCAFE</h1>", unsafe_allow_html=True)
    tavolo_sel = st.selectbox("Seleziona Tavolo:", ["---"] + [str(i) for i in range(1, 21)])
    
    if tavolo_sel != "---":
        if menu_df.empty: st.warning("Menu in fase di aggiornamento...")
        else:
            cat_list = menu_df['categoria'].unique()
            scelta = st.radio("Cosa desideri?", cat_list, horizontal=True)
            stk = carica_stock()
            
            for _, r in menu_df[menu_df['categoria'] == scelta].iterrows():
                c1, c2 = st.columns([3, 1])
                q = stk.get(r['prodotto'], 999)
                c1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
                if q > 0:
                    if c2.button("ORDINA", key=f"ord_{r['prodotto']}"):
                        if r['prodotto'] in stk:
                            stk[r['prodotto']] -= 1
                            salva_stock(stk)
                        nuovo = {
                            "id_univoco": str(time.time()), "tavolo": tavolo_sel, 
                            "prodotto": r['prodotto'], "prezzo": r['prezzo'], 
                            "stato": "NO", "orario": datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                        }
                        ordini_attuali.append(nuovo)
                        salva_ordini(ordini_attuali)
                        st.success("Inviato!"); time.sleep(1); st.rerun()
                else: c2.error("FINITO")
