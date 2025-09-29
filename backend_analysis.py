"""
Modulo di Backend per Career Compass AI.
Questo file contiene tutta la logica di analisi del profilo utente.
Viene importato e utilizzato dal front-end Streamlit (app_streamlit.py).
Non contiene codice di esecuzione diretta.
"""

import json
import requests
from dotenv import load_dotenv
import os
import re
from collections import defaultdict
import time
import streamlit as st
from profession_data import PROFESSIONI_ISTAT_3_DIGIT
import concurrent.futures
from types import SimpleNamespace
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable # Importiamo il decoratore

# Modello AI da utilizzare per tutte le chiamate
model_type = "gpt-4o-mini"

# Carica TUTTE le variabili d'ambiente
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")

# --- SETUP GLOBALE DEL MODULO ---

try:
    # Quando l'app è su Streamlit Cloud, legge i secrets da qui
    openai_api_key = st.secrets["OPENAI_API_KEY"]
except:
    # Quando esegui l'app in locale, legge i secrets dal file .env
    from dotenv import load_dotenv
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

# Creiamo un client LLM che verrà tracciato automaticamente da LangSmith
# Lo configuriamo una sola volta e lo riutilizziamo in tutte le funzioni
llm_client = ChatOpenAI(
    model=model_type,
    api_key=openai_api_key,
    temperature=0.1 # Puoi impostare una temperatura di default qui
)

# Ottimizzazione: Carica i file JSON una sola volta all'avvio del modulo, invece di ricaricarli ad ogni chiamata.
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.join(script_dir, "JSON")
    json_files = ["conoscenze.json", "skills.json", "attivita_generalizzate.json", "attitudini.json"]
    DATA_JSON = {file.split(".")[0]: json.load(open(os.path.join(json_folder, file), encoding="utf-8")) for file in json_files}
except Exception as e:
    print(f"ERRORE CRITICO: Impossibile caricare i file JSON. L'applicazione non funzionerà. Dettagli: {e}")
    DATA_JSON = None

# --- DEFINIZIONE DELLE FUNZIONI DI ANALISI ---
@traceable
def find_professions_locally_as_fallback(user_text, selected_categories_with_reasons):
    """
    Funzione di FALLBACK. Se le API INAPP falliscono, usa l'LLM per confrontare
    il profilo utente con il dizionario locale PROFESSIONI_ISTAT_3_DIGIT.
    """
    print("ATTENZIONE: Esecuzione della ricerca di professioni in modalità fallback locale.")
    
    # Prepara una stringa con le competenze chiave dell'utente per dare più contesto all'LLM
    reasoning_summary = []
    for key, items in selected_categories_with_reasons.items():
        if isinstance(items, list):
            for item in items:
                # Usiamo le descrizioni testuali delle competenze, non solo i codici
                dict_key = key.replace('best_', '')
                if dict_key == 'attivita': dict_key = 'attivita_generalizzate' # Correzione nome chiave
                
                competenza_desc = DATA_JSON.get(dict_key, {}).get(item.get('code'), 'N/A')
                reasoning_summary.append(f"- {competenza_desc}: {item.get('reason')}")
    
    context_skills = "\n".join(reasoning_summary)

    # Prepara la lista di professioni locali per il prompt
    local_professions_list = "\n".join([f"{code}: {details['nome']}" for code, details in PROFESSIONI_ISTAT_3_DIGIT.items()])

    prompt = f"""
    Il sistema di ricerca primario non è disponibile. Devi eseguire un'analisi di emergenza.
    
    **Profilo Utente:**
    "{user_text}"

    **Competenze Chiave e Aspirazioni Rilevate:**
    {context_skills}

    **Compito:**
    Basandoti ESCLUSIVAMENTE sul profilo e sulle competenze chiave, analizza la seguente lista di professioni e identifica le 15 più pertinenti.

    **Lista Professioni Disponibili (da cui scegliere):**
    {local_professions_list}

    **Regole Etiche:**
    - Ignora genere, età o background. Concentrati sul potenziale e sulle competenze.
    - Evita stereotipi professionali.

    **Formato di Risposta JSON Richiesto:**
    Devi restituire una lista di oggetti JSON. Per ogni professione, includi i campi 'code', 'desc', 'importanza' e 'complessita'.
    Poiché 'importanza' e 'complessita' non sono presenti nei dati locali, assegna a entrambi un valore fisso di 50.
    ```json
    [
        {{"code": "X.X.X", "desc": "Nome Professione...", "importanza": 50, "complessita": 50}},
        {{"code": "Y.Y.Y", "desc": "Nome Professione...", "importanza": 50, "complessita": 50}}
    ]
    ```
    Restituisci solo il JSON, senza commenti o testo aggiuntivo.
    """
    try:
        response = llm_client.invoke(
            [
                SystemMessage(content="Sei un analista di carriere esperto in grado di abbinare profili utente a descrizioni di lavoro, operando in modalità di emergenza."),
                HumanMessage(content=prompt)
            ],
            model=model_type,
            temperature=0.2
        )
        raw_content = response.content.strip()
        cleaned_json = re.sub(r"```json|```", "", raw_content).strip()
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"Errore critico durante la funzione di fallback locale: {e}")
        return []

