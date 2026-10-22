"""
Stack Analyzer for J.A.R.V.I.S. Idea Engine.
Analyzes technology stacks, extracts capabilities, and maps cross-technology synergies.
"""

from typing import List, Dict, Any, Set
from idea_engine.models import TechnologyProfile, StackAnalysis


TECH_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    # Programming Languages
    "python": {
        "name": "Python",
        "category": "Language",
        "primary": ["AI & Machine Learning", "Backend APIs", "Automation & Scripting", "Data Engineering"],
        "secondary": ["Computer Vision", "Web Scraping", "NLP", "Robotics"],
        "best_for": ["Rapid prototyping", "AI pipelines", "Microservices", "Data analysis"],
        "limitations": ["CPU-bound multi-threading", "Mobile native UI", "Low-level memory control"]
    },
    "typescript": {
        "name": "TypeScript",
        "category": "Language",
        "primary": ["Full-Stack Web Development", "Type-Safe Client Apps", "Node.js Backends"],
        "secondary": ["Serverless Functions", "Desktop Apps (Electron/Tauri)", "Mobile (React Native)"],
        "best_for": ["Enterprise web apps", "Interactive dashboards", "Scalable frontend architectures"],
        "limitations": ["Requires compilation step", "Runtime overhead for heavy mathematical computing"]
    },
    "javascript": {
        "name": "JavaScript",
        "category": "Language",
        "primary": ["Browser Scripting", "Dynamic Web Interfaces", "Event-Driven Backends"],
        "secondary": ["Cross-Platform Mobile", "Full-Stack Serverless"],
        "best_for": ["Web applications", "Real-time sockets", "Interactive UIs"],
        "limitations": ["Lack of compile-time types without TypeScript", "High compute tasks"]
    },
    "rust": {
        "name": "Rust",
        "category": "Language",
        "primary": ["Systems Programming", "High-Performance Services", "WebAssembly", "Memory Safety"],
        "secondary": ["Crypto/Blockchain", "CLI Tools", "Embedded Systems", "Game Engines"],
        "best_for": ["Low-latency backends", "Compute-heavy modules", "Safe concurrency", "Wasm modules"],
        "limitations": ["Steep learning curve", "Longer compile times"]
    },
    "golang": {
        "name": "Go (Golang)",
        "category": "Language",
        "primary": ["High-Concurrency Backends", "Cloud Native Microservices", "DevOps Tooling"],
        "secondary": ["Distributed Systems", "Network Programming", "CLI Utilities"],
        "best_for": ["Scalable API services", "Kubernetes operators", "High-throughput data streaming"],
        "limitations": ["Limited meta-programming/generics flexibility", "UI development"]
    },
    "cpp": {
        "name": "C++",
        "category": "Language",
        "primary": ["Low-Level Performance", "Computer Vision Engines", "Game Development", "Embedded"],
        "secondary": ["High-Frequency Trading", "Audio Processing", "Robotics"],
        "best_for": ["Hardware acceleration", "Real-time simulation", "Native drivers"],
        "limitations": ["Manual memory risks", "Complex build systems"]
    },

    # Backend Frameworks
    "fastapi": {
        "name": "FastAPI",
        "category": "Backend Framework",
        "primary": ["High-Performance Async REST APIs", "Automatic OpenAPI Docs", "Pydantic Validation"],
        "secondary": ["WebSocket Streaming", "Background Task Orchestration", "AI Model Serving"],
        "best_for": ["AI inference backends", "Modern microservices", "Async data aggregators"],
        "limitations": ["Not full-stack out-of-the-box (requires separate frontend/database setup)"]
    },
    "flask": {
        "name": "Flask",
        "category": "Backend Framework",
        "primary": ["Lightweight Web Services", "Microframework Architecture", "WSGI Applications"],
        "secondary": ["Jinja Templating", "Small Utilities & Extensions"],
        "best_for": ["Minimalist APIs", "Tooling dashboards", "Rapid embedded web servers"],
        "limitations": ["Synchronous by default (without async extensions)", "Manual structure for large apps"]
    },
    "django": {
        "name": "Django",
        "category": "Backend Framework",
        "primary": ["Batteries-Included Full-Stack", "Built-In ORM & Admin Panel", "Authentication & Security"],
        "secondary": ["REST APIs via DRF", "Content Management"],
        "best_for": ["Monolithic web products", "Complex data models", "SaaS boilerplates"],
        "limitations": ["Heavier footprint", "Opinionated ORM pattern"]
    },
    "express": {
        "name": "Express.js",
        "category": "Backend Framework",
        "primary": ["Node.js REST Services", "Middleware Pipeline", "Lightweight HTTP Server"],
        "secondary": ["Socket.io Streaming", "Server-Side Rendering Handlers"],
        "best_for": ["JavaScript microservices", "API gateways", "Real-time backends"],
        "limitations": ["Unopinionated structure can cause fragmentation", "Callback/Promise overhead"]
    },
    "nest": {
        "name": "NestJS",
        "category": "Backend Framework",
        "primary": ["Enterprise TypeScript Backends", "Dependency Injection", "Modular Microservices"],
        "secondary": ["GraphQL APIs", "WebSocket Gateways", "gRPC Communication"],
        "best_for": ["Large scalable backends", "Multi-tenant architectures"],
        "limitations": ["Boilerplate overhead for small prototypes"]
    },

    # Frontend Frameworks & Libraries
    "react": {
        "name": "React",
        "category": "Frontend Framework",
        "primary": ["Component-Based Declarative UI", "Virtual DOM Rendering", "Rich Ecosystem"],
        "secondary": ["State Management (Zustand/Redux)", "Universal Web Applications"],
        "best_for": ["Single Page Applications (SPAs)", "Interactive dashboards", "Productivity suites"],
        "limitations": ["Requires build pipeline & routing library", "Client-side SEO without SSR"]
    },
    "nextjs": {
        "name": "Next.js",
        "category": "Frontend / Full-Stack",
        "primary": ["Server-Side Rendering (SSR)", "Static Site Generation (SSG)", "React Server Components"],
        "secondary": ["API Routes", "Automatic Image Optimization", "Edge Middleware"],
        "best_for": ["Production SaaS web apps", "SEO-critical web portals", "Full-stack React products"],
        "limitations": ["Vendor lock-in tendencies with Vercel infrastructure"]
    },
    "vue": {
        "name": "Vue.js",
        "category": "Frontend Framework",
        "primary": ["Reactivity System", "Single File Components", "Gentle Learning Curve"],
        "secondary": ["Pinia State Management", "Vue Router Integration"],
        "best_for": ["Clean interactive web portals", "Progressive web interfaces"],
        "limitations": ["Smaller ecosystem compared to React"]
    },
    "svelte": {
        "name": "Svelte / SvelteKit",
        "category": "Frontend Framework",
        "primary": ["Compile-Time Reactivity", "Zero Virtual DOM Overhead", "Tiny Bundle Sizes"],
        "secondary": ["Built-In Transitions", "Full-Stack Serverless Routing"],
        "best_for": ["Ultra-fast lightweight apps", "Data visualizers", "Embedded web widgets"],
        "limitations": ["Smaller third-party component library ecosystem"]
    },
    "tailwind": {
        "name": "Tailwind CSS",
        "category": "Styling Framework",
        "primary": ["Utility-First Styling", "Responsive Layout Design", "Design System Enforcement"],
        "secondary": ["Dark Mode Styling", "Modern Typography"],
        "best_for": ["Rapid UI polishing", "Custom glassmorphism/neumorphism interfaces"],
        "limitations": ["Class clutter in HTML without component abstraction"]
    },

    # Databases & Storage
    "supabase": {
        "name": "Supabase",
        "category": "BaaS & Database",
        "primary": ["Managed PostgreSQL", "Row Level Security (RLS)", "Instant Auth & User Management"],
        "secondary": ["Real-time Database Subscriptions", "Storage Buckets", "pgvector Embedding Search"],
        "best_for": ["Full-stack prototypes", "AI applications needing pgvector", "Collaborative apps"],
        "limitations": ["Platform lock-in on custom extensions", "Free tier sleep limits"]
    },
    "postgresql": {
        "name": "PostgreSQL",
        "category": "Relational Database",
        "primary": ["ACID Compliance", "Complex Relational Joins", "JSONB Document Storage"],
        "secondary": ["pgvector Vector Indexing", "Full-Text Search", "Extensions Ecosystem"],
        "best_for": ["Mission-critical data", "Vector + relational hybrid architectures", "Financial records"],
        "limitations": ["Requires scaling strategy for massive distributed sharding"]
    },
    "mongodb": {
        "name": "MongoDB",
        "category": "NoSQL Database",
        "primary": ["Flexible Schema Documents", "Horizontal Sharding", "Aggregation Pipelines"],
        "secondary": ["Atlas Vector Search", "Time Series Collections"],
        "best_for": ["Rapid schema iteration", "Event logging", "Content management catalogs"],
        "limitations": ["Complex multi-document transactions overhead"]
    },
    "redis": {
        "name": "Redis",
        "category": "In-Memory Database & Cache",
        "primary": ["Sub-Millisecond In-Memory Caching", "Pub/Sub Messaging", "Session Management"],
        "secondary": ["Rate Limiting", "Queue Management (BullMQ/Celery)", "Vector Similarity Search"],
        "best_for": ["Real-time notification feeds", "API rate limiters", "Leaderboards & sessions"],
        "limitations": ["RAM cost for very large datasets", "Data persistence tuning required"]
    },
    "firebase": {
        "name": "Firebase",
        "category": "BaaS & Database",
        "primary": ["Firestore Document Sync", "Authentication", "Cloud Functions"],
        "secondary": ["Cloud Messaging (FCM)", "Hosting & Analytics"],
        "best_for": ["Mobile-first apps", "Real-time chat & collaboration", "Serverless MVPs"],
        "limitations": ["Vendor lock-in", "Complex relational queries are difficult in Firestore"]
    },

    # AI Models & LLM APIs
    "gemini": {
        "name": "Google Gemini API",
        "category": "AI / Multimodal Foundation Model",
        "primary": ["Long-Context Reasoning (1M+ Tokens)", "Multimodal (Vision/Audio/Video/Code)", "Structured JSON Generation"],
        "secondary": ["Function Calling / Tool Execution", "Grounding with Google Search", "Embeddings"],
        "best_for": ["Multimodal analysis", "Large codebase comprehension", "Document intelligence", "AI agents"],
        "limitations": ["Rate limits on free tiers", "Cloud dependency"]
    },
    "openai": {
        "name": "OpenAI API (GPT-4o)",
        "category": "AI / Foundation Model",
        "primary": ["High-Accuracy Reasoning", "Function Calling", "Structured Outputs"],
        "secondary": ["Vision Understanding", "Voice Integration", "Embeddings (text-embedding-3)"],
        "best_for": ["Complex agentic workflows", "Structured extraction", "Chatbots"],
        "limitations": ["Cost per token on high-volume usage"]
    },
    "langchain": {
        "name": "LangChain / LangGraph",
        "category": "AI Framework",
        "primary": ["Multi-Agent Orchestration", "Cyclic Graph Workflows", "Stateful Memory"],
        "secondary": ["RAG Pipelines", "Tool Integrations", "Document Loaders"],
        "best_for": ["Complex autonomous AI agents", "Multi-step research pipelines"],
        "limitations": ["Abstraction complexity", "Fast-moving API shifts"]
    },
    "llamaindex": {
        "name": "LlamaIndex",
        "category": "AI Framework",
        "primary": ["Data Ingestion & Indexing", "Advanced RAG Pipelines", "Hierarchical Query Engines"],
        "secondary": ["Knowledge Graph Extraction", "Agentic Data Connectors"],
        "best_for": ["Enterprise search over complex docs (PDF, Excel, Notion)", "Document Q&A"],
        "limitations": ["Focused strictly on data indexing and retrieval"]
    },
    "opencv": {
        "name": "OpenCV",
        "category": "Computer Vision",
        "primary": ["Image Processing & Filtering", "Feature Extraction", "Object Detection & Tracking"],
        "secondary": ["Face Recognition", "Contour Analysis", "Camera Stream Capture"],
        "best_for": ["Real-time video analytics", "Inspection systems", "Motion tracking", "Augmented reality"],
        "limitations": ["Classical CV lacks deep contextual semantic understanding without deep learning"]
    },
    "pytorch": {
        "name": "PyTorch",
        "category": "Deep Learning Framework",
        "primary": ["Custom Neural Network Training", "Tensor Acceleration (CUDA)", "Fine-Tuning Models"],
        "secondary": ["TorchVision", "HuggingFace Integration", "ONNX Export"],
        "best_for": ["Custom AI research", "Specialized computer vision / audio models", "Edge model deployment"],
        "limitations": ["Requires GPU infrastructure for training and heavy inference"]
    },

    # DevOps & Infrastructure
    "docker": {
        "name": "Docker",
        "category": "DevOps & Containerization",
        "primary": ["Reproducible Environment Packaging", "Microservice Isolation", "Portable Deployment"],
        "secondary": ["Multi-Stage Builds", "Docker Compose Multi-Container Orchestration"],
        "best_for": ["Production deployments", "Complex dependency isolation", "CI/CD pipelines"],
        "limitations": ["Container overhead on low-resource microcontrollers"]
    },
    "kubernetes": {
        "name": "Kubernetes (K8s)",
        "category": "Cloud & Orchestration",
        "primary": ["Automated Scaling", "Self-Healing Workloads", "Container Fleet Management"],
        "secondary": ["Service Mesh Integration", "Rolling Deployments", "Secret Management"],
        "best_for": ["High-availability multi-node systems", "Large distributed SaaS backends"],
        "limitations": ["Significant configuration complexity for solo developer projects"]
    },
    "aws": {
        "name": "AWS (Amazon Web Services)",
        "category": "Cloud Platform",
        "primary": ["Serverless Compute (Lambda)", "Object Storage (S3)", "Managed Databases (RDS/DynamoDB)"],
        "secondary": ["CloudFront CDN", "SageMaker ML Hosting", "SQS Messaging"],
        "best_for": ["Scalable enterprise architectures", "Serverless cloud backends"],
        "limitations": ["Complex IAM permissions", "Surprise billing if unmonitored"]
    },
    "gcp": {
        "name": "Google Cloud Platform (GCP)",
        "category": "Cloud Platform",
        "primary": ["Cloud Run Container Serving", "BigQuery Analytics", "Vertex AI ML Platform"],
        "secondary": ["Cloud Functions", "Cloud Storage", "Pub/Sub"],
        "best_for": ["AI-heavy cloud services", "Big data analytics", "Fast container deployments"],
        "limitations": ["Pricing tier nuances"]
    },

    # Mobile & IoT / Hardware
    "flutter": {
        "name": "Flutter",
        "category": "Mobile / Cross-Platform",
        "primary": ["Native iOS/Android Compiled Apps", "Custom Canvas Rendering", "Single Codebase"],
        "secondary": ["Desktop Apps (Windows/macOS/Linux)", "Web Builds"],
        "best_for": ["High-fidelity mobile applications", "Smooth UI animations", "Offline-first mobile tools"],
        "limitations": ["Platform channel overhead for deep OS-specific native features"]
    },
    "reactnative": {
        "name": "React Native",
        "category": "Mobile Framework",
        "primary": ["Native Mobile UI with React", "JavaScript Bridge / TurboModules", "Code Sharing with Web"],
        "secondary": ["Expo Ecosystem", "Over-The-Air (OTA) Updates"],
        "best_for": ["Mobile apps for React teams", "Fast cross-platform mobile prototypes"],
        "limitations": ["Bridge performance bottlenecks for continuous heavy graphics/sensors"]
    },
    "arduino": {
        "name": "Arduino / ESP32",
        "category": "Hardware / IoT",
        "primary": ["Microcontroller Firmware", "Sensor Interfacing (GPIO/I2C/SPI)", "WiFi/BLE Connectivity (ESP32)"],
        "secondary": ["Motor Control", "Telemetry Data Logging", "Edge IoT Automation"],
        "best_for": ["Smart home devices", "Agricultural sensors", "Wearable hardware", "Robotics"],
        "limitations": ["Kilobytes of RAM constraints", "No heavy on-device neural networks without TinyML"]
    },
    "raspberrypi": {
        "name": "Raspberry Pi",
        "category": "Single Board Computer",
        "primary": ["Linux-Based Edge Computing", "Camera Stream Processing", "GPIO Control"],
        "secondary": ["Local Server Hosting", "Local Small AI Inference", "Robotics Controller"],
        "best_for": ["Edge computer vision", "Home automation hubs", "Autonomous rovers", "Kiosks"],
        "limitations": ["Power consumption higher than bare microcontrollers"]
    },
    "html": {
        "name": "HTML5",
        "category": "Markup & Structure",
        "primary": ["Semantic Document Structure", "Web Accessibility Elements", "Hypermedia Linking"],
        "secondary": ["Canvas 2D API", "Web Audio / Video", "Form Encodings"],
        "best_for": ["Static page markup", "Email templates", "UI layout framing"],
        "limitations": ["Static structure only: No programmatic computation, database storage, backend logic, or AI inference capabilities."]
    },
    "css": {
        "name": "CSS3",
        "category": "Styling & Presentation",
        "primary": ["Visual Presentation", "Responsive Grid / Flexbox Layouts", "CSS Keyframe Animations"],
        "secondary": ["3D CSS Transforms", "Custom Variables", "Media Queries"],
        "best_for": ["UI theme styling", "Visual animations", "Responsive breakpoints"],
        "limitations": ["Presentation only: Cannot perform server-side computing, persist data, or run machine learning models."]
    },
    "markdown": {
        "name": "Markdown",
        "category": "Documentation & Text",
        "primary": ["Lightweight Formatted Text", "Documentation Specifications", "Static Content"],
        "secondary": ["Table Formats", "Code Snippet Blocks"],
        "best_for": ["Technical documentation", "Static content management", "Prompt engineering templates"],
        "limitations": ["Static text specification only: No executable runtime logic or database layer."]
    },
    "sqlite": {
        "name": "SQLite",
        "category": "Embedded Database",
        "primary": ["Zero-Configuration Serverless SQL", "Local File Storage", "ACID Transactions"],
        "secondary": ["In-Memory DB Testing", "Full-Text Search (FTS5)"],
        "best_for": ["Local desktop apps", "Mobile caching", "Embedded devices", "Unit testing"],
        "limitations": ["Single-writer concurrency limitations for heavy multi-client cloud servers."]
    },
    "bash": {
        "name": "Bash / Shell",
        "category": "Scripting & Automation",
        "primary": ["CLI Automation", "Process Orchestration", "CI/CD Pipeline Scripts"],
        "secondary": ["File Manipulation", "Environment Configuration"],
        "best_for": ["Deployment scripts", "Local workflow automation", "System administration"],
        "limitations": ["Error handling complexity for complex business domain logic."]
    }
}


