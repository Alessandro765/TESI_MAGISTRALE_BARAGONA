import streamlit as st
from backend_analysis import run_full_analysis_pipeline, validate_user_input
import os
import json
import urllib.parse

# --- CARICAMENTO DEI DATI JSON PER LA VISUALIZZAZIONE ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.join(script_dir, "JSON")
    json_files = ["conoscenze.json", "skills.json", "attivita_generalizzate.json", "attitudini.json"]
    data = {file.split(".")[0]: json.load(open(os.path.join(json_folder, file), encoding="utf-8")) for file in json_files}
except Exception as e:
    st.error(f"Errore critico nel caricamento dei file JSON: {e}")
    data = {}

# --- CONFIGURAZIONE DELLA PAGINA E STILE ---
st.set_page_config(
    page_title="Career Compass AI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato
CUSTOM_CSS = """
<style>
    /* Stile generale */
    .stApp { background-color: #f8f9fa; }

    /* Bottoni */
    .stButton > button { border-radius: 0.5rem; border: 2px solid #0066cc; color: #0066cc; background-color: transparent; transition: all 0.2s ease-in-out; }
    .stButton > button:hover { border-color: #004C99; color: white; background-color: #004C99; }
    .stButton > button:focus { box-shadow: 0 0 0 0.2rem rgba(0, 102, 204, 0.5); }

    /* Chat bubbles */
    .chat-bubble { padding: 10px 15px; border-radius: 20px; margin-top: 10px; margin-bottom: 10px; max-width: 80%; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .user-bubble { background-color: #e7f0fa; align-self: flex-end; margin-left: auto; border-bottom-right-radius: 5px; }
    .ai-bubble { background-color: #f1f3f5; align-self: flex-start; border-bottom-left-radius: 5px; }

    /* Footer, Box informativo */
    .footer { margin-top: 50px; background-color: #e9ecef; color: #6c757d; text-align: center; padding: 15px; font-size: 1.4em; }
    .intro-box { background-color: #e7f0fa; border: 1px solid #bce0ff; border-radius: 0.5rem; padding: 15px 20px; margin-bottom: 25px; font-size: 1.1em; color: #343a40; }

    /* Stili specifici per la Sidebar */
    [data-testid="stSidebar"] h1 { font-size: 1.75em !important; color: #343a40 !important; font-weight: 600; }
    [data-testid="stSidebar"] .st-emotion-cache-1b0udgb { font-size: 0.95em !important; color: #6c757d !important; }
    [data-testid="stSidebar"] .st-emotion-cache-12w0qpk summary p { font-weight: 600 !important; font-size: 1.1em !important; color: #004C99 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] li { font-size: 1.0em !important; color: #495057 !important; }
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] .st-emotion-cache-1q8dd3e { font-size: 1.2em !important; color: #343a40 !important; font-weight: 600; }

    /* Stile per il pulsante arancione di reset */
    [data-testid="stHorizontalBlock"] > div:nth-child(3) .stButton > button {
        background-color: #ffc107;
        border-color: #ffc107;
        color: #212529;
    }
    [data-testid="stHorizontalBlock"] > div:nth-child(3) .stButton > button:hover {
        background-color: #e0a800;
        border-color: #d39e00;
        color: white;
    }

</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- FUNZIONE DI ANALISI CON CACHING ---
@st.cache_data(show_spinner=False)
def run_analysis(full_user_text, force_fallback=False):
    """
    Funzione wrapper che chiama la pipeline di backend e gestisce la cache.
    Ora accetta l'argomento force_fallback per passarlo al backend.
    """
    return run_full_analysis_pipeline(user_input_text=full_user_text, force_fallback=force_fallback)

# --- INIZIALIZZAZIONE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "ai", "content": "Ciao! Sono Career Compass AI. Per iniziare, descrivimi le tue passioni, le tue esperienze e cosa cerchi in un lavoro. Più dettagli mi fornisci, più accurata sarà la mia analisi."}]
if "full_text" not in st.session_state:
    st.session_state.full_text = ""
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "analysis_triggered" not in st.session_state:
    st.session_state.analysis_triggered = False

# --- LAYOUT SIDEBAR ---
with st.sidebar:
    st.title("Report di Analisi")
    # checkbox di debug in cima alla sidebar
    force_fallback_test = st.checkbox("🧪 Forzare test di fallback")
    st.caption("_Dettagli del tuo profilo elaborati dalla nostra IA._")
    st.divider()

    if not st.session_state.analysis_done:
        st.info("I risultati appariranno qui dopo l'analisi.")
    else:
        results = st.session_state.analysis_results
        
        if "error" in results and "feedback" not in results:
            st.error(f"**Errore durante l'analisi:**\n{results['error']}")
        elif results:
            with st.expander("🎯 **Le Tue Professioni Consigliate**", expanded=True):
                for prof in results.get("audited_ranked_professions", []):
                    desc = prof['desc']
                    code = prof['code']
                    # Creiamo una query di ricerca sicura
                    query = urllib.parse.quote_plus(f"professione ISTAT {code} {desc}")
                    link = f"https://www.google.com/search?q={query}"
                    # Creiamo il subheader con il link cliccabile
                    st.subheader(f"[{desc} ({code})]({link})")
                    score = prof.get('relevance_score', 0)
                    st.progress(score / 10, text=f"Pertinenza: {score}/10")
                    st.markdown(f"**Motivazione:** *{prof.get('reason', 'N/A')}*")
                    audit = prof.get('fairness_audit', {})
                    summary = audit.get('potential_bias_summary', 'N/A')
                    if "Nessun bias" in summary:
                        st.success(f"✅ **Fairness Audit:** {summary}")
                    else:
                        st.warning(f"⚠️ **Fairness Audit:** {summary}")
                        with st.container(border=True):
                            st.markdown(f"**Sottogruppi potenzialmente interessati:** {', '.join(audit.get('affected_subgroups', []))}")
                            st.caption(f"**Ragionamento:** {audit.get('reasoning', '')}")
                    st.divider()
            with st.expander("🔗 **Percorsi Correlati**"):
                for prof in results.get("affine_professions", []):
                    desc = prof['desc']
                    code = prof['code']
                    query = urllib.parse.quote_plus(f"professione ISTAT {code} {desc}")
                    link = f"https://www.google.com/search?q={query}"
                    # Creiamo l'elemento della lista con il link cliccabile
                    st.markdown(f"- **[{desc} ({code})]({link})**")
            with st.expander("🧠 **Il Ragionamento dell'IA**"):
                reasoning = results.get("reasoning_data", {})
                for key, title in [("best_conoscenze", "Conoscenze"), ("best_skills", "Skills"), ("best_attitudini", "Attitudini"), ("best_attivita_generalizzate", "Attività")]:
                    st.markdown(f"**{title} Rilevate:**")
                    if reasoning.get(key):
                        for item in reasoning.get(key, []):
                            dict_key = key.replace('best_', '')
                            if dict_key == 'attivita': dict_key = 'attivita_generalizzate'
                            st.markdown(f"- **{data.get(dict_key, {}).get(item['code'], 'N/A')}**: *{item['reason']}*")
                keyword = reasoning.get('explicit_job_keyword', '')
                if keyword: st.markdown(f"**Aspirazione Esplicita:** *{keyword}*")
            with st.expander("⚙️ **Dati di Classificazione**"):
                istat_cats = results.get('istat_categories', [])
                st.markdown(f"**Macro-categorie ISTAT identificate:** {', '.join(istat_cats)}")
                usage = results.get('usage_stats', {})
                if usage: st.caption(f"Token usati: {usage.get('total_tokens', 0)} | Costo stimato: ${usage.get('estimated_cost_usd', 0):.6f}")

# --- LAYOUT PRINCIPALE (CHAT) ---
st.title("🧭 Career Compass AI")
intro_text = """
Usa la chat qui sotto per descriverti. Premi <b>'Aggiungi dettaglio'</b> per inserire più informazioni.
<br>Quando sei pronto, clicca su <b>'Analizza il mio profilo'</b> per ricevere il tuo report personalizzato nella barra laterale.
<br>Usa <b>'Termina analisi'</b> in qualsiasi momento per ricominciare da capo.
<br><br>💡 <i>Consiglio:</i> Fornisci dettagli pertinenti al lavoro che intendi approfondire per ottenere un'analisi realmente accurata!
"""
st.markdown(f'<div class="intro-box">{intro_text}</div>', unsafe_allow_html=True)

# Visualizzazione cronologia chat
for message in st.session_state.messages:
    role = message["role"]
    bubble_class = "user-bubble" if role == "user" else "ai-bubble"
    st.markdown(f'<div class="chat-bubble {bubble_class}">{message["content"]}</div>', unsafe_allow_html=True)

st.divider()

if st.session_state.get("analysis_triggered", False):
    with st.spinner("Sto analizzando il tuo profilo... Potrebbe volerci qualche istante..."):
        # Passa il valore del checkbox alla funzione di analisi
        results = run_analysis(st.session_state.full_text, force_fallback=force_fallback_test)
    
    st.session_state.analysis_results = results
    st.session_state.analysis_done = True
    st.session_state.analysis_triggered = False 

    if "error" not in results:
        st.session_state.messages.append({"role": "ai", "content": "Analisi completata! Trovi tutti i dettagli del tuo report personalizzato nella barra laterale a sinistra."})
    st.rerun()

# --- CALLBACKS E WIDGETS DI INPUT ---
def add_detail_callback():
    user_prompt = st.session_state.user_input_area
    if user_prompt:
        st.session_state.full_text += user_prompt + "\n"
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        st.session_state.messages.append({"role": "ai", "content": "Perfetto. C'è altro che vorresti aggiungere?"})
        st.session_state.user_input_area = ""

def analyze_profile_callback():
    user_prompt = st.session_state.user_input_area
    if user_prompt:
        st.session_state.full_text += user_prompt + "\n"
        st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    if not st.session_state.full_text.strip() or st.session_state.full_text.isspace():
        st.warning("Per favore, descriviti prima di chiedere l'analisi.")
        return

    # Esegui la validazione PRIMA di fare qualsiasi altra cosa
    with st.spinner("Verifico la completezza del tuo profilo..."):
        validation_result = validate_user_input(st.session_state.full_text)

    if validation_result and validation_result.get("is_sufficient"):
        # Se la validazione ha successo, aggiungi i messaggi e imposta il trigger
        st.session_state.messages.append({"role": "user", "content": "No, grazie. Sono pronto."})
        st.session_state.messages.append({"role": "ai", "content": "Ok, iniziamo l'analisi!"})
        st.session_state.analysis_triggered = True
    else:
        # Se la validazione fallisce, mostra il feedback
        feedback = validation_result.get("feedback", "Si è verificato un errore durante la validazione.")
        st.session_state.messages.append({"role": "ai", "content": feedback})
    
    st.session_state.user_input_area = ""

# Etichetta personalizzata, visibile e stilizzata
st.markdown("<h5>Scrivi qui per descriverti...</h5>", unsafe_allow_html=True)

def reset_analysis_callback():
    """Resetta completamente lo stato della sessione per una nuova analisi."""
    st.session_state.messages = [{"role": "ai", "content": "Ciao! Sono Career Compass AI. Per iniziare, descrivimi le tue passioni, le tue esperienze e cosa cerchi in un lavoro. Più dettagli mi fornisci, più accurata sarà la mia analisi."}]
    st.session_state.full_text = ""
    st.session_state.analysis_results = None
    st.session_state.analysis_done = False
    st.session_state.analysis_triggered = False
    st.session_state.user_input_area = ""

# Problemi con alcuni parametri di deafult in text_area, quindi usiamo key e gestiamo lo stato manualmente
user_prompt_input = st.text_area(
    label="Input utente", # L'etichetta ora è nascosta, ma serve per il funzionamento interno
    key="user_input_area", 
    height=150,
    label_visibility="collapsed" # nasconde l'etichetta
)

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    st.button("Aggiungi dettaglio", on_click=add_detail_callback,  disabled=not st.session_state.get("user_input_area", "").strip(), use_container_width=True)
with col2:
    st.button("Analizza il mio profilo", type="primary", use_container_width=True, on_click=analyze_profile_callback)
with col3:
    st.button("Termina analisi", on_click=reset_analysis_callback, use_container_width=True)

# --- FOOTER ---
footer = """
<div class="footer">
    <p>
    <b>Disclaimer:</b> Career Compass AI è uno strumento di supporto e i suoi suggerimenti non devono essere considerati come una consulenza professionale definitiva. 
    <br> <!-- <-- TAG AGGIUNTO QUI PER ANDARE A CAPO -->
    I risultati sono generati da un'IA e potrebbero contenere imprecisioni.
    </p>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)