def get_affine_professions_locally(profession_codes):
    """
    Funzione di FALLBACK per trovare professioni affini localmente.
    Una professione è affine se condivide le prime due parti del codice (es. 2.2.x).
    """
    print("ATTENZIONE: Esecuzione della ricerca di professioni affini in modalità fallback locale.")
    affine_professions = []
    seen_codes = set()
    for code in profession_codes:
        if not code: continue
        prefix = ".".join(code.split('.')[:2]) # Es: da "2.2.1" ottiene "2.2"
        for local_code, details in PROFESSIONI_ISTAT_3_DIGIT.items():
            if local_code.startswith(prefix) and local_code not in profession_codes and local_code not in seen_codes:
                affine_professions.append({"code": local_code, "desc": details.get("nome", "")})
                seen_codes.add(local_code)
    return affine_professions[:10] # Limita il numero di risultati

def select_best_categories(user_text, json_data):
    
    """
    Utilizza l'LLM per tradurre il testo dell'utente in un profilo strutturato.
    Identifica le competenze più pertinenti da un vocabolario controllato (JSON)
    e fornisce una motivazione per ogni scelta, garantendo la spiegabilità.
    """
    
    conoscenze_dict = json_data["conoscenze"]
    skills_dict = json_data["skills"]
    attivita_generalizzate_dict = json_data["attivita_generalizzate"]
    attitudini_dict = json_data["attitudini"]

    prompt = f"""
    L'utente ha raccontato se stesso come: "{user_text}".

    **Compito:** Analizza il profilo dell'utente per identificare le sue competenze e aspirazioni lavorative.
    1.  Identifica le **2 categorie più pertinenti** per ciascuna delle seguenti aree: conoscenze (B), skills (C), attitudini (D), e attività (G).
    2.  Per ogni categoria scelta, fornisci una **breve motivazione** basata ESCLUSIVAMENTE sul testo dell'utente.
    3.  Se l'utente esprime chiaramente una preferenza per un settore, estrai la **keyword principale**.

    **REGOLE FONDAMENTALI DI ETICA E RESPONSABILITÀ:**
    - **Valuta il profilo basandoti esclusivamente sulle competenze, esperienze e aspirazioni menzionate.**
    - **IGNORA ogni possibile correlazione con genere (nomi), età, o background socio-culturale.**
    - **EVITA STEREOTIPI PROFESSIONALI.** Non associare determinate competenze a generi o età specifiche.
    - **Le motivazioni devono citare o parafrasare parti del testo dell'utente.**

    **Categorie disponibili (scegli SOLO da queste):**
    **Conoscenze (B):** {json.dumps(conoscenze_dict, indent=2, ensure_ascii=False)}
    **Skills (C):** {json.dumps(skills_dict, indent=2, ensure_ascii=False)}
    **Attitudini (D):** {json.dumps(attitudini_dict, indent=2, ensure_ascii=False)}
    **Attività (G):** {json.dumps(attivita_generalizzate_dict, indent=2, ensure_ascii=False)}

    **Formato di risposta JSON richiesto:**
    ```json
    {{
        "best_conoscenze": [
            {{"code": "Bxx", "reason": "Motivazione basata sul testo..."}},
            {{"code": "Bxx", "reason": "Motivazione basata sul testo..."}}
        ],
        "best_skills": [
            {{"code": "Cxx", "reason": "Motivazione basata sul testo..."}},
            {{"code": "Cxx", "reason": "Motivazione basata sul testo..."}}
        ],
        "best_attitudini": [
            {{"code": "Dxx", "reason": "Motivazione basata sul testo..."}},
            {{"code": "Dxx", "reason": "Motivazione basata sul testo..."}}
        ],
        "best_attivita": [
            {{"code": "Gxx", "reason": "Motivazione basata sul testo..."}},
            {{"code": "Gxx", "reason": "Motivazione basata sul testo..."}}
        ],
        "explicit_job_keyword": "keyword o ''"
    }}
    ```
    """
    try:
        # Usiamo il client LangChain con il suo metodo .invoke()
        response = llm_client.invoke([
            SystemMessage(content="Sei un assistente AI etico e responsabile, specializzato nell'analisi di profili professionali in modo imparziale."),
            HumanMessage(content=prompt)
            ],
            model=model_type,
            temperature=0.2
        )
        
        # Estraiamo il testo direttamente da .content
        raw_content = response.content.strip()
        cleaned_json = re.sub(r"```json|```", "", raw_content).strip()
        result = json.loads(cleaned_json)

        # Il controllo di validità rimane identico
        for key, valid_dict in [("best_conoscenze", conoscenze_dict), 
                                ("best_skills", skills_dict), 
                                ("best_attitudini", attitudini_dict),
                                ("best_attivita", attivita_generalizzate_dict)]:
            if key in result:
                result[key] = [item for item in result[key] if isinstance(item, dict) and item.get("code") in valid_dict]
        
        # Estraiamo le info sui token e le rendiamo compatibili
        usage_info = response.response_metadata.get('token_usage', {})
        usage = SimpleNamespace(
            prompt_tokens=usage_info.get('prompt_tokens', 0),
            completion_tokens=usage_info.get('completion_tokens', 0)
        )
        return result, usage
    except Exception as e:
        print(f"Errore in select_best_categories: {e}")
        return None, None

