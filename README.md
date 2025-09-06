# Progetto di Orientamento Professionale con Analisi Bottom-Up Script: backend_analysis.py

Dipendenze necesarie:

* **streamlit**: Serve per l'interfaccia web (**app_streamlit.py**).
* **openai**: Serve per comunicare con l'IA (**backend_analysis.py**).
* **python-dotenv**: Serve per caricare la tua chiave API dal file (**backend_analysis.py**).
* **requests**: Serve per fare le chiamate all'API dell'INAPP (**backend_analysis.py**).

**gitignore** per:

* **venv/ **: Impedisce di caricare l'intera cartella dell'ambiente virtuale, che può essere molto pesante e contiene file specifici del tuo computer.
* **pycache/ e *.pyc**: Sono file temporanei che Python crea per velocizzare l'esecuzione. Non servono nel repository.
* **.vscode/, .idea/, .DS_Store**: Sono cartelle e file di configurazione specifici del tuo editor di testo o del tuo sistema operativo. È buona norma ignorarli per non "imporre" le tue preferenze agli altri collaboratori.

# Career Compass AI: Guida Tecnica e Architetturale

## Introduzione e Obiettivi

 **Career Compass AI** **è un'applicazione web avanzata progettata per fornire orientamento professionale personalizzato, etico e spiegabile. Partendo da una descrizione testuale libera fornita dall'utente, il sistema sfrutta un'architettura a due componenti—un potente** **motore di analisi (backend)** **e un'**interfaccia utente interattiva (frontend)**—per suggerire le professioni più adatte secondo la classificazione ISTAT.**

 **Gli obiettivi principali del progetto sono:**

* **Analisi Personalizzata:** **Tradurre il racconto informale di un utente in un profilo strutturato di competenze, conoscenze e attitudini.**
* **Intelligenza Artificiale Responsabile:** **Integrare principi di** **Responsible AI** **per mitigare i bias, evitare stereotipi e fornire analisi di fairness trasparenti su ogni suggerimento, ispirandosi a ricerche accademiche sull'analisi multigruppo.**
* **Spiegabilità (Explainability):** **Rendere il processo decisionale dell'IA il più trasparente possibile, motivando ogni scelta e mostrando all'utente il "ragionamento" che ha portato ai risultati finali.**
* **Esperienza Utente Guidata:** **Offrire un'interfaccia intuitiva e interattiva, costruita con Streamlit, che faciliti il dialogo con l'IA e la consultazione dei risultati.**

**Questo documento è diviso in due parti: la prima descrive minuziosamente il motore di analisi (**backend_analysis.py**), mentre la seconda illustra l'architettura e le funzionalità dell'interfaccia utente (**app_streamlit.py**).**

---

## Parte 1: Il Motore di Analisi (**backend_analysis.py**)

**Il backend è il cuore pulsante dell'applicazione. È un modulo Python che non viene eseguito direttamente, ma espone una funzione principale (**run_full_analysis_pipeline**) che orchestra una serie di agenti AI e chiamate API per processare l'input dell'utente.**

### Descrizione Minuziosa delle Funzioni

#### validate_user_input(full_user_text)

* **Obiettivo:** **Agire da "filtro di qualità" o "gatekeeper". Questa funzione è il primo passo critico per evitare analisi inutili e costose su input di bassa qualità.**
* **Processo:**

  * **Riceve il testo completo della conversazione dell'utente.**
  * **Utilizza un prompt LLM con** **regole molto rigide** **per valutare se il testo è sufficiente per un'analisi di carriera.**
  * **Identifica e scarta immediatamente input palesemente inutili (es. "wheheheh", "ciao", "trovami un lavoro").**
  * **Verifica la presenza di almeno un elemento concreto (esperienza, competenza, interesse o obiettivo).**
* **Valore di Ritorno:** **Un dizionario JSON con un booleano** **is_sufficient** **e un campo** **feedback** **che fornisce un messaggio costruttivo all'utente in caso di input insufficiente.**

#### select_best_categories(user_text, json_data)

* **Obiettivo:** **Tradurre il testo libero e non strutturato dell'utente in un profilo di competenze standardizzato e spiegabile.**
* **Processo:**

  * **Riceve il testo validato e i dizionari JSON (**conoscenze**,** **skills**, etc.).
  * **Costruisce un prompt LLM che include il testo dell'utente e gli elenchi completi delle categorie, usandoli come "vocabolario controllato".**
  * **Incarica l'IA di selezionare le** **due categorie più pertinenti** **per ogni area (B, C, D, G) e di estrarre una keyword esplicita.**
  * **Integrazione Etica:** **Il prompt contiene regole ferree per ignorare dati demografici (età, genere) ed evitare stereotipi.**
  * **Spiegabilità:** **Per ogni codice scelto (es. "B9"), l'IA deve fornire una chiave** **"reason"** **che motiva la scelta basandosi su una citazione o parafrasi del testo dell'utente.**
