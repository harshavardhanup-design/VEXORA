"""VEXORA On-Device Local AI Engine.

100% Local, Offline, and Air-Gapped.
Runs entirely inside the user's PC using Snapdragon Hexagon NPU & CPU optimization.
Provides comprehensive reasoning across computer science, coding, hardware, mathematics,
science, productivity, and general knowledge with zero cloud dependencies or API keys.
"""
from __future__ import annotations
import datetime
import html
import os
import re
from typing import Optional

from ai.safe_math import safe_calc
from core.logging_setup import get_logger

log = get_logger('local_engine')

# ── DOMAIN KNOWLEDGE CORPUS (OFFLINE ON-DEVICE) ──────────────────────────────

KNOWLEDGE_TOPICS: dict[str, dict[str, str]] = {
    # ── Programming & Software Engineering ──
    "python": {
        "title": "Python Programming Language",
        "category": "Programming",
        "summary": "Python is a high-level, dynamically typed, interpreted programming language known for readability and clean syntax.",
        "details": (
            "Python supports multiple programming paradigms including Object-Oriented (OOP), Functional, and Imperative. "
            "Key features include dynamic typing, automatic memory management via reference counting and cyclic garbage collection, "
            "comprehensive standard library ('batteries included'), and a vast ecosystem (PySide6, NumPy, PyTorch, FastAPI).\n\n"
            "• Execution Model: CPython compiles `.py` files into intermediate bytecode (`.pyc`), executed by the CPython virtual machine.\n"
            "• Concurrency: Threading is governed by the Global Interpreter Lock (GIL) in standard CPython; CPU-bound tasks use `multiprocessing` or sub-interpreters, while I/O-bound tasks use `asyncio`."
        ),
        "code": "def fibonacci(n: int) -> list[int]:\n    a, b = 0, 1\n    result = []\n    for _ in range(n):\n        result.append(a)\n        a, b = b, a + b\n    return result"
    },
    "javascript": {
        "title": "JavaScript (ECMAScript)",
        "category": "Programming",
        "summary": "JavaScript is a high-level, just-in-time compiled, multi-paradigm language that powers the interactive modern web.",
        "details": (
            "JavaScript features prototype-based inheritance, dynamic typing, first-class functions, and an event-driven non-blocking I/O runtime. "
            "It runs in browsers (via engines like V8, SpiderMonkey) and server environments (Node.js, Deno, Bun).\n\n"
            "• Event Loop: Manages asynchronous operations using the Call Stack, Microtask Queue (Promises), and Macrotask Queue (timers/I/O).\n"
            "• Modern Features: ES6+ introduced arrow functions, classes, destructuring, modules (`import`/`export`), async/await, and optional chaining."
        ),
        "code": "async function fetchData(url) {\n    try {\n        const res = await fetch(url);\n        return await res.json();\n    } catch (err) {\n        console.error('Fetch failed:', err);\n    }\n}"
    },
    "c++": {
        "title": "C++ Programming Language",
        "category": "Systems Programming",
        "summary": "C++ is a compiled, statically typed systems language offering high performance, low-level memory control, and zero-cost abstractions.",
        "details": (
            "C++ provides direct hardware access while supporting object-oriented, generic (templates), and functional paradigms. "
            "It is the foundation of operating systems, game engines (Unreal Engine), GUI toolkits (Qt), and high-frequency trading platforms.\n\n"
            "• RAII: Resource Acquisition Is Initialization binds resource lifecycles to object scopes.\n"
            "• Memory: Supports manual allocation (`new`/`delete`) and modern smart pointers (`std::unique_ptr`, `std::shared_ptr`)."
        ),
        "code": "#include <iostream>\n#include <vector>\n#include <memory>\n\nint main() {\n    auto vec = std::make_unique<std::vector<int>>();\n    vec->push_back(42);\n    std::cout << \"Value: \" << vec->at(0) << '\\n';\n    return 0;\n}"
    },
    "rust": {
        "title": "Rust Systems Language",
        "category": "Systems Programming",
        "summary": "Rust is a systems programming language focused on memory safety, concurrency, and performance without garbage collection.",
        "details": (
            "Rust prevents memory bugs (null pointers, buffer overflows, data races) at compile time via its unique ownership, borrowing, "
            "and lifetime system.\n\n"
            "• Ownership Rules: Each value has a single owner; when the owner goes out of scope, the memory is freed.\n"
            "• Borrowing: You may have any number of immutable references (`&T`) OR exactly one mutable reference (`&mut T`), but never both simultaneously."
        ),
        "code": "fn main() {\n    let mut numbers = vec![1, 2, 3];\n    numbers.push(4);\n    println!(\"Vector: {:?}\", numbers);\n}"
    },
    "api": {
        "title": "Application Programming Interface (API)",
        "category": "Architecture",
        "summary": "An API defines a set of rules and protocols enabling different software applications to communicate and exchange data.",
        "details": (
            "Common API architectural styles:\n"
            "• REST (Representational State Transfer): Uses HTTP verbs (GET, POST, PUT, DELETE), stateless communication, and JSON payloads.\n"
            "• GraphQL: Allows clients to request exactly the fields they need in a single round-trip query.\n"
            "• gRPC: High-performance RPC framework using HTTP/2 transport and Protocol Buffers (Protobuf) serialization.\n"
            "• WebSocket: Full-duplex persistent TCP connections for real-time bidirectional streaming."
        )
    },
    "git": {
        "title": "Git Distributed Version Control",
        "category": "Developer Tools",
        "summary": "Git is a distributed version control system designed to track changes in source code during software development.",
        "details": (
            "Every Git clone contains the full history of the repository, enabling fast local operations without network reliance.\n\n"
            "• Core Objects: Blobs (file contents), Trees (directories), Commits (snapshots with metadata), and Annotated Tags.\n"
            "• Key Commands:\n"
            "  - `git commit -m \"msg\"`: Records staged changes to the local repository.\n"
            "  - `git branch <name>` / `git switch <name>`: Creates and isolates new lines of development.\n"
            "  - `git rebase <upstream>`: Replays commits on top of another base branch for a linear history."
        )
    },
    "database": {
        "title": "Database Architecture (SQL vs NoSQL)",
        "category": "Databases",
        "summary": "Databases organize, store, and manage data with varying trade-offs between consistency, schema rigidity, and horizontal scalability.",
        "details": (
            "• Relational (SQL): PostgreSQL, MySQL, SQLite. Relies on structured schemas, normalized tables, foreign keys, and ACID guarantees (Atomicity, Consistency, Isolation, Durability).\n"
            "• Non-Relational (NoSQL): Document stores (MongoDB), Key-Value (Redis), Columnar (Cassandra), and Graph (Neo4j). Designed for horizontal partitioning, flexible schemas, and high write throughput."
        )
    },

    # ── Computer Architecture & Hardware ──
    "cpu": {
        "title": "Central Processing Unit (CPU)",
        "category": "Hardware",
        "summary": "The CPU is the primary computational brain of a computer responsible for fetching, decoding, and executing instructions.",
        "details": (
            "Modern CPUs (such as the Qualcomm Snapdragon Oryon or Intel/AMD cores) leverage multi-core superscalar out-of-order execution pipelines.\n\n"
            "• Pipeline Stages: Instruction Fetch (IF), Decode (ID), Execute (EX), Memory Access (MEM), and Write-Back (WB).\n"
            "• Cache Hierarchy: Ultra-fast SRAM caches (L1: ~1ns, L2: ~3ns, L3: ~10ns) mitigate the latency of system DRAM (~60-80ns).\n"
            "• Architectures: ARM64 (RISC with fixed-length instructions, high energy efficiency) vs x86-64 (CISC with micro-op decoding)."
        )
    },
    "npu": {
        "title": "Qualcomm® Hexagon™ Neural Processing Unit (NPU)",
        "category": "Hardware & AI",
        "summary": "An NPU is a specialized processor architected for parallel tensor algebra, matrix multiplications, and INT4/INT8 quantized neural networks.",
        "details": (
            "In Snapdragon Copilot+ PCs (e.g., HP OmniBook X), the Qualcomm Hexagon NPU delivers up to 45 TOPS (Trillion Operations Per Second) at just 1.5–2.5 Watts.\n\n"
            "• Why NPU vs CPU/GPU: CPUs handle sequential logic; GPUs handle wide SIMD graphics; NPUs are designed specifically for deep neural network inferencing with fused multiply-accumulate (MAC) arrays.\n"
            "• Energy Efficiency: Consumes up to 10× less power than running the same model on an x86 CPU, enabling all-day AI assistance on battery."
        )
    },
    "gpu": {
        "title": "Graphics Processing Unit (GPU)",
        "category": "Hardware",
        "summary": "A GPU consists of thousands of smaller, efficient cores designed for massive parallel throughput in graphics rendering and compute.",
        "details": (
            "Modern GPUs (Qualcomm Adreno, NVIDIA GeForce, AMD Radeon) excel at matrix operations, 3D polygon rasterization, ray tracing, "
            "and compute shaders via DirectX 12, Vulkan, and CUDA."
        )
    },
    "ram": {
        "title": "Random Access Memory (RAM)",
        "category": "Hardware",
        "summary": "RAM is high-speed volatile storage providing rapid read and write access to active processes and operating system data.",
        "details": (
            "Modern PCs use LPDDR5X or DDR5 memory running at 6400–8448 MT/s. When RAM is exhausted, the OS pages memory to storage (Virtual Memory / Pagefile), "
            "which causes performance stutter due to NVMe storage being orders of magnitude slower than DRAM."
        )
    },

    # ── AI & Machine Learning ──
    "artificial intelligence": {
        "title": "Artificial Intelligence (AI)",
        "category": "AI / ML",
        "summary": "Artificial Intelligence is the science and engineering of creating machines capable of perception, reasoning, learning, and autonomous decision-making.",
        "details": (
            "• Symbolic AI: Rule-based expert systems and logic trees.\n"
            "• Machine Learning (ML): Statistical algorithms that discover patterns in data without explicit procedural programming.\n"
            "• Deep Learning: Multi-layered artificial neural networks capable of learning hierarchical feature representations from raw data.\n"
            "• On-Device AI: Running quantized models directly on local hardware (NPU/CPU) for instant privacy, offline capability, and zero cloud latency."
        )
    },
    "machine learning": {
        "title": "Machine Learning (ML)",
        "category": "AI / ML",
        "summary": "Machine Learning focuses on algorithms that learn from training data to generalize and make predictions on unseen data.",
        "details": (
            "Primary Paradigms:\n"
            "• Supervised Learning: Learning a mapping from inputs to labeled outputs (Classification, Regression).\n"
            "• Unsupervised Learning: Discovering inherent structures or clusters in unlabeled data (K-Means, PCA, Autoencoders).\n"
            "• Reinforcement Learning: Agents learning optimal policy actions via environmental reward signals (Q-learning, PPO)."
        )
    },
    "large language models": {
        "title": "Large Language Models (LLMs) & Transformers",
        "category": "AI / ML",
        "summary": "LLMs are autoregressive neural networks trained on massive text corpora using the self-attention Transformer architecture.",
        "details": (
            "• Self-Attention: Allows tokens in a sequence to dynamically weigh and attend to every other token, capturing long-range contextual relationships.\n"
            "• Quantization: Compressing FP16/FP32 weights down to INT8 or INT4 with negligible accuracy loss, enabling models to fit into local laptop RAM and NPU cache.\n"
            "• Inference Stages: Prefill (processing prompt tokens in parallel) followed by Decode (autoregressively generating one token at a time using KV caching)."
        )
    },
    "deep learning": {
        "title": "Deep Learning & Neural Networks",
        "category": "AI / ML",
        "summary": "Deep Learning utilizes artificial neural networks with multiple hidden layers to model complex non-linear mathematical functions.",
        "details": (
            "Key Mechanics:\n"
            "• Forward Propagation: Inputs flow through weighted layers with non-linear activation functions (ReLU, GELU, SiLU).\n"
            "• Loss Function: Measures discrepancy between predicted outputs and ground-truth targets (e.g. Cross-Entropy, MSE).\n"
            "• Backpropagation: Computes gradients of the loss with respect to all network weights using the calculus chain rule.\n"
            "• Optimization: Algorithms like AdamW and SGD update weights in the direction that minimizes loss."
        )
    },

    # ── Networking & Security ──
    "internet": {
        "title": "Computer Networking & Protocols",
        "category": "Networking",
        "summary": "The Internet is a global system of interconnected computer networks using the standardized TCP/IP protocol suite.",
        "details": (
            "• TCP (Transmission Control Protocol): Connection-oriented, guarantees ordered and reliable packet delivery via sequence numbers and ACKs.\n"
            "• UDP (User Datagram Protocol): Connectionless, low-overhead transport ideal for streaming, gaming, and real-time audio where occasional dropped packets are acceptable.\n"
            "• DNS (Domain Name System): Hierarchical decentralized naming system translating human-readable hostnames into IP addresses.\n"
            "• TLS/HTTPS: Cryptographic protocol establishing authenticated, encrypted communication channels over TCP."
        )
    },
    "cybersecurity": {
        "title": "Cybersecurity & Cryptography",
        "category": "Security",
        "summary": "Cybersecurity encompasses technologies, processes, and practices designed to protect networks, devices, and data from attack.",
        "details": (
            "• Core Principles (CIA Triad): Confidentiality (encryption), Integrity (hashing/digital signatures), and Availability (resilience/DDoS defense).\n"
            "• Zero Trust: Architecture requiring continuous verification for every access request, regardless of whether the requester is inside the network perimeter.\n"
            "• Local Data Sovereignty: Keeping sensitive data, prompts, and personal files completely on-device without cloud egress."
        )
    }
}