def get_istat_categories():
    
    """
    Interroga l'API di INAPP per recuperare l'elenco ufficiale delle macro-categorie professionali ISTAT.
    Formatta la risposta JSON in un dizionario pulito e facilmente utilizzabile.
    Fornisce i dati necessari alla successiva fase di classificazione del profilo utente.
    """
    
    url = "https://api.inapp.org/professioni/search.php?idFamiglia=1&idIndice=1&flag=27"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            categories = data[0]
            istat_categories = {}
            for key, value in categories.items():
                if key.isdigit():
                    istat_categories[key] = {
                        "desc_livello": value.get("desc_livello", "Sconosciuto"),
                        "longdesc_livello": value.get("longdesc_livello", "Descrizione non disponibile")
                    }
            return istat_categories
    except requests.exceptions.RequestException as e:
        print(f"Errore nella richiesta API delle categorie ISTAT: {e}")
        return {}

@traceable
def classify_user_category(user_text):
    
    """
    Utilizza l'LLM per classificare il profilo utente nelle due macro-categorie ISTAT più adatte.
    Il risultato agisce da filtro strategico per le fasi di ricerca successive.
    Garantisce che le professioni suggerite siano tematicamente pertinenti al profilo.
    """
    
    istat_categories = get_istat_categories()
    if not istat_categories: return [], None

    formatted_categories = "\n".join([f"{key} - {value['desc_livello']}" for key, value in istat_categories.items()])
    prompt = f"""
    L'utente ha raccontato di sé: "{user_text}".
    **Compito:** Analizza il profilo dell'utente e assegna le DUE categorie professionali ISTAT più adatte tra le seguenti.
    **REGOLA ETICA FONDAMENTALE:** Basa la tua scelta SOLO sulle competenze e aspirazioni descritte. Ignora genere, età o altri fattori demografici e evita stereotipi.
    {formatted_categories}
    **Rispondi esclusivamente con due numeri separati da una virgola, senza aggiungere testo.**
    """
    try:
        response = llm_client.invoke([
            SystemMessage(content="Sei un esperto imparziale nella classificazione delle professioni ISTAT."),
            HumanMessage(content=prompt)
            ],
            model=model_type,
            temperature=0.2
        )
        
        categories = response.content.strip()
        categories_list = [cat.strip() for cat in categories.split(",") if cat.strip().isdigit()]
        
        # Estraiamo le info sui token e le rendiamo compatibili
        usage_info = response.response_metadata.get('token_usage', {})
        usage = SimpleNamespace(
            prompt_tokens=usage_info.get('prompt_tokens', 0),
            completion_tokens=usage_info.get('completion_tokens', 0)
        )
        return categories_list[:2], usage
    except Exception as e:
        print(f"Errore in classify_user_category: {e}")
        return [], None

