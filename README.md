# 🧭 Career Compass AI: Documentazione Tecnica Completa

 **Career Compass AI** **è un'applicazione web avanzata progettata per fornire orientamento professionale personalizzato, etico e spiegabile. Partendo da una descrizione testuale libera fornita dall'utente, il sistema sfrutta un'architettura a due componenti—un potente** **motore di analisi (backend)** **e un'**interfaccia utente interattiva (frontend)**—per suggerire le professioni più adatte secondo la classificazione ISTAT.**

### Indice

1. FunzionalitàChiave
2. Architetturadel Sistema
3. Tech Stack e Dipendenze
4. Setup e Installazione
5. Approfondimento sul Backend (backend_analysis.py)

    ·       Descrizione delle Funzioni

    ·       Ottimizzazione delle Performance

    ·       Monitoraggio e Tracing con LangSmith

    ·       Meccanismo di Fallback

6. Approfondimento sul Frontend (app_streamlit.py)

    ·       Architettura e Componenti

    ·       Struttura del Layout

7. Fonti Dati
8. Esempi di Test

---

## ✨ Funzionalità Chiave

* **Analisi Personalizzata:** **Traduce il racconto informale di un utente in un profilo strutturato di competenze, conoscenze e attitudini.**
* **Intelligenza Artificiale Responsabile:** **Integra principi di** **Responsible AI** **per mitigare i bias, evitare stereotipi e fornire analisi di fairness trasparenti su ogni suggerimento.**
* **Spiegabilità (Explainability):** **Rende il processo decisionale dell'IA trasparente, motivando ogni scelta e mostrando il "ragionamento" che ha portato ai risultati.**
* **Robustezza e Resilienza:** **Implementa un meccanismo di** **fallback automatico** **che utilizza un database locale (**profession_data.py**) qualora i servizi API esterni non siano disponibili, garantendo la continuità del servizio.**
* **Performance Ottimizzate:** **Sfrutta la** **parallelizzazione** **(**concurrent.futures**) per eseguire chiamate API multiple simultaneamente, riducendo drasticamente i tempi di attesa.**
* **Monitoraggio Avanzato:** **Integrato con** **LangSmith** **per il tracing end-to-end, il monitoraggio dei costi, della latenza e dei token utilizzati in ogni fase della pipeline.**

---

## 🏗️ Architettura del Sistema

**Il sistema segue un flusso logico chiaro, orchestrando diverse tecnologie per fornire un'analisi completa:**

* **Utente** **→ Interagisce con l'**Interfaccia Streamlit **(**app_streamlit.py**).**
* **Streamlit Frontend** **→ Invia il profilo utente al** **Backend** **(**backend_analysis.py**) tramite la funzione** **run_full_analysis_pipeline**.
* **Backend Pipeline** **→ Esegue una catena di agenti AI e chiamate:**

  * **Chiamate a OpenAI (via LangChain)**: Per validare l'input, estrarre competenze, classificare, classificare le professioni ed eseguire l'audit di fairness.
  * **Chiamate all'API INAPP (in parallelo)**: Per recuperare le professioni associate alle competenze. In caso di fallimento, si attiva il **fallback** **sul database locale.**
* **LangSmith** **→ Tutte le chiamate LangChain vengono tracciate e registrate per il monitoraggio.**
* **Backend** **→ Restituisce un unico dizionario JSON con i risultati completi al** **Frontend**.
* **Streamlit Frontend** **→ Visualizza i risultati in un report interattivo e facile da consultare nella sidebar.**

---

## 🛠️ Tech Stack e Dipendenze

| **Tecnologia**           | **Scopo**                                                                                      |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| **Streamlit**            | **Creazione dell'interfaccia utente web interattiva.**                                         |
| **OpenAI (gpt-4o-mini)** | **Motore di intelligenza artificiale per l'analisi del testo e il ragionamento.**              |
| **LangChain**            | **Framework per orchestrare le chiamate all'LLM e abilitare il tracing.**                      |
| **LangSmith**            | **Piattaforma per il monitoraggio, il debug e l'analisi delle performance dell'applicazione.** |
| **Requests**             | **Esecuzione delle chiamate HTTP alle API esterne di INAPP.**                                  |
| **Dotenv**               | **Gestione delle variabili d'ambiente e delle chiavi API in locale.**                          |

---

## 🚀 Setup e Installazione

* **Clonare il Repository**

  **code**Bash

  ```
  git clone <url-del-tuo-repository>
  cd <nome-cartella-progetto>
  ```
* **Creare e Attivare l'Ambiente Virtuale**

  **code**Bash

  ```
  python -m venv venv
  # Windows
  .\venv\Scripts\activate
  # macOS/Linux
  source venv/bin/activate
  ```