class StackAnalyzer:
    """
    Analyzes an input list of technology strings, matches them with known capability profiles,
    identifies missing architectural layers, and computes cross-technology synergies.
    """

    @classmethod
    def analyze(cls, raw_technologies: List[str]) -> StackAnalysis:
        profiles: List[TechnologyProfile] = []
        categories_seen: Set[str] = set()
        seen_canonical: Set[str] = set()

        for raw_name in raw_technologies:
            clean_name = raw_name.strip()
            if not clean_name:
                continue
            canon = cls.canonicalize_name(clean_name)
            if canon in seen_canonical:
                continue
            seen_canonical.add(canon)
            profile = cls._get_or_create_profile(clean_name)
            profiles.append(profile)
            categories_seen.add(profile.category)

        # Determine missing standard architectural layers
        standard_layers = {"Frontend Framework", "Backend Framework", "Relational Database", "AI / Multimodal Foundation Model"}
        missing = [layer for layer in standard_layers if layer not in categories_seen]

        # Compute technical synergies
        synergies = cls._identify_synergies(profiles)

        # Recommend problem domains based on stack capabilities
        domains = cls._recommend_domains(profiles)

        # Evaluate architectural limitations / weak stack detection
        warnings: List[str] = []
        compute_categories = {"Language", "Backend Framework", "Deep Learning Framework", "AI / Multimodal Foundation Model", "Cloud Native Microservices", "Single Board Computer"}
        has_compute = any(p.category in compute_categories or any("compute" in c.lower() or "ai" in c.lower() or "backend" in c.lower() for c in p.primary_capabilities) for p in profiles)
        
        has_only_markup_styling = len(profiles) > 0 and all(p.category in {"Markup & Structure", "Styling & Presentation", "Documentation & Text"} for p in profiles)

        if has_only_markup_styling:
            warnings.append("Weak/Static Stack: Stack contains only static markup, styling, or documentation formats. Cannot execute backend logic, data persistence, or AI models without additional runtime layers.")
        elif not has_compute and len(profiles) > 0:
            warnings.append("Missing Compute Layer: Stack lacks a dedicated backend runtime or programming language. Complex data workflows or dynamic processing will require supplemental service architecture.")

        return StackAnalysis(
            technologies=profiles,
            categories_present=sorted(list(categories_seen)),
            missing_categories=missing,
            synergies=synergies,
            recommended_problem_domains=domains,
            architectural_warnings=warnings
        )

    @classmethod
    def canonicalize_name(cls, name: str) -> str:
        """Resolves common aliases and returns canonical identifier."""
        key = name.lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "")
        aliases = {
            "py": "python",
            "ts": "typescript",
            "js": "javascript",
            "reactjs": "react",
            "react.js": "react",
            "next": "nextjs",
            "next.js": "nextjs",
            "vuejs": "vue",
            "vue.js": "vue",
            "postgres": "postgresql",
            "pg": "postgresql",
            "mongo": "mongodb",
            "geminiapi": "gemini",
            "googlegemini": "gemini",
            "gpt4": "openai",
            "gpt4o": "openai",
            "k8s": "kubernetes",
            "rpi": "raspberrypi",
            "esp8266": "arduino",
            "esp32": "arduino"
        }
        resolved = aliases.get(key, key)
        if resolved == "gemini":
            return "gemini api"
        return resolved

    @classmethod
    def get_profile(cls, name: str) -> TechnologyProfile:
        """Public accessor to retrieve or generate a technology capability profile."""
        return cls._get_or_create_profile(name)

    @classmethod
    def _get_or_create_profile(cls, name: str) -> TechnologyProfile:
        key = name.lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "")

        # Alias resolution
        aliases = {
            "py": "python",
            "ts": "typescript",
            "js": "javascript",
            "reactjs": "react",
            "react.js": "react",
            "next": "nextjs",
            "next.js": "nextjs",
            "vuejs": "vue",
            "vue.js": "vue",
            "postgres": "postgresql",
            "pg": "postgresql",
            "mongo": "mongodb",
            "geminiapi": "gemini",
            "googlegemini": "gemini",
            "gpt4": "openai",
            "gpt4o": "openai",
            "k8s": "kubernetes",
            "rpi": "raspberrypi",
            "esp8266": "arduino",
            "esp32": "arduino"
        }
        resolved_key = aliases.get(key, key)

        if resolved_key in TECH_KNOWLEDGE_BASE:
            data = TECH_KNOWLEDGE_BASE[resolved_key]
            return TechnologyProfile(
                name=data["name"],
                category=data["category"],
                primary_capabilities=list(data["primary"]),
                secondary_capabilities=list(data["secondary"]),
                best_for=list(data["best_for"]),
                limitations=list(data["limitations"])
            )

        # Dynamic fallback for unlisted technologies
        category = "Specialized Tool / Library"
        if any(w in key for w in ["db", "sql", "data", "store"]):
            category = "Database & Storage"
        elif any(w in key for w in ["ui", "css", "web", "front", "react", "vue"]):
            category = "Frontend Tool"
        elif any(w in key for w in ["api", "server", "backend", "auth"]):
            category = "Backend Service"
        elif any(w in key for w in ["ai", "llm", "vision", "model", "embed"]):
            category = "AI / Machine Learning"

        return TechnologyProfile(
            name=name,
            category=category,
            primary_capabilities=[f"Domain-specific capability provided by {name}"],
            secondary_capabilities=["Integration support requires verification"],
            best_for=[f"Experimental workflows requiring {name}"],
            limitations=[
                f"Unknown or unverified technology '{name}'. Verified production capabilities, API stability, and ecosystem compatibility cannot be assumed without external verification."
            ]
        )

    @classmethod
    def _identify_synergies(cls, profiles: List[TechnologyProfile]) -> List[str]:
        """Identifies powerful technical combinations formed by the stack."""
        tech_names_lower = {p.name.lower() for p in profiles}
        synergies: List[str] = []

        has_ai = any("ai" in p.category.lower() or "gemini" in p.name.lower() or "openai" in p.name.lower() for p in profiles)
        has_fastapi = any("fastapi" in p.name.lower() for p in profiles)
        has_supabase = any("supabase" in p.name.lower() for p in profiles)
        has_react = any("react" in p.name.lower() or "next" in p.name.lower() for p in profiles)
        has_cv = any("opencv" in p.name.lower() or "vision" in p.name.lower() for p in profiles)
        has_docker = any("docker" in p.name.lower() for p in profiles)
        has_hardware = any("arduino" in p.name.lower() or "raspberry" in p.name.lower() for p in profiles)
        has_postgres = any("postgres" in p.name.lower() or "supabase" in p.name.lower() for p in profiles)

        if has_ai and has_fastapi:
            synergies.append("FastAPI + AI Model: Enables high-speed async streaming of LLM inference and structured JSON agent outputs.")

        if has_ai and has_supabase:
            synergies.append("Supabase (pgvector) + AI: Unlocks authenticated Semantic Search, RAG knowledge retrieval, and persistent conversational memory.")

        if has_react and has_supabase:
            synergies.append("React + Supabase: Instant real-time UI synchronization, Row Level Security (RLS) authentication, and asset file storage.")

        if has_cv and has_hardware:
            synergies.append("OpenCV + Edge Hardware: Real-time physical-world computer vision, smart camera feeds, and automated sensor actuation.")

        if has_cv and has_ai:
            synergies.append("OpenCV + Multimodal AI: Two-stage visual pipeline (OpenCV detects regions of interest -> Foundation model analyzes semantic context).")

        if has_docker and has_fastapi:
            synergies.append("Docker + FastAPI: Fully reproducible containerized microservices ready for zero-downtime cloud deployments.")

        if has_postgres and has_fastapi:
            synergies.append("PostgreSQL + FastAPI: High-throughput async relational queries with SQLAlchemy/Tortoise ORM and transactional data safety.")

        if not synergies and len(profiles) >= 2:
            synergies.append(f"Combined {profiles[0].name} and {profiles[1].name} into a cohesive full-stack service architecture.")

        return synergies

    @classmethod
    def _recommend_domains(cls, profiles: List[TechnologyProfile]) -> List[str]:
        """Recommends relevant problem domains based on the capabilities present in the stack."""
        domains = set()
        categories = {p.category for p in profiles}
        names = {p.name.lower() for p in profiles}

        if any("opencv" in n or "vision" in n or "raspberry" in n for n in names):
            domains.update(["Smart Agriculture & Crop Health", "Automated Quality Inspection", "Accessibility & Assistive Tech", "Security & Surveillance"])

        if any("ai" in c.lower() for c in categories):
            domains.update(["Intelligent Developer Tools", "Healthcare & Medical Diagnostics", "Legal & Financial Document Intelligence", "Education & Adaptive Tutoring"])

        if any("baas" in c.lower() or "relational" in c.lower() for c in categories):
            domains.update(["Collaborative SaaS Platforms", "Logistics & Supply Chain Tracking", "FinTech & Automated Budgeting"])

        if any("hardware" in c.lower() for c in categories):
            domains.update(["IoT Environmental Monitoring", "Smart Home Automation", "Energy Management"])

        if not domains:
            domains = {"Developer Productivity", "Workflow Automation", "Data Visualization", "Open-Ended Impact"}

        return sorted(list(domains))