def get_explicit_professions(keyword):
    
    """
    Gestisce i casi in cui l'utente menziona esplicitamente una professione.
    Esegue una ricerca testuale diretta sull'API di INAPP usando la parola chiave fornita.
    Restituisce una lista di professioni che corrispondono alla ricerca.
    """
    
    url = f"https://api.inapp.org/professioni/search.php?flag=26&idFamiglia=1&idIndice=1&compito={keyword}&string=meccanicofulltext=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        raw_data = response.text
        clean_data = re.sub(r"<[^>]+>", "", raw_data) # Rimuove tag HTML
        clean_data = re.sub(r"\\n|\\t", "", clean_data) # Rimuove caratteri di escape        
        clean_data = re.sub(r"[^\x20-\x7E]", "", clean_data) # Rimuove caratteri non standard
        clean_data = clean_data.strip()
        try:
            data = json.loads(clean_data)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list) or not data or "result" not in data[0]:
            return []
        results = data[0].get("result", {}).get("ALTO", {})
        extracted_professions = []
        for key, value in results.items():
            if isinstance(value, dict) and "pkLivello" in value and "desc_livello" in value:
                extracted_professions.append({"code": value["pkLivello"], "desc": value["desc_livello"], "importanza": 50, "complessita": 50}) # 50 valori di deafault per fallback
        return extracted_professions
    except requests.exceptions.RequestException:
        return []

#def chiamata_api(category, value): BARA
def chiamata_api(value):

    """
    Esegue una singola chiamata all'API di INAPP per recuperare le professioni associate a una competenza.
    Questa funzione "operaia" è progettata per essere eseguita in modo concorrente e parallelo.
    Restituisce il risultato in formato JSON, o None in caso di fallimento della richiesta.
    """  
    
    url = "https://api.inapp.org/professioni/search.php"
    params = {"flag": 28, "tipo": 2, "string": value}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return None
    except requests.exceptions.RequestException:
        return None

def aggregate_best_jobs(api_results, user_category, w_B, w_C, w_D, w_G):
    
    """
    Aggrega i risultati delle API e li filtra in base alla macro-categoria ISTAT dell'utente.
    Calcola un punteggio ponderato per ogni professione e ordina la lista per pertinenza.
    Restituisce le 40 professioni candidate per la fase finale di ranking qualitativo.
    """
    
    job_scores = defaultdict(lambda: {"desc": "", "total_score": 0, "importanza": 0, "complessita": 0})
    for category, weight in [("Conoscenze", w_B), ("Skills", w_C), ("attitudini", w_D),("attivita", w_G)]:
        if category in api_results:
            for key, jobs in api_results[category].items():
                if jobs:
                    for job in jobs.values():
                        code = job.get("pkLivello", "")
                        category_numbers = user_category if isinstance(user_category, list) else user_category.split(",")
                        if any(code.startswith(num) for num in category_numbers):
                            job_scores[code]["desc"] = job.get("desc_livello", "")
                            importanza = float(job.get("importanza", 0))
                            complessita = float(job.get("complessita", 0))
                            job_scores[code]["importanza"] = importanza
                            job_scores[code]["complessita"] = complessita
                            score = weight * (100 - importanza) + (100 - complessita)
                            job_scores[code]["total_score"] += score
    sorted_jobs = sorted(job_scores.items(), key=lambda x: -x[1]["total_score"])
    return [{"code": code, "desc": job["desc"], "importanza": job["importanza"], "complessita": job["complessita"], "total_score": job["total_score"]} for code, job in sorted_jobs][:40]

