# WarpCore + WarpFlow — System Architecture

## 1. High-Level System Architecture

The system consists of **three Docker services** and a **cloud-hosted database**, all orchestrated via Docker Compose.

```mermaid
graph TB
    subgraph "Frontend (WarpFlow)"
        FE["React + Vite + TypeScript<br/>:5173"]
    end

    subgraph "Backend (WarpCore)"
        API["FastAPI Server<br/>:8080"]
    end

    subgraph "CV Microservice"
        CV["CV Service (FastAPI + PyTorch)<br/>:8001"]
    end

    subgraph "External Cloud Services"
        DB[("Supabase PostgreSQL<br/>(AWS ap-south-1)")]
        S3[("AWS S3 / MinIO<br/>warpflow-storage")]
        CHROMA[("ChromaDB<br/>(Local Persistent)")]
    end

    subgraph "Third-Party APIs"
        GOOGLE["Google Workspace APIs"]
        OPENAI["OpenAI API"]
        GEMINI["Google Gemini API"]
        TWILIO["Twilio API"]
        ELEVEN["ElevenLabs API"]
        SLACK["Slack API"]
        TELEGRAM["Telegram Bot API"]
    end

    FE <-->|"REST + WebSocket<br/>(CORS)"| API
    API <-->|"HTTP (internal network)"| CV
    API <-->|"asyncpg (NullPool)"| DB
    API <-->|"boto3"| S3
    API <-->|"chromadb.PersistentClient"| CHROMA
    API <-->|"httpx / OAuth2"| GOOGLE
    API <-->|"httpx"| OPENAI
    API <-->|"httpx"| GEMINI
    API <-->|"httpx"| TWILIO
    API <-->|"httpx"| ELEVEN
    API <-->|"httpx"| SLACK
    API <-->|"httpx"| TELEGRAM
    CV -.->|"Shared Volume: cv-models"| S3
```

---

## 2. Docker Compose Deployment

| Service | Port | Context | Key Details |
|---|---|---|---|
| **warpcore** | `8080` | `./warpcore` | Main API; depends on `cv-service` health |
| **cv-service** | `8001` | `./warpcore/app/services/cv` | Training & inference; healthcheck at `/health` |
| **cv-service-gpu** *(optional)* | `8001` | Same as above, `Dockerfile.gpu` | NVIDIA GPU reservation (`count: 1`) |

**Shared resources:**
- **Network:** `warpcore-network` (bridge driver)
- **Volumes:** `cv-models` (shared between warpcore & cv-service), `./datasets` bind mount

---

## 3. Agent & Tool Orchestration Flow

The **AI Agent** is the central orchestrator. Users build visual workflows by connecting nodes on a canvas. At execution time, the **WorkflowEngine** picks the agent node, resolves connected service nodes, registers tools, and runs an LLM function-calling loop.

```mermaid
sequenceDiagram
    participant U as User (WarpFlow)
    participant API as WarpCore API
    participant EE as Execution Engine
    participant WE as WorkflowEngine
    participant LLM as Gemini / OpenAI
    participant TR as Tool Registry
    participant SVC as Service Functions

    U->>API: POST /api/workflows/{id}/execute
    API->>EE: start_workflow(db, workflow_id, trigger_data)
    EE->>EE: Load Workflow from DB
    EE->>EE: Find ai-agent node
    alt No AI Agent Node
        EE->>EE: execute_direct_workflow()<br/>(BFS through service nodes)
    else Has AI Agent Node
        EE->>EE: Resolve API key from UserSecret
        EE->>EE: Build prompt from template + trigger_data
        EE->>WE: new WorkflowEngine(db, user, nodes, connections)
        WE->>WE: Build adjacency graph
        WE->>WE: Find service nodes connected to agent
        WE->>WE: Extract node configurations
        WE->>TR: _register_tools(service_nodes)
        TR->>TR: Resolve credentials per node type<br/>(OAuth / botToken / credential-less)
        WE->>LLM: Send prompt + tool definitions
        loop Agent Loop (max 15 iterations)
            LLM-->>WE: Function call(s) or final text
            WE->>SVC: _execute_tool(name, args)
            SVC-->>WE: Result
            WE->>LLM: Return function results
        end
        WE-->>EE: {status, summary, steps[]}
    end
    EE-->>API: Execution result
    API-->>U: JSON response
```

### Tool Registry Architecture

The `TOOL_REGISTRY` maps **node types → tool definitions**. Each tool has a name, description, JSON Schema parameters, and an `_fn` reference.

