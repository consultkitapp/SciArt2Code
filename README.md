# SciArt2Code
A project focused on Local LLM powered scientific article to computational method implementation.

**Local Scientific Agent: Offline Paper-to-Code Implementation**

This project is a strictly **Local LLM Only** pipeline designed to ingest scientific research papers, extract methodologies, and autonomously implement them into functional Python code within secure, isolated Podman sandboxes.

This repository was purpose-built to endow researchers and scientists with resilient, local scientific research tools. Due to increasing geopolitical risks surrounding the access, privacy, and availability of online AI services, relying on cloud-based frontier models for sensitive research is becoming a vulnerability. By leveraging locally hosted orchestrator and coder models via `llama.cpp`, this tool ensures that your scientific IP and execution environments remain entirely offline, uncensored, and under your absolute control.

*Note: For users operating without strict offline requirements or those seeking to leverage advanced cloud-based frontier LLMs (e.g., GPT-4o, Claude 3.5 Sonnet), there are other excellent open-source projects available on GitHub, such as **Paper2Code**, **Deepcode**, and **Paper2Agent**.*

---

### Missing Features & Roadmap

The current pipeline is highly functional for text-based algorithmic implementation, but it has several known limitations that will be addressed in future releases:

* **Multimodal Parsing:** The current `pypdf` extraction ignores charts, plots, and complex mathematical block equations (LaTeX). Visual methodology extraction is not yet supported.
* **Dynamic Dependency Resolution:** If the Coder Agent hallucinates a package name or requests a library with strict system-level C++ compilation requirements, the sandbox execution will simply fail without allowing the agent to self-correct and try alternative libraries.
* **Multi-File State Tracking:** The current workflow handles standard single-file scripts and an accompanying `requirements.txt`. Complex repository generation involving deep modular directory structures is prone to context-loss.
* **Cross-Paper Memory Synthesis:** While ChromaDB currently stores single-paper methodologies, the Orchestrator cannot yet synthesize contradicting methods across multiple papers during a single run.
* **Automated Model Lifecycle Management:** The user must manually boot the `llama-server` instances on ports 8080 and 8081 before running the pipeline. Automatic spawning and VRAM allocation of models is not yet built into the main orchestrator script.