@traceable
def get_affine_professions(profession_codes):
    """
    Versione PARALLELIZZATA della funzione.
    Esegue le chiamate API per trovare professioni affini in modo concorrente.
    """
    affine_professions = []
    # Usiamo un set per evitare di aggiungere duplicati
    seen_codes = set(p for p in profession_codes if p)

    # Helper function per eseguire una singola chiamata API
    def fetch_affine_for_code(code):
        if not code:
            return []
        url = f"https://api.inapp.org/professioni/search.php?codice={code}&flag=31"
        try:
            response = requests.get(url, timeout=10) # Aggiunto timeout
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            # In caso di errore per un singolo codice, restituisce una lista vuota e non blocca le altre
            return []

    # max_workers definisce quanti "lavoratori" (thread) eseguono le chiamate contemporaneamente
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Sottomettiamo tutte le chiamate API al pool di thread
        future_to_code = {executor.submit(fetch_affine_for_code, code): code for code in seen_codes}
        
        # Raccogliamo i risultati man mano che diventano disponibili
        for future in concurrent.futures.as_completed(future_to_code):
            try:
                data = future.result()
                if isinstance(data, list):
                    for item in data:
                        code = item.get("pkLivello", "")
                        # Aggiungiamo solo se non è un duplicato e non è uno dei codici originali
                        if code and code not in seen_codes:
                            affine_professions.append({"code": code, "desc": item.get("desc_livello", "")})
                            seen_codes.add(code)
            except Exception as exc:
                print(f'La chiamata per professioni affini ha generato un\'eccezione: {exc}')

    return affine_professions

def rank_professions(user_text, professions):
    
    """
    Esegue il ranking qualitativo finale, utilizzando l'LLM come un consulente di carriera.
    Assegna un punteggio di pertinenza e una motivazione personalizzata a ogni professione.
    Seleziona e restituisce le 5 professioni più adatte per il report finale.
    """
    
    if not professions: return [], None

    formatted_professions = "\n".join([f"{job['code']}: {job['desc']} (importanza: {job['importanza']}, complessità: {job['complessita']})" for job in professions])
    prompt = f"""
        L'utente ha descritto se stesso come segue: "{user_text}"
        **Compito:** Analizza le professioni elencate e classificale in base alla loro attinenza con il profilo dell'utente.
        1. Assegna un punteggio di pertinenza (`relevance_score`) da 1 a 10.
        2. Fornisci una **breve motivazione** (`reason`) per il tuo punteggio, collegandoti al profilo dell'utente.
        3. Scarta le professioni meno pertinenti.
        **REGOLE FONDAMENTALI DI ETICA E RESPONSABILITÀ:**
        - **Basa il tuo giudizio SOLO sulle competenze e aspirazioni descritte dall'utente.**
        - **EVITA STEREOTIPI:** Non penalizzare o favorire professioni sulla base di preconcetti legati a genere, età o al fatto che l'utente sia un NEET. Considera il potenziale, non solo lo stato attuale.
        - Scarta opzioni che includono l'insegnamento e la ricerca se non è menzionata esplicitamente la volontà di insegnare.
         **Professioni disponibili:** {formatted_professions}
         **Formato di risposta JSON richiesto:**
        ```json
        [
            {{"code": "X.Y", "desc": "Nome Professione", "relevance_score": 8.5, "reason": "Motivazione della valutazione..."}},
            {{"code": "X.Z", "desc": "Nome Professione", "relevance_score": 7.0, "reason": "Motivazione della valutazione..."}}
        ]
        ```
        **Restituisci solo il JSON, senza aggiungere testo.**
    """
    try:
        response = llm_client.invoke([
            SystemMessage(content="Sei un esperto di orientamento professionale, etico e imparziale, che valuta le professioni basandosi sul potenziale e le competenze dell'utente."),
            HumanMessage(content=prompt)
            ],
            model=model_type,
            temperature=0.2
        )
        
        raw_content = response.content.strip()
        cleaned_json = re.sub(r"```json|```", "", raw_content).strip()
        ranked_professions = json.loads(cleaned_json)
        ranked_professions.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Estraiamo le info sui token e le rendiamo compatibili
        usage_info = response.response_metadata.get('token_usage', {})
        usage = SimpleNamespace(
            prompt_tokens=usage_info.get('prompt_tokens', 0),
            completion_tokens=usage_info.get('completion_tokens', 0)
        )
        return ranked_professions[:5], usage
    except Exception as e:
        print(f"Errore in rank_professions: {e}")
        return [], None