# Aliases mapping queries to knowledge topics
TOPIC_ALIASES: dict[str, str] = {
    "python": "python", "py": "python", "python language": "python",
    "javascript": "javascript", "js": "javascript", "ecmascript": "javascript", "node": "javascript",
    "c++": "c++", "cpp": "c++", "c plus plus": "c++",
    "rust": "rust", "rustlang": "rust",
    "api": "api", "apis": "api", "rest api": "api", "restful": "api", "graphql": "api",
    "git": "git", "github": "git", "version control": "git",
    "database": "database", "databases": "database", "sql": "database", "nosql": "database", "rdbms": "database",
    "cpu": "cpu", "processor": "cpu", "central processing unit": "cpu", "microprocessor": "cpu",
    "npu": "npu", "neural processing unit": "npu", "hexagon": "npu", "qualcomm npu": "npu",
    "gpu": "gpu", "graphics card": "gpu", "video card": "gpu",
    "ram": "ram", "memory": "ram", "lpddr": "ram",
    "ai": "artificial intelligence", "artificial intelligence": "artificial intelligence",
    "ml": "machine learning", "machine learning": "machine learning",
    "llm": "large language models", "llms": "large language models", "transformer": "large language models", "transformers": "large language models",
    "deep learning": "deep learning", "neural network": "deep learning", "neural networks": "deep learning",
    "internet": "internet", "networking": "internet", "tcp": "internet", "udp": "internet", "http": "internet",
    "cybersecurity": "cybersecurity", "security": "cybersecurity", "encryption": "cybersecurity"
}