```mermaid
graph LR
    subgraph "TOOL_REGISTRY (tools.py)"
        direction TB
        GD["google-docs<br/>5 tools"]
        GDR["google-drive<br/>7 tools"]
        GM["gmail<br/>6 tools"]
        GS["google-sheets<br/>6 tools"]
        GF["google-forms<br/>5 tools"]
        ML["ml-trainer / data-prep /<br/>supervised-train / unsupervised-train<br/>11+ tools"]
        CS["context-store<br/>6 tools"]
        CVT["cv-train / cv-inference<br/>4 tools"]
        TW["twilio<br/>5 tools"]
        EL["elevenlabs<br/>3 tools"]
        PG["postgresql<br/>5 tools"]
        SL["slack<br/>28 tools"]
        TG["telegram<br/>30+ tools"]
        AW["aws (S3)<br/>19 tools"]
    end

    subgraph "Credential Resolution"
        OAUTH["OAuth2 Token<br/>(Google Workspace)"]
        BOT["Bot Token / API Key<br/>(Slack, Telegram)"]
        CREDLESS["Credential-less<br/>(ML, CV, Context, Twilio,<br/>ElevenLabs, PostgreSQL)"]
    end

    GD & GDR & GM & GS & GF --> OAUTH
    SL & TG --> BOT
    ML & CS & CVT & TW & EL & PG --> CREDLESS
```

### Credential-Less Tools flow
For `CREDENTIAL_LESS_TOOLS`, the engine passes the **user_id** instead of an OAuth token, and the wrapper function fetches secrets from the `UserSecret` table at call time.

---

## 4. Workflow Triggers & Execution Paths

Workflows can be triggered multiple ways:

```mermaid
graph TB
    subgraph "Trigger Sources"
        MT["Manual Trigger<br/>(UI button)"]
        SCH["Schedule Trigger<br/>(APScheduler cron)"]
        WH["Webhook Trigger<br/>(HTTP POST)"]
        ET["Email Trigger<br/>(Gmail poller)"]
        NT["News Trigger<br/>(RSS poller)"]
    end

    subgraph "Execution Paths"
        direction TB
        EE["Execution Engine<br/>(start_workflow)"]
        DP["Direct Path<br/>(BFS, no AI agent)"]
        AP["Agent Path<br/>(LLM-orchestrated)"]
    end

    MT & SCH & WH & ET & NT --> EE
    EE -->|"No ai-agent node"| DP
    EE -->|"Has ai-agent node"| AP
    DP -->|"Execute Google Workspace<br/>nodes sequentially"| RESULT["Result"]
    AP -->|"LLM function-calling<br/>loop with tools"| RESULT
```

### Background Pollers (Lifespan)

| Poller | Function | Interval |
|---|---|---|
| **Scheduler** | `APScheduler` with `AsyncIOScheduler` | Cron-based per workflow |
| **Email Poller** | Polls Gmail for new emails | Configurable |
| **News Poller** | Polls RSS/News feeds | Configurable |

---

## 5. CV Training & Inference Pipeline

### 5.1 CV Microservice Architecture

The CV service is a **standalone FastAPI microservice** running on port 8001 with its own PyTorch environment.

```mermaid
graph TB
    subgraph "CV Microservice (:8001)"
        direction TB
        HEALTH["/health"]
        TRAIN["/training/train"]
        TASKS_EP["/training/tasks"]
        LOAD["/inference/models/load"]
        INFER["/inference/process_image"]
        SAVED["/inference/models/saved"]
        STREAM["/inference/video_feed<br/>(MJPEG)"]
        WS["/inference/detection/stream<br/>(WebSocket)"]

        subgraph "Training Pipeline"
            VT["visiontrain.py"]
            CT["ClassificationTask"]
            DT["DetectionTask"]
            ST["SegmentationTask"]
        end

        subgraph "Inference Pipeline"
            IE["InferenceEngine"]
            MR["Model Registry<br/>(in-memory cache)"]
        end
    end

    TRAIN --> VT
    VT --> CT & DT & ST
    LOAD --> IE
    IE --> MR
    INFER --> IE
    STREAM --> IE
    WS --> IE
```

### 5.2 CV Training — Supported Models & Methods

