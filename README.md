<div align="center">

# 🕵️‍♂️ SPECTER: See Beyond Blockchain
### Automated Multi-Chain Crypto Tracing & VASP Attribution Engine for Law Enforcement

[![SIH 2026](https://img.shields.io/badge/SIH%202026-Problem%20SIH26182-orange.svg?style=for-the-badge)](https://www.sih.gov.in/)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-success?style=for-the-badge&logo=vercel)](https://specter-beige.vercel.app/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%7C%20TypeScript%20%7C%20Vite-61DAFB?style=for-the-badge&logo=react)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20SQLAlchemy-336791?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

**"From an Unknown Wallet to an Actionable VASP Notice."**
Reconstructing multi-hop illicit fund trails, attributing destination VASPs with mathematical confidence scoring, and packaging court-admissible evidence for the **MHA I4C / SAHYOG Portal**.

[🌐 Live Prototype](https://specter-beige.vercel.app/) • [📖 System Architecture](#-system-architecture) • [🚀 Getting Started](#-getting-started) • [📊 Scoring Model](#-evidence-based-vasp-attribution) • [📑 Academic References](#-academic-references)

---

</div>

## 📌 Problem Statement (SIH26182)

* **Problem Statement ID:** `SIH26182`
* **Title:** Automated Attribution of Unknown Cryptocurrency Wallets to Nearest Virtual Asset Service Providers (VASPs) through Blockchain Intelligence APIs (SAHYOG Portal Integration)
* **Target Stakeholders:** Indian Cyber Crime Coordination Centre (I4C), Ministry of Home Affairs (MHA), State Cyber Crime Cells, Law Enforcement Agencies (LEAs), and Financial Regulators.
* **Team:** VeroAI *(Team ID: 146040)*

### The Core Operational Challenge
In financial cyber fraud (pig butchery, fake trading apps, ransomware, drug syndicates), victims deposit funds into an unhosted criminal wallet. The illicit money is rapidly fragmented through layers of intermediary wallets before being deposited into a centralized Virtual Asset Service Provider (VASP) for fiat off-ramping.

Manual tracking via public block explorers takes **hours or days per case**, requires dozen of open browser tabs, and fails to systematically differentiate between intermediary hops, bridge contracts, and deposit clusters. By the time a lawful disclosure request is manually filed, the funds have already been liquidated.

---

## ⚡ The SPECTER Solution

SPECTER replaces manual ad-hoc explorer searches with an end-to-end, automated investigative pipeline:

[ Unidentified Suspect Wallet ]
               │
               ▼
[ 1. Multi-Hop Tracing Engine ]  ───► Normalizes Account & UTXO models (TRON, ETH, BTC, SOL)
               │
               ▼
[ 2. Graph & Typology (EGRE) ]   ───► Detects peel chains, rapid consolidation, layering
               │
               ▼
[ 3. VASP Attribution Engine ]   ───► Matches destination deposit clusters with confidence scores
               │
               ▼
[ 4. Evidence Graph Packaging ]  ───► Preserves complete cryptographic chain of custody (tx hashes, hops)
               │
               ▼
[ 5. SAHYOG & Section 94 Notice ]───► Instant court-admissible PDF reports & JSON/CSV dispatch packages

---

## 🏛️ System Architecture

flowchart TB
%%{init: {
  "theme": "dark",
  "themeVariables": {
    "fontSize": "13px",
    "fontFamily": "Inter, Segoe UI, sans-serif",
    "primaryColor": "#1e293b",
    "primaryTextColor": "#f8fafc",
    "primaryBorderColor": "#6366f1",
    "lineColor": "#94a3b8",
    "secondaryColor": "#0f172a",
    "tertiaryColor": "#1e1e38"
  },
  "flowchart": {
    "curve": "basis",
    "nodeSpacing": 45,
    "rankSpacing": 55,
    "htmlLabels": true
  }
}}%%

  %% =========================================================================
  %% SUBGRAPH 1: FRONTEND PRESENTATION & INVESTIGATION WORKBENCH (React + TS)
  %% =========================================================================
  subgraph FRONTEND ["Layer 1: Frontend Investigation Workbench (React 18 + Vite + Cytoscape)"]
    direction TB
    UI_App["App.tsx<br/><i>Workbench Controller & State Container</i>"]
    UI_Navbar["Navbar.tsx<br/><i>Header & Chain Status Telemetry</i>"]
    UI_Input["InvestigationInput.tsx<br/><i>Target Wallet, Regex Validation & Hops</i>"]
    UI_StatusBar["InvestigationStatusBar.tsx<br/><i>13-Stage Real-Time Pipeline Tracker</i>"]
    UI_ResultReveal["PrimaryResultReveal.tsx<br/><i>Attributed VASP & High-Level Risk Score</i>"]
    UI_Cytoscape["FundFlowGraph.tsx<br/><i>Cytoscape.js Directed Graph (Dagre Layout)</i>"]
    UI_PathExplorer["PathExplorer.tsx<br/><i>Hop-by-Hop Tree & Value Retention</i>"]
    UI_Inspector["SelectedInspector.tsx<br/><i>Node/Edge Context & Wallet Intel Inspector</i>"]
    UI_RiskPanel["RiskBreakdownPanel.tsx<br/><i>EGRE 6-Dimension Breakdown & Radar</i>"]
    UI_TypologyPanel["TypologyPanel.tsx<br/><i>Structural Alert Cards (Fan-Out/Peeling)</i>"]
    UI_VelocityPanel["VelocityAlertsPanel.tsx<br/><i>Rapid Transit & Delta-t Windows</i>"]
    UI_VaspCard["VaspAttributionCard.tsx<br/><i>Top-1/Top-3 VASP Candidates & Ledger</i>"]
    UI_Evidence["EvidenceDrawer.tsx / EvidenceExplorer.tsx<br/><i>Cryptographic Evidence Chain & Hash Audit</i>"]
    UI_Sahyog["SahyogActionCenter.tsx<br/><i>Sec 91 CrPC, Freeze & Disclosure Actions</i>"]
    UI_Reports["ReportsExportPanel.tsx<br/><i>Court-Ready PDF, CSV & JSON Bundles</i>"]
    UI_ApiClient["services/api.ts<br/><i>Axios REST Client with Multi-Endpoint Mapping</i>"]

    UI_App --> UI_Navbar
    UI_App --> UI_Input
    UI_App --> UI_StatusBar
    UI_App --> UI_ResultReveal
    UI_App --> UI_Cytoscape
    UI_App --> UI_PathExplorer
    UI_App --> UI_Inspector
    UI_App --> UI_RiskPanel
    UI_App --> UI_TypologyPanel
    UI_App --> UI_VelocityPanel
    UI_App --> UI_VaspCard
    UI_App --> UI_Evidence
    UI_App --> UI_Sahyog
    UI_App --> UI_Reports
    UI_App --> UI_ApiClient
  end

  %% =========================================================================
  %% SUBGRAPH 2: FASTAPI GATEWAY & ROUTE CONTROLLERS
  %% =========================================================================
  subgraph API_GATEWAY ["Layer 2: REST API Gateway & Route Controllers (FastAPI)"]
    direction TB
    API_Main["app/main.py<br/><i>FastAPI App, CORS & Lifespan</i>"]
    API_Router["app/api/router.py<br/><i>Consolidated /api/v1 Router</i>"]

    EP_Health["endpoints/health.py<br/><i>GET /health</i>"]
    EP_Cases["endpoints/cases.py<br/><i>POST/GET /cases, GET /cases/{id}</i>"]
    EP_Investigation["endpoints/investigation.py<br/><i>POST /investigation/start<br/>GET /jobs/{id}<br/>GET /cases/{id}/summary<br/>GET /cases/{id}/report.pdf<br/>GET /cases/{id}/dataset</i>"]
    EP_Trace["endpoints/trace.py<br/><i>POST /trace/execute<br/>GET /trace/{id}</i>"]
    EP_Patterns["endpoints/patterns.py<br/><i>POST /patterns/trace/analyze<br/>GET /velocity, /typologies, /risk</i>"]
    EP_Vasp["endpoints/vasp.py<br/><i>POST /vasp/attribution/resolve<br/>GET /candidates, /lookup/{address}</i>"]
    EP_Intel["endpoints/intelligence.py<br/><i>GET /entity/{addr}, /cross-chain<br/>GET /vasp-cluster/{name}</i>"]
    EP_Sahyog["endpoints/sahyog.py<br/><i>GET /sahyog/package<br/>POST /disclosure-request, /freeze-request</i>"]

    API_Main --> API_Router
    API_Router --> EP_Health
    API_Router --> EP_Cases
    API_Router --> EP_Investigation
    API_Router --> EP_Trace
    API_Router --> EP_Patterns
    API_Router --> EP_Vasp
    API_Router --> EP_Intel
    API_Router --> EP_Sahyog
  end

  UI_ApiClient ==>|HTTP / JSON Requests| API_Router

  %% =========================================================================
  %% SUBGRAPH 3: 13-STAGE INVESTIGATION ORCHESTRATOR
  %% =========================================================================
  subgraph ORCHESTRATION ["Layer 3: Core Pipeline Orchestrator (InvestigationOrchestrator)"]
    direction TB
    Orchestrator["InvestigationOrchestrator (app/investigation/orchestrator.py)<br/><i>State Machine Manager, Parameter Freezing & Snapshots</i>"]

    subgraph STAGES ["Deterministic 13-Stage Pipeline Execution Flow"]
      direction TB
      S01["Stage 1: VALIDATING (5%)<br/><i>Syntax Check & Address Regex</i>"]
      S02["Stage 2: INGESTING (15%)<br/><i>Data Sync via Adapter Pool</i>"]
      S03["Stage 3: TRACING (35%)<br/><i>BFS/DFS Graph Traversal</i>"]
      S04["Stage 4: GRAPH_ANALYSIS (50%)<br/><i>Topology Snapshot & Pruning</i>"]
      S05["Stage 5: PATTERN_ANALYSIS (65%)<br/><i>Velocity, Typologies & EGRE Engine</i>"]
      S06["Stage 6: VASP_RESOLUTION (80%)<br/><i>Exact Match, Cluster & Heuristics</i>"]
      S07["Stage 7: EVIDENCE_BUILDING (90%)<br/><i>Structured Evidence Graph & Findings</i>"]
      S08["Stage 8: REPORT_GENERATION (95%)<br/><i>ReportLab Court-Ready PDF</i>"]
      S09["Stage 9: PACKAGE_GENERATION (98%)<br/><i>SAHYOG LEA Submission Archive</i>"]
      S10["Stage 10: COMPLETED (100%)<br/><i>Final State, DB Commit & Export</i>"]
      S_FAIL["Terminal: FAILED / ROLLBACK<br/><i>Audit Fault Logging & Rollback</i>"]

      S01 --> S02 --> S03 --> S04 --> S05 --> S06 --> S07 --> S08 --> S09 --> S10
      S01 -.->|Validation Error| S_FAIL
      S03 -.->|RPC / Data Error| S_FAIL
      S05 -.->|Analytics Error| S_FAIL
      S06 -.->|VASP Resolution Error| S_FAIL
    end

    Orchestrator --> STAGES
  end

  EP_Investigation ==>|trigger investigation| Orchestrator

  %% =========================================================================
  %% SUBGRAPH 4: MULTI-CHAIN INGESTION & BLOCKCHAIN ADAPTERS
  %% =========================================================================
  subgraph BLOCKCHAIN ["Layer 4: Multi-Chain Ingestion & Blockchain Adapters"]
    direction TB
    ChainRegistry["ChainRegistry (app/blockchain/registry.py)<br/><i>Factory, Multi-Chain Router & Address Validator</i>"]
    BC_Adapter["BlockchainAdapter (app/blockchain/adapters/base.py)<br/><i>Abstract Base Class: fetch, normalize, persist</i>"]

    TronAd["TronAdapter (app/blockchain/adapters/tron.py)<br/><i>TronGrid REST API, TRC-20 USDT, Base58</i>"]
    BtcAd["BitcoinAdapter (app/blockchain/adapters/bitcoin.py)<br/><i>Mempool.space API, UTXO vin/vout, Satoshis</i>"]
    EthAd["EthereumAdapter (app/blockchain/adapters/ethereum.py)<br/><i>Etherscan / EVM JSON-RPC, ERC-20 Logs</i>"]
    PolyAd["PolygonAdapter (app/blockchain/adapters/polygon.py)<br/><i>Polygonscan API, PoS Transfer Logs</i>"]
    BnbAd["BnbAdapter (app/blockchain/adapters/bnb.py)<br/><i>BscScan API, BEP-20 Transfer Logs</i>"]
    SolAd["SolanaAdapter (app/blockchain/adapters/solana.py)<br/><i>Solscan API / Solana RPC, SPL Tokens</i>"]

    ChainRegistry --> BC_Adapter
    BC_Adapter -->|implements| TronAd
    BC_Adapter -->|implements| BtcAd
    BC_Adapter -->|implements| EthAd
    BC_Adapter -->|implements| PolyAd
    BC_Adapter -->|implements| BnbAd
    BC_Adapter -->|implements| SolAd

    Ext_TronGrid[("TronGrid Node / API")]
    Ext_Mempool[("Mempool.space API")]
    Ext_Etherscan[("Etherscan / EVM RPC")]
    Ext_BscScan[("BscScan API")]
    Ext_Polygonscan[("Polygonscan API")]
    Ext_Solscan[("Solscan / Solana RPC")]

    TronAd --- Ext_TronGrid
    BtcAd --- Ext_Mempool
    EthAd --- Ext_Etherscan
    BnbAd --- Ext_BscScan
    PolyAd --- Ext_Polygonscan
    SolAd --- Ext_Solscan
  end

  S01 -->|validate_address_for_chain| ChainRegistry
  S02 -->|fetch and normalize| ChainRegistry

  %% =========================================================================
  %% SUBGRAPH 5: MULTI-HOP TRACING ENGINE
  %% =========================================================================
  subgraph TRACING_ENGINE ["Layer 5: Graph Traversal & Multi-Hop Tracing Engine"]
    direction TB
    TraceEngine["TraceEngine (app/tracing/engine.py)<br/><i>Multi-Hop BFS/DFS Directed Fund-Flow Traversal</i>"]
    CycleDet["CycleDetector<br/><i>Visited Address Tracker, Anti-Loop Filter</i>"]
    FlowFilter["FlowFilter<br/><i>Threshold Pruning: min_transfer_amount, % flow</i>"]
    PathBuilder["PathBuilder<br/><i>_build_path_detail, _calculate_relevance_score</i>"]
    TraceResult["TraceResultResponse (Schema)<br/><i>Hops, Paths, Wallets Discovered, Value Retention</i>"]

    TraceEngine --> CycleDet
    TraceEngine --> FlowFilter
    TraceEngine --> PathBuilder
    PathBuilder --> TraceResult
  end

  S03 ==>|execute_trace| TraceEngine
  TraceEngine -->|query transactions| ChainRegistry

  %% =========================================================================
  %% SUBGRAPH 6: ANALYTICAL INTELLIGENCE ENGINES
  %% =========================================================================
  subgraph ANALYTICS ["Layer 6: Analytical Intelligence & Risk Engines"]
    direction TB

    %% Velocity Subsystem
    subgraph VELOCITY_SYSTEM ["Velocity Intelligence Subsystem"]
      direction TB
      VelService["VelocityService (app/velocity/service.py)"]
      VelDetector["VelocityDetector (app/velocity/detector.py)<br/><i>Delta-t Gaps, Rolling Windows: 1m, 5m, 10m, 30m, 1h</i>"]
      VelScorer["VelocityScorer (app/velocity/scorer.py)<br/><i>Rapid Transit Score & Severity Bands</i>"]
      VelBuilder["VelocityEvidenceBuilder (app/velocity/evidence.py)<br/><i>Reason Codes & Explanations</i>"]
      VelResp["VelocityAnalysisResponse (Schema)"]

      VelService --> VelDetector
      VelService --> VelScorer
      VelService --> VelBuilder
      VelBuilder --> VelResp
    end

    %% Typology Subsystem
    subgraph TYPOLOGY_SYSTEM ["Typology Detection Subsystem"]
      direction TB
      TypService["TypologyService (app/typologies/service.py)"]
      TypDetector["TypologyDetector (app/typologies/detector.py)<br/><i>Fan-Out, Fan-In, Peeling Chain,<br/>Consolidation, U-Turn, Structuring</i>"]
      TypScorer["TypologyScorer (app/typologies/scorer.py)<br/><i>Pattern Confidence & Magnitude Weights</i>"]
      TypBuilder["TypologyEvidenceBuilder (app/typologies/evidence.py)<br/><i>Structural Typology Ledger</i>"]
      TypResp["TypologyAnalysisResponse (Schema)"]

      TypService --> TypDetector
      TypService --> TypScorer
      TypService --> TypBuilder
      TypBuilder --> TypResp
    end

    %% EGRE Subsystem
    subgraph EGRE_SYSTEM ["Explainable Graph Risk Engine (EGRE V1)"]
      direction TB
      EGRE["ExplainableGraphRiskEngine (app/intelligence/risk_engine.py)"]
      RiskService["RiskService (app/risk/service.py)"]

      subgraph DIMENSIONS ["6 Capped Risk Dimensions"]
        D1["Dim 1: Structural Patterns (Cap: 25)"]
        D2["Dim 2: Rapid Velocity (Cap: 20)"]
        D3["Dim 3: High-Risk VASP Interaction (Cap: 20)"]
        D4["Dim 4: Cross-Chain Bridges (Cap: 15)"]
        D5["Dim 5: Mixer / Privacy Pools (Cap: 20)"]
        D6["Dim 6: Volume / Transfer Magnitude (Cap: 10)"]
      end

      ContextDamp["Contextual Normalizer<br/><i>Known Regulated Service Entity Dampening</i>"]
      RiskResp["RiskIndicatorResponse (Schema)<br/><i>Raw Score, Contextual Score & Indicators</i>"]

      RiskService --> EGRE
      EGRE --> DIMENSIONS
      DIMENSIONS --> ContextDamp
      ContextDamp --> RiskResp
    end

    %% Intelligence & Classification
    subgraph CLASSIFICATION_SYSTEM ["Entity Classification & Network Intel"]
      direction TB
      WalletClassifier["WalletRoleClassifier (app/intelligence/classifier.py)<br/><i>Deposit, Hot, Cold, Mixer, Bridge, Scam</i>"]
      CrossChain["CrossChainIntelligenceEngine (app/intelligence/cross_chain.py)<br/><i>Bridge & Multi-Chain Transfer Links</i>"]
      MixerIntel["MixerIntelligenceEngine (app/intelligence/mixer.py)<br/><i>Privacy Pool Signatures: Tornado, SunPump</i>"]
      SourceReg["SourceRegistry (app/sources/registry.py)<br/><i>Provenance & Intelligence Weighting</i>"]
    end
  end

  S05 ==>|analyze_trace| VelService
  S05 ==>|analyze_trace| TypService
  S05 ==>|analyze_trace| RiskService
  TraceResult -.-> VelService
  TraceResult -.-> TypService
  TraceResult -.-> RiskService
  RiskService --> CrossChain
  RiskService --> MixerIntel
  RiskService --> WalletClassifier

  %% =========================================================================
  %% SUBGRAPH 7: VASP ATTRIBUTION ENGINE
  %% =========================================================================
  subgraph VASP_ENGINE ["Layer 7: VASP Attribution & Entity Resolution Engine"]
    direction TB
    VASPService["VASPService (app/vasp/service.py)<br/><i>End-to-End Attribution Coordinator</i>"]
    VASPRepo["VASPRepository (app/vasp/repository.py)<br/><i>Verified Seed Intelligence: Binance, Bybit, etc.</i>"]
    VASPMatcher["VASPMatcher (app/vasp/matcher.py)<br/><i>Exact Lookup, Cluster Discovery, Sweep Heuristics</i>"]
    VASPScorer["VASPScorer (app/vasp/scorer.py)<br/><i>Scoring Model: High 80-100, Med 50-79, Low 0-49</i>"]
    VASPEvidence["VASPEvidenceBuilder (app/vasp/evidence.py)<br/><i>Conservative Grounded 'Why This VASP' Ledger</i>"]
    VASPResp["VASPAttributionResponse (Schema)<br/><i>Top-1/Top-3 Attributed Candidates & Confidence</i>"]

    VASPService --> VASPRepo
    VASPService --> VASPMatcher
    VASPService --> VASPScorer
    VASPService --> VASPEvidence
    VASPEvidence --> VASPResp
  end

  S06 ==>|resolve_from_trace_result| VASPService
  TraceResult -.-> VASPService

  %% =========================================================================
  %% SUBGRAPH 8: EVIDENCE, REPORTING & SAHYOG PORTAL HANDOVER
  %% =========================================================================
  subgraph EVIDENCE_REPORTING ["Layer 8: Evidence Ledger, Court-Ready Reports & SAHYOG LEA Integration"]
    direction TB
    EvBuilder["EvidenceBuilder (app/evidence/builder.py)<br/><i>Synthesizes Findings, Graph Edges & Provenance</i>"]
    PDFGen["PDFReportGenerator (app/reporting/pdf_generator.py)<br/><i>ReportLab Court-Ready PDF (Section 91 CrPC Ready)</i>"]
    DataExp["DataExporter (app/export/exporters.py)<br/><i>Exports Multi-Dataset JSON, CSVs & ZIP Package</i>"]

    subgraph SAHYOG_INTEGRATION ["SAHYOG National LEA Portal Integration"]
      direction TB
      SahyogAd["SahyogAdapter (app/sahyog/adapter.py)<br/><i>Bharat Cyber Coordination Centre (I4C) Protocol</i>"]
      SahyogTrans["LocalPackageTransport / HTTPS Transport<br/><i>SHA-256 Digest & Digital Chain of Custody</i>"]
      Sec91Notice["Sec 91 CrPC Information Disclosure Request<br/><i>Target VASP, KYC, IP, Login & Bank Accounts</i>"]
      FreezeReq["Asset Preservation / Freezing Request<br/><i>Urgent Seizure Order with Audit Trail</i>"]

      SahyogAd --> SahyogTrans
      SahyogAd --> Sec91Notice
      SahyogAd --> FreezeReq
    end
  end

  S07 ==>|build_evidence_graph_and_findings| EvBuilder
  S08 ==>|generate_pdf_report| PDFGen
  S09 ==>|build_sahyog_package| SahyogAd
  S09 ==>|export_all| DataExp

  VelResp -.-> EvBuilder
  TypResp -.-> EvBuilder
  RiskResp -.-> EvBuilder
  VASPResp -.-> EvBuilder

  EvBuilder -.-> PDFGen
  EvBuilder -.-> SahyogAd

  %% =========================================================================
  %% SUBGRAPH 9: DATABASE PERSISTENCE LAYER (SQLAlchemy ORM)
  %% =========================================================================
  subgraph DATABASE ["Layer 9: Relational Persistence Layer (SQLAlchemy ORM + SQLite/Postgres)"]
    direction TB
    DB_Session["app/core/database.py<br/><i>SQLAlchemy Session & Engine Factory</i>"]

    subgraph ORM_MODELS ["Database Entities & Relationship Tables"]
      direction TB
      M_Case[("Case<br/><i>case_id, investigator_id, reported_wallet, chain, asset, status</i>")]
      M_Job[("InvestigationJob<br/><i>job_id, progress_percent, current_stage, snapshot_params</i>")]
      M_Snapshot[("InvestigationSnapshot<br/><i>snapshot_id, trace_graph_snapshot, engine_version</i>")]
      M_TraceRun[("TraceRun<br/><i>trace_id, starting_wallet, max_hops, total_transfers</i>")]
      M_TracePath[("TracePath<br/><i>path_id, hop_count, total_value, cycle_flag</i>")]
      M_TraceNode[("TraceNode<br/><i>wallet_address, cluster_tag, role_tag</i>")]
      M_TraceEdge[("TraceEdge<br/><i>tx_hash, from_addr, to_addr, amount, delta_t</i>")]
      M_Tx[("NormalizedTransaction<br/><i>canonical tx fields, fee, status, timestamp</i>")]
      M_Finding[("Finding<br/><i>finding_id, finding_type, severity, confidence</i>")]
      M_Evidence[("EvidenceItem<br/><i>evidence_id, source_id, tx_hashes, addresses</i>")]
      M_Alert[("Alert<br/><i>alert_type, severity, trigger_metric, delta_t</i>")]
      M_VASP[("VASPRecord<br/><i>entity_name, service_type, address, is_regulated</i>")]
      M_Sahyog[("SahyogRequest<br/><i>request_id, vasp_name, request_type, sha256_hash</i>")]
      M_Risk[("RiskAssessmentRecord<br/><i>risk_score, raw_score, contextual_score, level</i>")]
    end

    DB_Session --> ORM_MODELS
    M_Case --> M_Job
    M_Job --> M_Snapshot
    M_Case --> M_TraceRun
    M_TraceRun --> M_TracePath
    M_TraceRun --> M_TraceNode
    M_TraceRun --> M_TraceEdge
    M_Case --> M_Finding
    M_Finding --> M_Evidence
    M_Case --> M_Alert
    M_Case --> M_Sahyog
    M_Case --> M_Risk
  end

  Orchestrator -->|Persist Case & Job State| M_Case
  TraceEngine -->|Persist Graph Topology| M_TraceRun
  BC_Adapter -->|Persist Ingested Txs| M_Tx
  EvBuilder -->|Persist Findings & Evidence| M_Finding
  EvBuilder -->|Persist Evidence Items| M_Evidence
  VelService -->|Persist Velocity Alerts| M_Alert
  TypService -->|Persist Typology Alerts| M_Alert
  VASPService -->|Query & Cache VASP Intelligence| M_VASP
  SahyogAd -->|Record Audit Log & Requests| M_Sahyog
  RiskService -->|Store Risk Calculations| M_Risk

  %% =========================================================================
  %% SUBGRAPH 10: BENCHMARK & EVALUATION FRAMEWORK
  %% =========================================================================
  subgraph EVALUATION ["Layer 10: Scientific Evaluation & Benchmark Framework"]
    direction TB
    EvalFramework["EvaluationFramework (app/evaluation/framework.py)<br/><i>Complete System Evaluation Pipeline</i>"]
    BaselineComp["BaselineComparator (app/evaluation/baseline_comparison.py)<br/><i>Automated vs Manual LEA Investigation Speedup</i>"]
    VaspEval["VASPAccuracyEvaluator (app/evaluation/vasp_accuracy.py)<br/><i>Top-1 / Top-3 Attribution Accuracy on Ground Truth</i>"]
    VelocityEval["VelocityEvaluator (app/evaluation/velocity_metrics.py)<br/><i>Delta-t Calculation Precision & Rapid Hop Benchmark</i>"]

    EvalFramework --> BaselineComp
    EvalFramework --> VaspEval
    EvalFramework --> VelocityEval
  end

  EvalFramework -.->|Evaluates Pipeline Output| S10

  %% =========================================================================
  %% STYLING AND COLOR CODES
  %% =========================================================================
  classDef uiLayer fill:#1e1b4b,stroke:#818cf8,color:#f8fafc,stroke-width:2px;
  classDef apiLayer fill:#14532d,stroke:#4ade80,color:#f8fafc,stroke-width:2px;
  classDef orchLayer fill:#701a75,stroke:#f472b6,color:#f8fafc,stroke-width:2px;
  classDef stageLayer fill:#3b0764,stroke:#c084fc,color:#f8fafc,stroke-width:1px;
  classDef chainLayer fill:#083344,stroke:#22d3ee,color:#f8fafc,stroke-width:2px;
  classDef traceLayer fill:#1e293b,stroke:#38bdf8,color:#f8fafc,stroke-width:2px;
  classDef intelLayer fill:#451a03,stroke:#fb923c,color:#f8fafc,stroke-width:2px;
  classDef vaspLayer fill:#172554,stroke:#60a5fa,color:#f8fafc,stroke-width:2px;
  classDef evLayer fill:#064e3b,stroke:#34d399,color:#f8fafc,stroke-width:2px;
  classDef dbLayer fill:#27272a,stroke:#a1a1aa,color:#f8fafc,stroke-width:1px;
  classDef evalLayer fill:#312e81,stroke:#a5b4fc,color:#f8fafc,stroke-width:2px;

  class UI_App,UI_Navbar,UI_Input,UI_StatusBar,UI_ResultReveal,UI_Cytoscape,UI_PathExplorer,UI_Inspector,UI_RiskPanel,UI_TypologyPanel,UI_VelocityPanel,UI_VaspCard,UI_Evidence,UI_Sahyog,UI_Reports,UI_ApiClient uiLayer;
  class API_Main,API_Router,EP_Health,EP_Cases,EP_Investigation,EP_Trace,EP_Patterns,EP_Vasp,EP_Intel,EP_Sahyog apiLayer;
  class Orchestrator orchLayer;
  class S01,S02,S03,S04,S05,S06,S07,S08,S09,S10,S_FAIL stageLayer;
  class ChainRegistry,BC_Adapter,TronAd,BtcAd,EthAd,PolyAd,BnbAd,SolAd chainLayer;
  class TraceEngine,CycleDet,FlowFilter,PathBuilder,TraceResult traceLayer;
  class VelService,VelDetector,VelScorer,VelBuilder,TypService,TypDetector,TypScorer,TypBuilder,EGRE,RiskService,D1,D2,D3,D4,D5,D6,ContextDamp,WalletClassifier,CrossChain,MixerIntel,SourceReg intelLayer;
  class VASPService,VASPRepo,VASPMatcher,VASPScorer,VASPEvidence,VASPResp vaspLayer;
  class EvBuilder,PDFGen,DataExp,SahyogAd,SahyogTrans,Sec91Notice,FreezeReq evLayer;
  class DB_Session,M_Case,M_Job,M_Snapshot,M_TraceRun,M_TracePath,M_TraceNode,M_TraceEdge,M_Tx,M_Finding,M_Evidence,M_Alert,M_VASP,M_Sahyog,M_Risk dbLayer;
  class EvalFramework,BaselineComp,VaspEval,VelocityEval evalLayer;

---

## 🧩 Codebase Graph & Directory Structure

Specter/

├── app/

│   ├── api/

│   │   ├── endpoints/

│   │   │   ├── cases.py               # Case file management and lifecycle

│   │   │   ├── health.py              # System, DB, and blockchain provider health checks

│   │   │   ├── intelligence.py        # Entity and address classification queries

│   │   │   ├── investigation.py       # Async job runner & full case coordinator

│   │   │   ├── patterns.py            # Financial crime typology endpoints

│   │   │   ├── sahyog.py              # SAHYOG legal request & freeze package dispatch

│   │   │   ├── trace.py               # Multi-hop fund traversal endpoints

│   │   │   └── vasp.py                # VASP entity lookup & clustering queries

│   │   └── router.py                  # Consolidated FastAPI v1 router

│   ├── blockchain/

│   │   ├── adapters/

│   │   │   ├── base.py                # Abstract base blockchain connector

│   │   │   ├── bitcoin.py             # BTC adapter (UTXO co-spend & change heuristics)

│   │   │   ├── bnb.py                 # BNB Chain EVM adapter

│   │   │   ├── ethereum.py            # Ethereum ERC-20 & account transfer parser

│   │   │   ├── polygon.py             # Polygon POS adapter

│   │   │   ├── solana.py              # Solana SPL token & account parser

│   │   │   └── tron.py                # TRON TRC-20 (USDT) TronGrid adapter

│   │   └── registry.py                # Dynamic adapter resolver & factory

│   ├── core/

│   │   ├── config.py                  # Environment settings & API keys

│   │   ├── database.py                # SQLAlchemy ORM session factory

│   │   └── logging.py                 # Structured forensic logging

│   ├── evidence/

│   │   └── builder.py                 # Cryptographic chain of custody & evidence graph

│   ├── intelligence/

│   │   ├── classifier.py              # Address role classification (Deposit vs Hot vs Contract)

│   │   ├── cross_chain.py             # Cross-chain bridge & swap transition tracker

│   │   ├── mixer.py                   # Privacy mixer (Tornado Cash, etc.) interaction detector

│   │   └── risk_engine.py             # EGRE (Enhanced Graph Risk Engine)

│   ├── investigation/

│   │   └── orchestrator.py            # 5-stage automated investigation coordinator

│   ├── models/                        # SQLAlchemy database models

│   ├── reporting/

│   │   └── pdf_generator.py           # Automated Section 94 CrPC / BNSS forensic report generator

│   ├── sahyog/

│   │   └── adapter.py                 # Standardized MHA SAHYOG payload generator

│   └── main.py                        # FastAPI application entry point

├── frontend/                          # React + TypeScript Web Application

│   ├── src/

│   │   ├── components/                # Modular UI components (Graph, Inspector, Exports)

│   │   ├── services/                  # API client & mock datasets

│   │   ├── types/                     # TypeScript schema definitions

│   │   └── App.tsx                    # Master investigation dashboard

└── tests/                             # Comprehensive automated test suite

---

## 🎯 Key Differentiators

### 1. Evidence-Based VASP Attribution (No Overclaiming)
Commercial tools often guess or force an exchange name. SPECTER strictly adheres to an **evidence-first rule**:
* If evidence is strong (known deposit sweep heuristics + verified disclosure), it scores **100/100 (HIGH)**.
* If a path ends at an unhosted cold wallet or privacy protocol, it **explicitly outputs `No High-Confidence VASP Found`**.
* This eliminates false notices being served to exchanges, saving law enforcement crucial operational time.

### 2. Forensic Typology Detection (EGRE Engine)
The **Enhanced Graph Risk Engine (EGRE)** continuously evaluates fund dynamics along the traced path:
* **Rapid Consolidation:** Detecting victim fan-in transactions pooled into a single aggregator.
* **Structuring / Smurfing:** Identifying large amounts split into uniform sub-threshold amounts.
* **Peel Chains:** Identifying incremental peel-off transactions that keep forwarding primary value.
* **Dormancy & Burst:** Flagging addresses dormant for >180 days suddenly liquidating volume.

### 3. Native MHA SAHYOG & Legal Notice Integration
* Generates structured **Section 94 CrPC / BNSS** compliant legal notice packages.
* Formats transaction trails, cluster proofs, and target wallet identifiers into **MHA SAHYOG-ready JSON/CSV schemas** ready for direct inter-agency dispatch.

---

## 🔗 Supported Blockchains

| Network | Standard | Model | Implementation Status | Adapter Driver |
| :--- | :--- | :--- | :--- | :--- |
| **TRON** | TRC-20 (USDT) | Account | 🟢 **Live / Production** | TronGrid API / TronScan |
| **Ethereum** | ERC-20 / Native | Account | 🟡 **Implemented** | Etherscan v2 API |
| **Bitcoin** | Native BTC | UTXO | 🟡 **Implemented** | Blockstream / Mempool.space API |
| **Solana** | SPL Tokens | Account | 🟡 **Implemented** | Solana Web3 RPC |
| **Polygon** | ERC-20 / Native | Account | 🟡 **Implemented** | PolygonScan API |
| **BNB Chain** | BEP-20 / Native | Account | 🟡 **Implemented** | BscScan API |

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.10+**
* **Node.js 18+** & `npm`
* **PostgreSQL** (optional for production, SQLite supported out-of-the-box for local dev)

### 1. Clone the Repository
```bash
git clone https://github.com/sridharan0774/Specter.git
cd Specter

2. Backend Setup

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations / seed
python -c "from app.core.database import init_db; init_db()"

# Start the FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
API Documentation will be available at http://localhost:8000/docs.

3. Frontend Setup

cd frontend

# Install packages
npm install

# Start Vite development server
npm run dev
Open http://localhost:5173 in your browser.

---

🧪 Running Automated Tests

Run the test suite to verify multi-hop tracing, graph builders, and VASP attribution:
# Run all backend unit and integration tests
pytest tests/ -v

---

📚 Academic References

The heuristics, graph partitioning algorithms, and address clustering models used in SPECTER are based on peer-reviewed research:

1. Address Clustering Heuristics for Ethereum, Financial Cryptography and Data Security (FC 2020), Springer. doi:10.1007/978-3-030-51280-4_33
2. Watch Your Back: Identifying Cybercrime Financial Relationships in Bitcoin through Back-and-Forth Exploration, ACM SIGSAC (CCS '22). doi:10.1145/3548606.3560587
3. TRacer: Scalable Graph-Based Transaction Tracing for Account-Based Blockchain Trading Systems, IEEE Transactions on Information Forensics and Security (TIFS 2023). doi:10.1109/TIFS.2023.3266162
4. Analysis of Address Linkability in Tornado Cash on Ethereum, CNCERT 2021, Springer, 2022. doi:10.1007/978-981-16-9229-1_3
5. A Two-Layer Transaction Network-Based Method for Virtual Currency Address Identity Recognition, Cryptography (MDPI 2025). doi:10.3390/cryptography9040065
6. AI-Based Framework for Classifying Cryptocurrency Exchanges through Transaction Feature Analysis, IEEE ICBC 2025. doi:10.1109/ICBC64466.2025.11114507

---

👥 Team VeroAI (Team ID: 146040)

- Smart India Hackathon 2026
- Built with dedication to empower Indian Cyber Crime Investigators and support the vision of I4C (Indian Cybercrime Coordination Centre).

---