* **Installare le Dipendenze**

  **code**Bash

  ```
  pip install -r requirements.txt
  ```
* **Configurare le Variabili d'Ambiente**
  Crea un file **.env** **nella cartella principale del progetto e inserisci le tue chiavi:**

  **code**Ini

  ```
  OPENAI_API_KEY="sk-..."
  LANGCHAIN_TRACING_V2="true"
  LANGCHAIN_API_KEY="ls__..."
  LANGCHAIN_PROJECT="Career-Compass-AI" # o il nome che preferisci
  ```
* **Avviare l'Applicazione**

  **code**Bash

  ```
  streamlit run app_streamlit.py
  ```

---

## 🧠 Approfondimento sul Backend (**backend_analysis.py**)

**Il backend è il cuore dell'applicazione. Espone la funzione** **run_full_analysis_pipeline** **che orchestra una serie di agenti AI e chiamate API.**

### Descrizione Minuziosa delle Funzioni

* **validate_user_input**: Agisce da "gatekeeper", utilizzando un LLM con regole rigide per scartare input di bassa qualità prima di avviare l'analisi costosa.
* **select_best_categories**: Traduce il testo libero dell'utente in un profilo di competenze standardizzato e spiegabile, obbligando l'IA a motivare ogni scelta.
* **classify_user_category**: Identifica le macro-aree professionali ISTAT più adatte, usate a valle come filtro strategico.
* **aggregate_best_jobs**: Fonde i risultati grezzi delle API, li filtra e calcola un punteggio di accessibilità.
* **rank_professions**: Agisce come un consulente di orientamento AI, applicando un giudizio qualitativo e assegnando un punteggio finale di pertinenza.
* **perform_fairness_audit**: Esegue un'analisi critica dei potenziali bias per ogni professione suggerita, identificando sottogruppi specifici che potrebbero incontrare barriere.

### ⚡ Ottimizzazione delle Performance (Chiamate API Parallele)

**Per ridurre la latenza, le chiamate all'API esterna di INAPP, che sono numerose e sequenziali per natura, sono state parallelizzate utilizzando la libreria** **concurrent.futures.ThreadPoolExecutor**.

* **Problema:** **L'attesa totale era la** **somma** **dei tempi di ogni singola chiamata API.**
* **Soluzione:** **Le chiamate vengono sottomesse a un pool di thread e èseguite simultaneamente. L'attesa totale è ora pari al tempo della singola chiamata più lenta, con una** **riduzione drastica del tempo di attesa complessivo**.

### 📈 Monitoraggio e Tracing con LangSmith

**L'applicazione è completamente integrata con LangSmith per garantire osservabilità e manutenibilità.**

* **Implementazione:**

  * **Tutte le chiamate a OpenAI sono gestite tramite il client** **langchain-openai**.
  * **La variabile d'ambiente** **LANGCHAIN_TRACING_V2="true"** **attiva automaticamente il monitoraggio.**
  * **Le funzioni principali sono decorate con** **@traceable** **per ottenere una visione granulare della pipeline.**
* **Benefici:**

  * **Analisi della Latenza:** **Visualizzazione a cascata (waterfall) dei tempi di esecuzione di ogni funzione e chiamata LLM, per identificare facilmente i colli di bottiglia.**
  * **Controllo dei Costi:** **Monitoraggio preciso del numero di token e del costo stimato per ogni analisi.**
  * **Debug:** **Ispezione completa dei prompt inviati e delle risposte ricevute per ogni passaggio.**

### 🛡️ Meccanismo di Fallback per la Ricerca delle Professioni

**Il sistema è progettato per essere resiliente. Se le API INAPP falliscono o non restituiscono risultati, si attiva automaticamente un percorso di emergenza.**

* **Attivazione:** **Il fallback scatta se le chiamate API generano un'eccezione o restituiscono una lista vuota.**
* **Funzionamento:**

  * **Fonte Dati Locale**: Invece dell'API, viene utilizzato il dizionario **PROFESSIONI_ISTAT_3_DIGIT** **dal file** **profession_data.py**.
  * **Abbinamento Semantico via LLM**: Un prompt di emergenza incarica l'IA di confrontare il profilo utente con le descrizioni delle professioni nel file locale per trovare le corrispondenze più pertinenti.
  * **Continuità della Pipeline**: I risultati del fallback vengono re-iniettati nel flusso di analisi, che prosegue senza interruzioni.
* **Test:** **È possibile forzare l'attivazione del fallback per scopi di debug tramite il checkbox** **🧪 Forzare test di fallback** **nella sidebar.**

---

## 🖥️ Approfondimento sul Frontend (**app_streamlit.py**)