```mermaid
graph LR
    subgraph "Classification (8 models)"
        direction TB
        C1["ResNet-50"]
        C2["EfficientNet-B0"]
        C3["VGG-16"]
        C4["Inception V3"]
        C5["MobileNet V2"]
        C6["DenseNet-121"]
        C7["ViT-B/16"]
        C8["ConvNeXt-Tiny"]
    end

    subgraph "Detection (10 models)"
        direction TB
        D1["YOLOv3/v4/v5/v8"]
        D2["Faster R-CNN"]
        D3["SSD-300"]
        D4["RetinaNet"]
        D5["EfficientDet"]
        D6["DETR"]
        D7["Mask R-CNN"]
    end

    subgraph "Segmentation (9 models)"
        direction TB
        S1["U-Net (smp)"]
        S2["DeepLabV3"]
        S3["PSPNet (smp)"]
        S4["SegNet"]
        S5["FCN"]
        S6["Mask R-CNN"]
        S7["YOLACT"]
        S8["SegFormer"]
        S9["Mask2Former"]
    end
```

### 5.3 CV Training Flow

```mermaid
sequenceDiagram
    participant U as User / Agent Tool
    participant API as WarpCore API
    participant CV as CV Service (:8001)
    participant GPU as PyTorch (CUDA/CPU)
    participant DISK as Saved Models Volume

    U->>API: cv_train_model(task, model, dataset_path, ...)
    API->>CV: POST /training/train
    CV->>CV: Validate task, model, optimizer
    CV->>CV: get_task() → ClassificationTask / DetectionTask / SegmentationTask
    CV->>GPU: task.train()
    Note over GPU: 1. load_data() — ImageFolder/COCO/Binary masks
    Note over GPU: 2. get_model() — Load pretrained torchvision model
    Note over GPU: 3. Modify final layer for num_classes
    Note over GPU: 4. get_optimizer() — SGD/Adam/RMSprop/AdaGrad/AdamW
    Note over GPU: 5. Training loop (epochs × batches)
    Note over GPU: 6. Validation after each epoch
    GPU->>DISK: save_model() → .pt checkpoint
    CV-->>API: {status, model_saved_at}
    API-->>U: Training result
```

### 5.4 CV Inference Flow

```mermaid
sequenceDiagram
    participant U as User / Agent Tool
    participant API as WarpCore API
    participant CV as CV Service
    participant IE as InferenceEngine
    participant GPU as PyTorch

    U->>API: cv_load_model(task_type, model_name, model_path)
    API->>CV: POST /inference/models/load
    CV->>IE: new InferenceEngine(task_type, model_name, ...)
    IE->>GPU: Load model architecture + state_dict
    IE->>IE: Cache in model_registry
    CV-->>API: Model loaded

    U->>API: cv_infer(image_url)
    API->>CV: POST /inference/process_image
    CV->>IE: process_frame(frame)
    IE->>GPU: Forward pass
    GPU-->>IE: Predictions
    IE-->>CV: Annotated image + results
    CV-->>API: {annotated_image_base64, predictions}
    API-->>U: Inference result
```

### 5.5 Segmentation Dataset Formats

| Format | Detection Method | Handler Class |
|---|---|---|
| **COCO** | `_annotations.coco.json` present | `CocoSegmentationDataset` |
| **Binary** | `images/` + `masks/` dirs | `BinarySegmentationDataset` |
| **Multiclass** | `labels.txt` file present | `MulticlassSegmentationDataset` |

### 5.6 GPU Requirements

| Mode | Requirement | Configuration |
|---|---|---|
| **CPU Training** | Default `cv-service` container | Slower, no GPU needed |
| **GPU Training** | `cv-service-gpu` + NVIDIA Container Toolkit | `CUDA_VISIBLE_DEVICES=0`, `driver: nvidia`, `count: 1` |
| **Inference** | Auto-detects via `torch.cuda.is_available()` | Falls back to CPU if no GPU |

---

## 6. ML Training Pipeline (scikit-learn)

The ML pipeline runs **inside WarpCore** (no separate microservice). It uses scikit-learn and CatBoost for tabular data.

```mermaid
graph TB
    subgraph "ML Pipeline (warpcore/app/services/ml/)"
        direction TB
        UPLOAD["Upload Dataset<br/>(CSV/JSON → S3)"]
        PREP["Preprocessing<br/>(handle missing, encode,<br/>scale, feature selection)"]
        ALGO["Algorithm Registry<br/>(algorithms.py)"]
        TRAIN["Trainer<br/>(trainer.py)"]
        SAVE["Save Model<br/>(joblib → S3)"]
        PREDICT["Predict<br/>(load from S3, run inference)"]
    end

    subgraph "Supervised Algorithms"
        LR["Logistic Regression"]
        RFC["Random Forest Classifier"]
        SVC["SVM Classifier"]
        GBC["Gradient Boosting"]
        ABC["AdaBoost"]
        CBC["CatBoost Classifier"]
        LINR["Linear Regression"]
        RFR["Random Forest Regressor"]
        SVR2["SVM Regressor"]
        GBR["Gradient Boosting Regressor"]
        ABR["AdaBoost Regressor"]
        CBR["CatBoost Regressor"]
    end

    subgraph "Unsupervised Algorithms"
        KM["K-Means"]
        DBS["DBSCAN"]
        PCA2["PCA"]
    end

    UPLOAD --> PREP --> ALGO --> TRAIN --> SAVE
    SAVE --> PREDICT
    ALGO --> LR & RFC & SVC & GBC & ABC & CBC
    ALGO --> LINR & RFR & SVR2 & GBR & ABR & CBR
    ALGO --> KM & DBS & PCA2
```