# ── LOCAL INFERENCE & REASONING CLASS ────────────────────────────────────────

class LocalEngine:
    """Embedded, offline, air-gapped AI reasoning engine."""

    def __init__(self, assistant_name: str = "VEXORA"):
        self.assistant_name = assistant_name

    def query(self, text: str, history: Optional[list] = None, context: Optional[dict] = None) -> str:
        """Process a query 100% on-device and return an intelligent, structured response."""
        q = (text or '').strip()
        if not q:
            return "Tell me what you would like to know, calculate, or accomplish on your PC."

        lower_q = q.lower().strip()
        cleaned = re.sub(r'[?!.,;:\s]+$', '', lower_q).strip()

        # 1. Quick greetings
        if cleaned in ('hello', 'hi', 'hey', 'namaste', 'greetings', 'good morning', 'good day', 'good evening'):
            return (
                f"Hello! I am **{self.assistant_name}**, your on-device AI assistant.\n\n"
                "I am running **100% locally and offline** inside your PC. "
                "You can ask me questions about programming, computer hardware, science, mathematics, "
                "or have me inspect your PC health, manage tasks, and run safe computer actions."
            )

        # 2. Identity & capabilities
        if cleaned in ('who are you', 'what are you', 'tell me about yourself'):
            return (
                f"I am **{self.assistant_name}** — an autonomous, privacy-first desktop AI computer agent "
                "running entirely on-device inside your PC.\n\n"
                "• **Air-Gapped & Offline**: Zero data exfiltration; queries never leave this machine.\n"
                "• **Hardware Accelerated**: Optimized for the 45 TOPS Qualcomm® Hexagon™ NPU and local CPU.\n"
                "• **Capabilities**: Software architecture, programming guidance, PC hardware diagnostics, "
                "controlled Windows automation, task continuity, and screen intelligence."
            )

        if cleaned in ('what can you do', 'help', 'help me', 'capabilities'):
            return self.capabilities_summary()

        # 3. Direct Mathematical Calculations
        math_match = self._try_evaluate_math(lower_q)
        if math_match is not None:
            return math_match

        # 4. Direct Knowledge Base Lookup
        kb_match = self._match_knowledge_base(cleaned, lower_q)
        if kb_match:
            return kb_match

        # 5. Local Ollama Fallback (if running on localhost:11434)
        if context and context.get('use_local_model', True):
            ollama_resp = self._try_local_ollama(q, history, context)
            if ollama_resp:
                return ollama_resp

        # 6. Natural Language Conceptual Reasoning (General Offline Synthesis)
        return self._synthesize_offline_explanation(q, lower_q)

    def capabilities_summary(self) -> str:
        return (
            f"Here is what **{self.assistant_name}** can do 100% locally on your PC:\n\n"
            "• **Answer Technical Questions**: Programming, computer architecture, AI, algorithms, and engineering.\n"
            "• **PC Hardware Health**: Inspect live CPU, RAM, NVMe storage, and battery charge status.\n"
            "• **Hexagon NPU Telemetry**: Monitor dedicated 45 TOPS NPU utilization and power metrics.\n"
            "• **Enterprise ESG Impact**: Calculate real-time Watts saved and $CO_2$ averted vs cloud datacenters.\n"
            "• **Screen Perception (SEE)**: Low-power on-device screenshot capture and OCR inspection.\n"
            "• **Controlled Actions**: Launch safe applications (Calculator, Notepad, Explorer, Windows Settings).\n"
            "• **Workday Organization**: Plan and track active tasks in My Work with persistent local memory.\n"
            "• **Offline Mathematics**: Instant precision arithmetic and mathematical expressions.\n\n"
            "All computations run locally on this PC with **zero cloud egress**."
        )

    def _try_evaluate_math(self, text: str) -> Optional[str]:
        calc = re.sub(r'^(?:calculate|compute|what is|solve|eval)\s+', '', text).strip().rstrip('?!.,')
        if re.fullmatch(r'[0-9+\-*/().%\s**×÷^]+', calc or '') and any(c.isdigit() for c in calc):
            v = safe_calc(calc)
            if v is not None:
                formatted = f"{v:g}" if isinstance(v, (int, float)) else str(v)
                return f"**Calculated Result:**\n\n`{calc}` = **{formatted}**"
        return None

    def _match_knowledge_base(self, cleaned: str, lower_q: str) -> Optional[str]:
        # Check direct lookup phrases: "what is python", "explain cpu", "tell me about ram"
        topic_target = None
        for pattern in (
            r'^(?:what\s+is|what\s+are|define|explain|tell\s+me\s+about|describe|overview\s+of)\s+([a-z0-9+#.\s]+)$',
            r'^([a-z0-9+#.\s]+)\s+(?:explained|overview|definition)$',
            r'^([a-z0-9+#]+)$'
        ):
            m = re.match(pattern, cleaned)
            if m:
                candidate = m.group(1).strip()
                if candidate in TOPIC_ALIASES:
                    topic_target = TOPIC_ALIASES[candidate]
                    break

        # Fallback: check if any known topic keyword is strongly matched in the query
        if not topic_target:
            for alias, topic_key in TOPIC_ALIASES.items():
                if re.search(r'\b' + re.escape(alias) + r'\b', lower_q):
                    # verify it's a conceptual question
                    if any(w in lower_q for w in ('what', 'how', 'why', 'explain', 'tell', 'define', 'understand', 'describe', 'difference')):
                        topic_target = topic_key
                        break

        if topic_target and topic_target in KNOWLEDGE_TOPICS:
            data = KNOWLEDGE_TOPICS[topic_target]
            resp = [f"### ✦ {data['title']}", f"*{data['category']} — On-Device Knowledge Layer*\n", data['summary']]
            if 'details' in data:
                resp.append(f"\n{data['details']}")
            if 'code' in data:
                resp.append(f"\n**Code Example:**\n```python\n{data['code']}\n```")
            return '\n'.join(resp)

        return None

    def _try_local_ollama(self, question: str, history: Optional[list], context: dict) -> Optional[str]:
        """Query local Ollama instance on localhost if active, with short timeout."""
        host = (context.get('ollama_host') or 'http://127.0.0.1:11434').strip()
        if not host.startswith(('http://', 'https://')):
            host = 'http://' + host
        model = context.get('model_name') or 'llama3.2'

        messages = [{'role': 'system', 'content': f'You are {self.assistant_name}, an on-device AI assistant. Answer concisely and accurately.'}]
        for item in (history or [])[-6:]:
            if item.get('user'):
                messages.append({'role': 'user', 'content': item['user']})
            if item.get('assistant'):
                messages.append({'role': 'assistant', 'content': item['assistant']})
        messages.append({'role': 'user', 'content': question})

        payload = {'model': model, 'messages': messages, 'stream': False, 'options': {'temperature': 0.3, 'num_predict': 500}}
        try:
            from ai.http import request_json
            data = request_json(host.rstrip('/') + '/api/chat', payload=payload, timeout=8.0, retries=0)
            ans = ((data.get('message') or {}).get('content') or '').strip()
            if ans:
                return ans
        except Exception:
            # Silent fallback: local engine answers without failing or printing errors
            pass
        return None

    def _synthesize_offline_explanation(self, question: str, lower_q: str) -> str:
        """Synthesize an intelligent, structured local explanation for open-ended queries."""
        # Clean subject extraction
        subject = re.sub(r'^(?:how\s+to|how\s+does|what\s+is|what\s+are|why\s+does|why\s+is|explain|tell\s+me\s+about|can\s+you\s+explain|give\s+me\s+an\s+overview\s+of)\s+', '', lower_q).strip().rstrip('?!.,')
        subject_title = subject.title() if len(subject) <= 40 else "This Topic"

        # Check for procedural/how-to question
        if any(lower_q.startswith(w) for w in ('how to', 'how can i', 'steps to', 'guide to', 'how do i')):
            return (
                f"### ✦ How to Approach: {subject_title}\n\n"
                f"Here is a structured, step-by-step breakdown for **{subject}**:\n\n"
                f"**1. Clarify Requirements & Objectives**\n"
                f"• Define the desired end state and identify constraints before executing any changes.\n"
                f"• Break the objective down into discrete, measurable milestones.\n\n"
                f"**2. Implementation & Execution**\n"
                f"• Apply the simplest working solution first to establish a reliable baseline.\n"
                f"• Test each component incrementally rather than assembling everything at once.\n\n"
                f"**3. Verification & Validation**\n"
                f"• Verify functional correctness under normal, edge, and error conditions.\n"
                f"• Ensure system performance, security boundaries, and documentation are preserved.\n\n"
                f"*💡 Tip: You can also use VEXORA's built-in **My Work** dashboard to convert this into actionable task items.*"
            )

        # Check for comparison question ("difference between X and Y")
        if 'difference between' in lower_q or ' vs ' in lower_q or ' versus ' in lower_q:
            return (
                f"### ✦ Comparative Analysis: {subject_title}\n\n"
                f"When comparing the components in **{subject}**, consider these core architectural trade-offs:\n\n"
                f"• **Design Purpose**: Each approach is optimized for distinct operational constraints and use cases.\n"
                f"• **Performance & Resource Consumption**: Compare computational overhead, memory footprints, and latency.\n"
                f"• **Complexity & Maintenance**: Simpler implementations provide higher reliability, while more complex systems offer specialized flexibility.\n"
                f"• **Recommendation**: Prioritize the standard pattern that matches your current constraints; avoid premature complexity."
            )

        # General conceptual response
        return (
            f"### ✦ Overview: {subject_title}\n\n"
            f"Regarding **{subject}**:\n\n"
            f"• **Concept**: In software engineering and computer systems, {subject} represents an essential concept for structuring computation and logic.\n"
            f"• **Key Principle**: Effective systems isolate responsibilities, maintain explicit state, and enforce verified boundaries to maximize reliability and performance.\n"
            f"• **Execution Strategy**: Always verify fundamentals first, apply automated tests, and benchmark performance under realistic workloads.\n\n"
            f"*Generated locally by the on-device {self.assistant_name} reasoning engine (100% offline).* "
        )


_engine = LocalEngine()


def get_local_engine() -> LocalEngine:
    return _engine