**Il frontend è costruito con Streamlit per essere intuitivo e reattivo, basandosi sulla gestione dello stato di sessione.**

### Architettura e Componenti Chiave

* **Stato di Sessione (**st.session_state**)**: Utilizzato per tracciare la cronologia della chat (**messages**), il testo completo (**full_text**), e i flag di controllo del flusso (**analysis_triggered**, **analysis_done**).
* **Caching (**@st.cache_data**)**: La funzione **run_analysis** **è "wrappata" nella cache di Streamlit. Questo evita di rieseguire analisi costose se l'input non cambia, rendendo l'app reattiva e risparmiando sui costi delle API.**
* **Callback (**on_click**)**: L'interazione con i pulsanti è gestita tramite callback per una gestione pulita dello stato, prevenendo errori e garantendo che le azioni vengano eseguite prima del ridisegno della pagina.

### Struttura del Layout

* **Area Principale (Chat)**:

  * **Un box informativo guida l'utente.**
* **La chat viene visualizzata con "bolle" stilizzate.**
* **Un'area di testo e tre pulsanti principali gestiscono l'interazione:**

  * **Aggiungi dettaglio**: Per costruire il profilo in più passaggi.
  * **Analizza il mio profilo**: Per avviare la validazione e l'analisi.
  * **Termina analisi**: Per resettare completamente la sessione e iniziare una nuova analisi.
* **Sidebar Sinistra (Report di Analisi)**:

  * **Un cruscotto dinamico che si popola solo dopo l'analisi.**
* **🎯 Le Tue Professioni Consigliate**: Mostra le top 5 professioni con link a Google, barra di pertinenza, motivazione dell'IA e un chiaro report di Fairness Audit con icone (✅/⚠️).
* **🔗 Percorsi Correlati**: Incoraggia l'esplorazione di professioni affini.
* **🧠 Il Ragionamento dell'IA**: La sezione dedicata alla spiegabilità, che mostra le competenze estratte e le relative motivazioni.
* **⚙️ Dati di Classificazione**: Riporta dettagli tecnici come le macro-categorie ISTAT e le statistiche di utilizzo (token e costo) tracciate da LangSmith.

---

## 📚 Fonti dei Dati

**L'applicazione si basa su diverse fonti di dati per la sua analisi:**

* **File JSON (**/JSON**)**: Contengono le tassonomie di **conoscenze, skills, attitudini e attività generalizzate**. Vengono utilizzati dall'IA come vocabolario controllato per standardizzare il profilo utente.
* **Database Locale (**profession_data.py**)**: Questo file contiene un dizionario Python (**PROFESSIONI_ISTAT_3_DIGIT**) che mappa i codici ISTAT a 3 digit a schede descrittive complete (nome, descrizione, esempi, formazione, mercato). Viene utilizzato come fonte dati primaria durante il **meccanismo di fallback**.

---

## 🧪 Esempi di Test

**Per validare il sistema, utilizzare profili utente:**

### Esempio 1: Il Neolaureato Tecnico

Sono un neolaureato in Ingegneria Informatica. Durante gli studi mi sono appassionato allo sviluppo software, in particolare al linguaggio Python e allo sviluppo di applicazioni web. Ho realizzato un piccolo progetto personale per un sito di e-commerce e mi piace molto l'idea di creare strumenti che risolvano problemi reali. Sono una persona logica, precisa e mi piace trovare soluzioni efficienti a problemi complessi. Cerco un lavoro dove possa applicare le mie competenze di programmazione e continuare a imparare nuove tecnologie.

### Esempio 2: L'Artigiano Creativo

La mia vera passione è lavorare con le mani. Nel mio tempo libero mi dedico al restauro di vecchi mobili in legno, mi piace ridare vita a oggetti che altri butterebbero. Uso molto il legno ma mi affascina anche la lavorazione del metallo. Sono molto preciso, quasi maniacale per i dettagli, e credo nella qualità e nella durata delle cose. Non mi piace stare fermo a una scrivania, ho bisogno di creare qualcosa di concreto e vederlo finito. Cerco un'attività che mi permetta di usare la mia manualità e la mia creatività.

### Esempio 3: Il Profilo Orientato al Business e alla Gestione

Ho una laurea triennale in economia e ho lavorato per due anni come assistente marketing. Mi occupavo di analizzare i dati delle campagne e di preparare report per il mio responsabile. Mi piace molto l'aspetto strategico del lavoro: capire il mercato, pianificare le attività e coordinare le persone per raggiungere un obiettivo. Ho buone doti organizzative e comunicative. Il mio obiettivo è crescere professionalmente e arrivare un giorno a gestire un team o dei progetti importanti in autonomia.