def perform_fairness_audit(user_text, ranked_professions):
    
    """
    Esegue un audit etico su ciascuna delle 5 professioni finali.
    Utilizza l'LLM per identificare potenziali bias o barriere d'accesso (genere, età, background).
    Arricchisce i risultati con un'analisi di fairness per garantire suggerimenti responsabili.
    """
    
    audited_professions = []
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    
    for profession in ranked_professions:
        profession_desc = profession.get("desc", "N/A")
        prompt = f"""
        L'utente ha il seguente profilo: "{user_text}"
        Una delle professioni suggerite è: "{profession_desc}"
        **Compito di Audit Etico:**
        In linea con i principi di analisi della fairness multigruppo, analizza se la professione di "{profession_desc}" potrebbe presentare bias o barriere d'accesso per specifici SOTTOGRUPPI demografici.
        Considera i seguenti aspetti:
        1.  **Bias legati all'età:** Ci sono fasce d'età specifiche (es. under 25, over 50) che potrebbero essere ingiustamente favorite o svantaggiate?
        2.  **Bias di genere:** Esistono stereotipi di genere che potrebbero influenzare le assunzioni in questo campo?
        3.  **Bias legati al background:** La professione richiede percorsi formativi o esperienze che potrebbero escludere persone da determinati background?
        **Formato di risposta JSON richiesto:**
        ```json
        {{
            "potential_bias_summary": "Un riassunto conciso dei potenziali bias o 'Nessun bias evidente rilevato'.",
            "affected_subgroups": ["Esempio: 'Lavoratori over 50'", "Esempio: 'Donne in ruoli tecnici'"],
            "reasoning": "Spiegazione del perché questi sottogruppi potrebbero essere svantaggiati, basata su conoscenze generali del mondo del lavoro."
        }}
        ```
        **Restituisci solo il JSON, senza aggiungere testo.**
        """
        try:
            response = llm_client.invoke([
                SystemMessage(content="Sei un revisore AI specializzato in etica e fairness algoritmica, con il compito di scoprire bias nascosti in analisi multigruppo."),
                HumanMessage(content=prompt)
                ],
                model=model_type,
                temperature=0.2
            )
            
            raw_content = response.content.strip()
            cleaned_json = re.sub(r"```json|```", "", raw_content).strip()
            audit_result = json.loads(cleaned_json)
            profession['fairness_audit'] = audit_result
            
            # Accumuliamo i token direttamente dal dizionario
            usage_info = response.response_metadata.get('token_usage', {})
            if usage_info:
                total_usage["prompt_tokens"] += usage_info.get('prompt_tokens', 0)
                total_usage["completion_tokens"] += usage_info.get('completion_tokens', 0)

        except Exception as e:
            print(f"Errore durante l'audit di fairness per '{profession_desc}': {e}")
            profession['fairness_audit'] = {"potential_bias_summary": "Errore durante l'analisi di fairness.", "affected_subgroups": [], "reasoning": str(e)}
        
        audited_professions.append(profession)
        time.sleep(1) # Pausa per non sovraccaricare l'API

    return audited_professions, total_usage