* **Valore di Ritorno:** **Un dizionario contenente le liste dei codici selezionati (con motivazione) e la keyword.**

#### classify_user_category(user_text)

* **Obiettivo:** **Identificare le due macro-aree professionali ISTAT (Grandi Gruppi 1-9) più adatte al profilo generale dell'utente.**
* **Processo:**

  * **Recupera le 9 categorie ISTAT tramite** **get_istat_categories()**.
  * **Usa un prompt LLM per chiedere una classificazione di alto livello, sempre applicando le regole anti-bias.**
* **Scopo:** **Il risultato di questa funzione viene usato a valle come** **filtro strategico** **nella funzione** **aggregate_best_jobs** **per garantire che i suggerimenti appartengano a settori coerenti.**

#### aggregate_best_jobs(...)

* **Obiettivo:** **Fondere i risultati grezzi delle chiamate API in una lista unificata e ponderata di professioni candidate.**
* **Processo:**

  * **Riceve i risultati delle chiamate API per ogni codice B, C, D, G.**
  * **Filtra le professioni trovate, mantenendo solo quelle che appartengono alle macro-categorie ISTAT identificate in precedenza.**
  * **Calcola un punteggio per ogni professione, favorendo quelle con** **bassa importanza e bassa complessità** **per renderle più accessibili, specialmente per profili entry-level.**
* **Valore di Ritorno:** **Una lista ordinata delle 40 migliori professioni candidate, pronte per la valutazione finale.**

#### rank_professions(user_text, professions)

* **Obiettivo:** **Eseguire la valutazione finale. Questo agente AI agisce come un consulente di orientamento esperto, applicando un giudizio qualitativo alla lista preselezionata.**
* **Processo:**

  * **Riceve la lista delle 40 professioni candidate.**
  * **Usa un prompt LLM per chiedere di assegnare un punteggio di pertinenza (**relevance_score **da 1 a 10) e una** **motivazione testuale** **per ogni scelta.**
  * **Il prompt include istruzioni etiche specifiche, come considerare il potenziale dell'utente e non solo lo stato attuale (particolarmente importante per i profili NEET).**
* **Valore di Ritorno:** **Una lista ordinata delle 5 professioni più pertinenti, complete di punteggio e motivazione.**

#### perform_fairness_audit(user_text, ranked_professions)

* **Obiettivo:** **Arricchire i risultati finali con un'analisi critica dei potenziali bias, ispirata direttamente dai concetti di** **analisi multigruppo a grana fine** **dell'articolo di ricerca.**
* **Processo:**

  * **Itera su ciascuna delle 5 professioni finali.**
  * **Per ogni professione, invia un nuovo prompt a un agente AI specializzato in etica.**
  * **Il prompt chiede di identificare potenziali bias o barriere d'accesso non per categorie generiche, ma per** **sottogruppi specifici** **(es. "lavoratori over 50", "donne in ruoli tecnici").**
* **Valore di Ritorno:** **La lista delle professioni arricchita con un dizionario** **fairness_audit** **per ciascuna, contenente un riassunto dei bias, i sottogruppi interessati e la motivazione.**

#### run_full_analysis_pipeline(user_input_text)

* **Obiettivo:** **Essere l'**unico punto di ingresso **per il frontend. Orchestra l'intera sequenza di analisi in modo robusto.**
* **Processo:**

  * **Validazione Iniziale:** **Chiama** **validate_user_input** **come primo passo. Se l'input è insufficiente, si ferma e restituisce il feedback.**
  * **Esecuzione a Cascata:** **Se la validazione ha successo, esegue in sequenza tutte le altre funzioni di analisi (**select_best_categories**,** **classify_user_category**, **aggregate_best_jobs**, **rank_professions**, **perform_fairness_audit**, etc.).
  * **Gestione Errori:** **L'intera funzione è avvolta in un blocco** **try...except** **che cattura qualsiasi errore imprevisto durante la pipeline e lo restituisce in un formato gestibile dal frontend, prevenendo crash.**
  * **Aggregazione Risultati:** **Compone un unico dizionario finale contenente tutti i dati necessari per la visualizzazione nel frontend (professioni consigliate, dati per il ragionamento, statistiche di utilizzo, etc.).**

---

## Parte 2: L'Interfaccia Utente (**app_streamlit.py**)