### ML Data Flow

```mermaid
sequenceDiagram
    participant U as User / Agent
    participant API as ML Router
    participant S3 as AWS S3
    participant DB as PostgreSQL
    participant T as Trainer

    U->>API: Upload CSV dataset
    API->>S3: Store file (datasets/{id}.csv)
    API->>DB: Insert MLDataset record
    API-->>U: dataset_id

    U->>API: Train model (dataset_id, algorithm, target_col)
    API->>S3: Download dataset
    API->>T: preprocess → split → train
    T->>T: fit model (scikit-learn/CatBoost)
    T->>T: Evaluate (accuracy, F1, MSE, R², etc.)
    T->>S3: Upload model (models/{id}.joblib)
    T->>DB: Insert MLModel record
    API-->>U: {model_id, metrics}

    U->>API: Predict (model_id, input_data)
    API->>S3: Download model
    API->>T: model.predict(input)
    API-->>U: predictions[]
```

---

## 7. Database Schema (Supabase PostgreSQL)

```mermaid
erDiagram
    User {
        UUID id PK
        string email UK
        string name
        string hashed_password
        string auth_provider
        string google_id UK
        string avatar_url
        bool is_active
        datetime created_at
        datetime updated_at
    }

    Workflow {
        UUID id PK
        UUID owner_id FK
        string name
        text description
        bool is_active
        JSONB nodes
        JSONB connections
        JSONB viewport
        datetime created_at
        datetime updated_at
    }

    NodeTemplate {
        string id PK
        string name
        string icon
        string color
        string category
        text description
        JSONB default_data
        bool is_active
    }

    Credential {
        UUID id PK
        UUID owner_id FK
        string type
        string name
        text client_id
        text client_secret
        text access_token
        text refresh_token
        datetime token_expiry
    }

    UserSecret {
        UUID id PK
        UUID owner_id FK
        string secret_key
        text encrypted_value
        datetime created_at
        datetime updated_at
    }

    MLDataset {
        UUID id PK
        UUID owner_id FK
        string name
        text s3_path
        string file_type
        int row_count
        JSONB columns
    }

    MLModel {
        UUID id PK
        UUID owner_id FK
        UUID dataset_id FK
        string name
        string algorithm
        string model_type
        string model_category
        text s3_path
        JSONB metrics
        JSONB feature_names
        JSONB hyperparameters
    }

    ContextCollection {
        UUID id PK
        UUID owner_id FK
        string name
        int document_count
        int chunk_count
    }

    ContextDocument {
        UUID id PK
        UUID collection_id FK
        string filename
        string file_type
        int chunk_count
        text s3_path
    }

    User ||--o{ Workflow : owns
    User ||--o{ Credential : owns
    User ||--o{ UserSecret : owns
    User ||--o{ MLDataset : owns
    User ||--o{ MLModel : owns
    User ||--o{ ContextCollection : owns
    MLModel }o--|| MLDataset : trained_on
    ContextDocument }o--|| ContextCollection : belongs_to
```