def validate_user_input(full_user_text):
    """
    Un agente AI valuta se l'input dell'utente è sufficiente per un'analisi professionale significativa.
    """
    prompt = f"""
    Analizza il seguente testo fornito da un utente:
    ---
    {full_user_text}
    ---

    **Il Tuo Ruolo:** Sei un rigoroso agente di validazione. Il tuo unico obiettivo è decidere se il testo contiene **informazioni concrete e sufficienti** per un'analisi di carriera.

    **Regole Strette per la Valutazione:**
    1.  **FALLIMENTO IMMEDIATO:** Se il testo è un nonsense (es. 'asdasd', 'wheheheh'), un saluto (es. 'ciao'), o una semplice richiesta senza dettagli (es. 'trovami un lavoro'), è **INSUFFICIENTE**.
    2.  **CONTROLLO MINIMO DI SUFFICIENZA:** Per essere **SUFFICIENTE**, il testo deve contenere ALMENO UNO tra i seguenti elementi concreti:
        - Un'esperienza passata (lavoro, scuola, volontariato).
        - Una competenza o abilità (es. "so usare Photoshop", "sono bravo a parlare in pubblico").
        - Un interesse o una passione specifica (es. "mi piace il giardinaggio", "seguo la tecnologia").
        - Un obiettivo di carriera chiaro (es. "vorrei lavorare nel marketing").

    **Compito:**
    Valuta il testo in base a queste regole e rispondi con il seguente formato JSON.

    **Formato di risposta JSON richiesto:**
    ```json
    {{
        "is_sufficient": boolean,
        "feedback": "Se insufficiente, fornisci un feedback costruttivo e specifico basato sulle regole (es. 'La tua descrizione è troppo generica. Prova a raccontarmi di un'esperienza passata o di una competenza che possiedi.'). Se sufficiente, scrivi 'Descrizione sufficiente per l'analisi.'"
    }}
    ```
    **Restituisci solo il JSON.**
    """
    try:
        response = llm_client.invoke(
            [
                SystemMessage(content="Sei un assistente AI rigoroso che valuta la completezza dei profili utente per l'orientamento professionale, seguendo regole ferree."),
                HumanMessage(content=prompt)
            ],
            model=model_type,
            response_format={"type": "json_object"}, # Manteniamo il formato JSON
            temperature=0.0
        )
        result = json.loads(response.content)
        return result
    except Exception as e:
        print(f"Errore durante la validazione dell'input: {e}")
        return {"is_sufficient": True, "feedback": "Controllo di validazione saltato a causa di un errore."}