**Il frontend è costruito con Streamlit e progettato per essere intuitivo, reattivo e informativo. La sua logica è basata sulla gestione dello stato della sessione per creare un'esperienza interattiva fluida.**

### Architettura e Componenti Chiave

#### Gestione dello Stato (**st.session_state**)

**Lo stato della sessione è fondamentale per il funzionamento dell'app. Vengono utilizzate diverse variabili per tracciare:**

* **messages**: La cronologia della conversazione tra utente e AI.
* **full_text**: Il testo completo e accumulato del profilo utente.
* **analysis_triggered**: Un booleano che funge da "trigger" per avviare l'analisi dopo che l'utente ha confermato.
* **analysis_done**: Un booleano che indica se l'analisi è completa e se i risultati possono essere mostrati nella sidebar.

#### Caching per Performance (**@st.cache_data**)

**La funzione** **run_analysis**, che chiama la pipeline del backend, è decorata con **@st.cache_data**. Questo è cruciale per due motivi:

* **Risparmio Economico:** **Evita di eseguire nuovamente le costose chiamate alle API di OpenAI se l'input dell'utente non è cambiato.**
* **Velocità:** **Una volta completata la prima analisi, l'utente può interagire con l'interfaccia (es. aprire e chiudere sezioni nella sidebar) e i risultati verranno ricaricati istantaneamente dalla cache, rendendo l'app estremamente reattiva.**

#### Funzioni di Callback (**on_click**)

**L'interazione con i pulsanti è gestita tramite funzioni di callback. Questo approccio moderno, raccomandato da Streamlit, previene errori (**StreamlitAPIException**) e permette una gestione pulita dello stato. Ad esempio, la** **add_detail_callback** **aggiorna la chat e svuota la casella di testo prima che la pagina venga ridisegnata.**

### Struttura del Layout

#### Area Principale (Chat)

* **Box Informativo:** **Un'intestazione chiara e stilizzata spiega all'utente come interagire con l'app.**
* **Cronologia Chat:** **I messaggi vengono visualizzati in "bolle" con stili diversi per l'utente e per l'IA.**
* **Area di Input:** **Un'etichetta personalizzata (**`<h5>`**) e una** **textarea** **per l'inserimento del testo, seguita da due pulsanti:**

  * **Aggiungi dettaglio**: Disabilitato se la text area è vuota, permette di costruire il profilo in più passaggi.
  * **Analizza il mio profilo**: Avvia la sequenza di validazione e analisi.

#### Sidebar Sinistra (Report di Analisi)

**La sidebar è il cruscotto dei risultati. È inizialmente vuota e si popola solo dopo un'analisi completata con successo. È strutturata con sezioni espandibili (**st.expander**) per mantenere l'ordine e la leggibilità.**

* **🎯 Le Tue Professioni Consigliate:** **La sezione più importante, mostrata espansa di default. Per ogni professione, visualizza:**

  * **Il nome e il codice ISTAT come** **link cliccabile** **a una ricerca Google.**
  * **Un** **progress bar** **visivo per il punteggio di pertinenza.**
  * **La** **motivazione** **testuale fornita dall'IA.**
  * **Il** **report di Fairness Audit**, che usa icone (✅/⚠️) e colori per evidenziare la presenza di potenziali bias.
* **🔗 Percorsi Correlati:** **Un elenco di professioni affini, anch'esse cliccabili, per incoraggiare l'esplorazione.**
* **🧠 Il Ragionamento dell'IA:** **La sezione dedicata alla spiegabilità. Mostra le categorie B, C, D, G che l'IA ha estratto, insieme alla motivazione testuale per ciascuna, traducendo i codici in descrizioni leggibili grazie ai file JSON caricati.**
* **⚙️ Dati di Classificazione:** **Una sezione per i dettagli tecnici, come le macro-categorie ISTAT identificate e le statistiche di utilizzo delle API (token e costo stimato).**

---

## Come Avviare l'Applicazione

* **Creare l'Ambiente Virtuale:**

  **code**Bash

  ```
  python -m venv venv
  ```
* **Attivare l'Ambiente:**

  * **Windows:** **.\venv\Scripts\activate**
  * **macOS/Linux:** **source venv/bin/activate**
* **Installare le Dipendenze:**

  **code**Bash

  ```
  pip install -r requirements.txt
  ```
* **Configurare la Chiave API:** **Creare un file** **.env** **nella cartella principale e inserire** **OPENAI_API_KEY="sk-..."**.
* **Lanciare l'Applicazione:**

  **code**Bash

  ```
  streamlit run app_streamlit.py
  ```