### DB Connection Details
- **Driver:** `asyncpg` (async) / `psycopg2` (sync for Alembic)
- **Pool:** `NullPool` (no connection pooling — relies on Supabase's PgBouncer)
- **Host:** `aws-1-ap-south-1.pooler.supabase.com:6543`
- **Migrations:** Alembic

---

## 8. Storage Architecture

```mermaid
graph TB
    subgraph "S3 Storage (warpflow-storage)"
        DS["datasets/{id}.csv"]
        MO["models/{id}.joblib"]
        DOC["documents/{id}.pdf"]
    end

    subgraph "ChromaDB (Local Persistent)"
        VC["Per-user collections<br/>storage/chromadb/{user_id}/"]
        EMB["Embeddings (all-MiniLM-L6-v2)"]
    end

    subgraph "Shared Docker Volume"
        CVM["cv-models volume<br/>/app/cv_models ↔ /app/training/saved_models"]
        DSV["./datasets bind mount"]
    end

    API["WarpCore API"] -->|"boto3"| DS & MO & DOC
    API -->|"chromadb.PersistentClient"| VC
    API -->|"sentence-transformers"| EMB
    CV["CV Service"] -->|"torch.save/load"| CVM
    CV -->|"os.path"| DSV
```

### S3 Access Patterns
1. **Server-level S3:** Default credentials from `.env` (`S3_ACCESS_KEY`, `S3_SECRET_KEY`)
2. **Per-user S3:** User stores credentials in `UserSecret` → decrypted at runtime → separate boto3 client
3. **Agent S3 tools:** User provides AWS creds as JSON in node config → `s3_service.py` builds boto3 client

---

## 9. Context Store (RAG Pipeline)

```mermaid
sequenceDiagram
    participant U as User
    participant API as Context Router
    participant PDF as PDF Processor
    participant EMB as Sentence Transformers
    participant VS as ChromaDB Vector Store
    participant DB as PostgreSQL

    U->>API: Upload document (PDF/TXT/MD)
    API->>PDF: Extract & chunk text
    PDF-->>API: chunks[]
    API->>EMB: Encode chunks (all-MiniLM-L6-v2)
    EMB-->>API: embeddings[]
    API->>VS: add_documents(ids, texts, embeddings, metadatas)
    API->>DB: Insert ContextCollection + ContextDocument
    API-->>U: {collection_id, chunk_count}

    U->>API: Query (text, collection, top_k)
    API->>EMB: Encode query
    API->>VS: query(embedding, top_k)
    VS-->>API: [{content, metadata, score}]
    API-->>U: Relevant chunks
```

---

## 10. Frontend Architecture (WarpFlow)

| Layer | Technology |
|---|---|
| **Framework** | React 18 + TypeScript |
| **Build Tool** | Vite |
| **Styling** | Tailwind CSS |
| **State** | React Context API |
| **Routing** | React Router |

### Key Pages & Components

| File | Purpose |
|---|---|
| `WorkFlowBuilder.tsx` (45KB) | Main canvas — drag-and-drop node editor |
| `ExecuteModal.tsx` | Workflow execution dialog with real-time step display |
| `NodeConfigModal.tsx` | Per-node configuration panel |
| `WorkflowSelector.tsx` | Sidebar workflow list + CRUD |
| `AuthPage.tsx` | Login / Signup with Google OAuth |
| `ProtectedRoute.tsx` | Auth guard component |

---

## 11. Node Template Catalog (77+ nodes)

| Category | Node Types |
|---|---|
| **Triggers** | Manual, Schedule, Webhook, Email Trigger |
| **AI & ML** | OpenAI, Gemini, Anthropic, HuggingFace, AI Agent, ML Trainer, Context Store, ElevenLabs TTS, Text Analysis, Image Gen |
| **Communication** | Slack, Discord, Teams, Telegram, Email, SMS, Twilio |
| **Data & Storage** | PostgreSQL, MongoDB, Redis, MySQL, Google Sheets, Airtable, CSV |
| **Logic & Flow** | IF Condition, Switch, Loop, Merge, Split, Wait |
| **Data Processing** | Transform, Filter, Aggregate, Sort, JSON |
| **APIs & Services** | HTTP, REST API, GraphQL, Stripe, GitHub, AWS |
| **Analytics** | Google Analytics, Mixpanel, Segment |
| **Google Workspace** | Docs, Drive, Gmail, Sheets, Forms |

---

## 12. Security & Authentication

```mermaid
graph LR
    subgraph "Auth Flow"
        EMAIL["Email + Password<br/>(bcrypt hashing)"]
        GOOGLE["Google OAuth 2.0<br/>(PKCE flow)"]
    end

    subgraph "Token Management"
        JWT["JWT Access Token<br/>(HS256, 24h expiry)"]
        CSRF["CSRF Token<br/>(X-CSRF-Token header)"]
        COOKIE["HTTP-Only Cookie<br/>(access_token)"]
    end

    subgraph "Secret Storage"
        US["UserSecret table<br/>(Fernet-encrypted values)"]
    end

    EMAIL & GOOGLE --> JWT --> COOKIE
    JWT --> CSRF
    US -->|"decrypt_value()"| API["Service Functions"]
```

- **Rate Limiting:** SlowAPI (`20/min` for execution, `60/min` for external triggers)
- **CORS:** Restricted to `FRONTEND_URL` only
- **Credentials:** OAuth tokens stored in `Credential` table; API keys in `UserSecret` (Fernet-encrypted)