# --- FUNZIONE PRINCIPALE DELLA PIPELINE --- #
@traceable
def run_full_analysis_pipeline(user_input_text, force_fallback=False):
    """
    Esegue l'intera pipeline di analisi, dall'input utente al risultato finale.
    Questa è la funzione che verrà chiamata dal front-end Streamlit.
    """
    if not DATA_JSON:
        return {"error": "I file di dati JSON non sono stati caricati correttamente. Controlla i log."}

    try:
        
        total_input_tokens = 0
        total_output_tokens = 0
        
        # 1. Esecuzione pipeline
        selected_categories_with_reasons, usage1 = select_best_categories(user_input_text, DATA_JSON)
        if not selected_categories_with_reasons:
            return {"error": "La fase iniziale di analisi del profilo non ha prodotto risultati."}
        if usage1:
            total_input_tokens += usage1.prompt_tokens
            total_output_tokens += usage1.completion_tokens

        selected_categories = {
            "best_conoscenze": [item['code'] for item in selected_categories_with_reasons.get("best_conoscenze", [])],
            "best_skills": [item['code'] for item in selected_categories_with_reasons.get("best_skills", [])],
            "best_attitudini": [item['code'] for item in selected_categories_with_reasons.get("best_attitudini", [])],
            "best_attivita": [item['code'] for item in selected_categories_with_reasons.get("best_attivita", [])]
        }
        explicit_job_keyword = selected_categories_with_reasons.get("explicit_job_keyword", "")

        user_category, usage2 = classify_user_category(user_input_text)
        if usage2:
            total_input_tokens += usage2.prompt_tokens
            total_output_tokens += usage2.completion_tokens

        best_professions = [] # Inizializziamo la lista come vuota

        # Se il flag di test è attivo, forziamo il fallimento saltando il blocco 'try'
        if force_fallback:
            print(">>> TEST MODE: Fallback forzato attivo. <<<")
        else:
            # Altrimenti, eseguiamo il normale tentativo API in PARALLELO, protetto da un blocco try/except
            try:
                api_results = defaultdict(dict)
                tasks_to_run = []
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    # 1. Sottomettiamo tutte le chiamate per le categorie (conoscenze, skills, etc.)
                    for category, values in [("Conoscenze", selected_categories["best_conoscenze"]),
                                            ("Skills", selected_categories["best_skills"]),
                                            ("attitudini", selected_categories["best_attitudini"]),
                                            ("attivita", selected_categories["best_attivita"])]:
                        for value in values[:2]:
                            # Sottomettiamo il task e salviamo il "future" insieme ai suoi metadati
                            # future = executor.submit(chiamata_api, category, value) BARA
                            future = executor.submit(chiamata_api, value)
                            tasks_to_run.append({"type": "category", "category": category, "value": value, "future": future})

                    # 2. Sottomettiamo anche la chiamata per la keyword esplicita, se presente
                    explicit_future = None
                    if explicit_job_keyword:
                        explicit_future = executor.submit(get_explicit_professions, explicit_job_keyword)

                    # 3. Raccogliamo i risultati delle chiamate per le categorie
                    for task in tasks_to_run:
                        try:
                            result = task["future"].result(timeout=10) # Aspetta max 10 secondi per questo task
                            if result:
                                api_results[task["category"]][task["value"]] = result
                        except Exception as e:
                            print(f"Chiamata API per {task['category']}/{task['value']} fallita: {e}")
                
                # Aggreghiamo i risultati ottenuti in parallelo
                best_professions = aggregate_best_jobs(api_results, user_category, 0.25, 0.25, 0.25, 0.25)

                # 4. Raccogliamo il risultato della keyword esplicita e lo aggiungiamo
                if explicit_future:
                    try:
                        explicit_prof_result = explicit_future.result(timeout=10)
                        if explicit_prof_result:
                            best_professions.extend(explicit_prof_result)
                    except Exception as e:
                        print(f"Chiamata API per keyword esplicita '{explicit_job_keyword}' fallita: {e}")

            except Exception as api_error:
                print(f"Errore durante le chiamate API INAPP: {api_error}. Si attiva il fallback.")
                best_professions = [] # In caso di errore, ci assicuriamo che la lista sia vuota per attivare il fallback

        # Controllo e attivazione del fallback se la lista è vuota (per errore API, nessun risultato o test forzato)
        if not best_professions:
            print("⚠️  API INAPP non ha prodotto risultati. Attivazione della ricerca di fallback locale.")
            best_professions = find_professions_locally_as_fallback(user_input_text, selected_categories_with_reasons)

        ranked_results, usage3 = rank_professions(user_input_text, best_professions)
        if usage3:
            total_input_tokens += usage3.prompt_tokens
            total_output_tokens += usage3.completion_tokens
        
        audited_ranked_results, usage4 = perform_fairness_audit(user_input_text, ranked_results)
        if usage4:
            total_input_tokens += usage4["prompt_tokens"]
            total_output_tokens += usage4["completion_tokens"]
        
        main_profession_codes = [prof["code"] for prof in audited_ranked_results]
        
        try:
            # Tentativo primario di ottenere professioni affini via API
            affine_professions = get_affine_professions(main_profession_codes)
            
            # Se l'API risponde ma con una lista vuota, lo consideriamo un fallimento e attiviamo il fallback
            if not affine_professions and main_profession_codes:
                raise ValueError("L'API ha restituito una lista vuota per le professioni affini.")

        except Exception as e:
            # Se si verifica un errore di qualsiasi tipo, si attiva il fallback locale
            print(f"API per professioni affini non disponibile ({e}). Attivazione fallback locale.")
            affine_professions = get_affine_professions_locally(main_profession_codes)
        
        # 2. Calcolo costo hardcodato per il fe, se si intende ottenere un dettaglio dinamico inserire la porpria chiave lang smith 
        prices = {"gpt-4o-mini": (0.00015, 0.00060)}
        price_input, price_output = prices.get(model_type, (0, 0))
        cost = (total_input_tokens / 1000 * price_input) + (total_output_tokens / 1000 * price_output)

        # 3. Composizione del risultato finale
        final_results = {
            "audited_ranked_professions": audited_ranked_results,
            "affine_professions": affine_professions,
            "reasoning_data": selected_categories_with_reasons,
            "istat_categories": user_category,
            "usage_stats": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "estimated_cost_usd": cost
            }
        }
        
        return final_results

    except Exception as e:
        import traceback
        print(f"ERRORE NELLA PIPELINE DI BACKEND: {traceback.format_exc()}")
        return {"error": f"Si è verificato un errore critico durante l'analisi. Dettagli tecnici: {e}"}