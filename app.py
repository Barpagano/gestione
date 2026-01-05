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
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; }
    /* Rosso per tasto elimina */
    .stButton button[key*="del_prod_"] { background-color: #ff4b4b !important; color: white !important; }
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

if admin_mode:
    st.title("☕ PAGANOCAFE - Gestione")
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "💰 CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])

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
        with st.expander("Aggiungi prodotto da monitorare"):
            p_sel = st.selectbox("Scegli dal menu", menu_df['prodotto'].unique()) if not menu_df.empty else None
            if st.button("AGGIUNGI A STOCK") and p_sel:
                stk[p_sel] = 0; salva_stock(stk); st.rerun()
        for p, q in stk.items():
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{p}**")
            if c2.button("➖", key=f"m_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
            c3.markdown(f"<div class='quantita-display'>{q}</div>", unsafe_allow_html=True)
            if c4.button("➕", key=f"p_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()

    with tab_menu:
        st.subheader("➕ Aggiungi al Listino")
        with st.form("new_prod"):
            c1, c2, c3 = st.columns(3)
            f_cat = c1.text_input("Categoria (es: VETRINA)")
            f_prod = c2.text_input("Nome Prodotto")
            f_prez = c3.number_input("Prezzo (€)", step=0.1)
            if st.form_submit_button("AGGIUNGI"):
                nuovo = pd.DataFrame([{"categoria": f_cat.upper(), "prodotto": f_prod, "prezzo": f_prez}])
                pd.concat([menu_df, nuovo]).to_csv(MENU_FILE, index=False); st.rerun()
        
        st.divider()
        st.subheader("🗑️ Modifica / Elimina dal Menu")
        if menu_df.empty: st.info("Menu vuoto.")
        else:
            # Mostriamo il menu riga per riga con tasto elimina funzionante
            for i, r in menu_df.iterrows():
                mc1, mc2, mc3, mc4 = st.columns([2, 3, 1, 1])
                mc1.write(f"*{r['categoria']}*")
                mc2.write(f"**{r['prodotto']}**")
                mc3.write(f"€{r['prezzo']:.2f}")
                # Il trucco è usare un ID unico basato sull'indice della riga
                if mc4.button("🗑️", key=f"del_prod_{i}"):
                    # Rimuoviamo la riga specifica
                    df_aggiornato = menu_df.drop(i)
                    df_aggiornato.to_csv(MENU_FILE, index=False)
                    # Pulizia automatica dallo stock se presente
                    stk = carica_stock()
                    if r['prodotto'] in stk:
                        del stk[r['prodotto']]
                        salva_stock(stk)
                    st.rerun()

# ==========================================
# SEZIONE CLIENTE
# ==========================================
else:
    st.markdown("<h1 style='text-align:center;'>🥐 PAGANOCAFE</h1>", unsafe_allow_html=True)
    tavolo_sel = st.selectbox("Seleziona Tavolo:", ["---"] + [str(i) for i in range(1, 21)])
    if tavolo_sel != "---":
        if menu_df.empty: st.warning("Menu in caricamento...")
        else:
            scelta = st.radio("Scegli:", menu_df['categoria'].unique(), horizontal=True)
            stk = carica_stock()
            for _, r in menu_df[menu_df['categoria'] == scelta].iterrows():
                c1, c2 = st.columns([3, 1])
                q = stk.get(r['prodotto'], 999)
                c1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
                if q > 0:
                    if c2.button("ORDINA", key=f"ord_{r['prodotto']}"):
                        if r['prodotto'] in stk: stk[r['prodotto']] -= 1; salva_stock(stk)
                        nuovo = {"id_univoco": str(time.time()), "tavolo": tavolo_sel, "prodotto": r['prodotto'], "prezzo": r['prezzo'], "stato": "NO", "orario": datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")}
                        ordini_attuali.append(nuovo); salva_ordini(ordini_attuali)
                        st.success("Inviato!"); time.sleep(0.5); st.rerun()
                else: c2.error("FINITO")
