# SciArt2Code

**Local Scientific Agent: Secure Paper-to-Code Implementation**

This project is a local-LLM-driven pipeline designed to ingest scientific research papers, extract methodologies, and autonomously implement them into functional Python code within isolated Podman sandboxes. Generated code by this first alpha version is more akin to pseudocode / code scaffold rather than production ready code. The sandboxed executions may fail due to missing python imports and for other reasons.

This repository was purpose-built to endow researchers and scientists with resilient, locally-hosted scientific research tools. Due to increasing geopolitical risks surrounding the access, privacy, and availability of online AI services, relying on cloud-based frontier models for sensitive research is becoming a vulnerability. By leveraging local orchestrator and coder models via `llama.cpp`, this tool ensures that your scientific IP and execution environments remain uncensored and under your absolute control.

*Note: For users operating without strict privacy requirements or those seeking to leverage advanced cloud-based frontier LLMs (e.g., GPT-4o, Claude 3.5 Sonnet), there are other excellent open-source projects available on GitHub, such as **[Paper2Code](https://github.com/going-doer/paper2code)**, **[DeepCode](https://github.com/HKUDS/DeepCode)**, and **[Paper2Agent](https://github.com/jmiao24/Paper2Agent)**.*

Here are the updated step-by-step instructions, incorporating the explicit manual folder creation required before running the pipeline.

### 1. System Prerequisites

Before starting, ensure your host machine has the following installed:

* **Python 3.10+**
* **Podman:** Required for creating the isolated execution sandboxes.


* **llama.cpp (`llama-server`):** Compiled and accessible in your project root to serve the local LLMs.



### 2. Prepare the Python Environment

Create a clean virtual environment and install the strictly pinned dependencies.

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

```

### 3. Initialize the Base Workspace & Sandboxes

Run the sandbox setup script first. This will automatically generate the base `agent_workspace/` directory, pull the Python image, and launch the 4 concurrent background containers (`qwen-sandbox-1` through `qwen-sandbox-4`).

```bash
chmod +x setup_sandboxes.sh
./setup_sandboxes.sh

```

### 4. Create the Manual Input Folders

While the scripts handle output directories, you must manually create the folders for your models and papers inside the newly generated workspace.

```bash
mkdir -p ./agent_workspace/models/Qwen3.6-35B-A3B-GGUF/
mkdir -p ./agent_workspace/models/Qwen3.5-9B-GGUF/
mkdir -p ./agent_workspace/papers/

```

### 5. Download the Local LLM Weights

The system relies on two specific GGUF models. You need to download them and place them in the exact directory structure expected by the `start_servers.sh` script.

1. Download the Orchestrator model (`Qwen3.6-35B-A3B-Q6_K.gguf`) and place it inside `./agent_workspace/models/Qwen3.6-35B-A3B-GGUF/`.


2. Download the Coder model (`Qwen3.5-9B-Q8_0.gguf`) and place it inside `./agent_workspace/models/Qwen3.5-9B-GGUF/`.



### 6. Prepare Your Scientific Papers

Copy the PDF files of the research papers you want to analyze and paste them into the `./agent_workspace/papers/` folder.

### 7. Boot the Local LLM Servers

Run the server startup script. This will launch the Orchestrator model on port 8080 and the Coder model on port 8081.

```bash
chmod +x start_servers.sh
./start_servers.sh

```

Note: This script will run the servers in the background and pipe their output to `orchestrator.log` and `agents.log`. Ensure your machine has sufficient VRAM (~40GB total) to host both models simultaneously.

### 8. Run the Application

You can interact with the system using either the Command Line Interface or the Web GUI.

**Option A: Command Line Interface**
Use this for processing a single paper interactively.

```bash
python main.py

```

When prompted, enter the path to your PDF (e.g., `./agent_workspace/papers/paper1.pdf`).

**Option B: Streamlit Web Dashboard**
Use this to utilize the 4 concurrent Podman pods and process multiple papers in parallel.

```bash
streamlit run dashboard.py

```

This will open the dashboard in your web browser. From there, you can specify the paths to multiple PDFs and click "Run Concurrent Analysis" to watch the real-time extraction and execution.


**Dynamic Context Resolution via RivalSearch MCP**
While the core intelligence and code execution remain local, the pipeline features a seamless integration with the **RivalSearch MCP** (Model Context Protocol) server. Scientific papers frequently lack complete context—referencing undocumented libraries, obscure concepts, or mathematical constants without explanation. Rather than hallucinating missing information, the Analyst Agent utilizes the RivalSearch MCP tools to dynamically perform web research, fetching accurate, up-to-date context to ensure the final generated code is highly accurate. The current integration of RivalSearch MCP sends search queries to an external MCP server. If you want to change MCP tool or self host it or disable it completely, you can modify the `agents.py` file.

---

## Option 1: Disable MCP Completely (Strictly Offline)

If you want a 100% offline workflow with zero web search capabilities, you can disable the MCP tool discovery and pass an empty list of tools to `create_react_agent`.

### Code Changes in `agents.py`

1. **Update the prompt** to remove instructions about using `web_search`.


2. **Bypass tool discovery** in `DocumentAnalysisAgent.initialize()`.



```python
class DocumentAnalysisAgent:
    def __init__(self):
        # Remove web search instructions from the prompt
        self.prompt = """
        You are a Senior Research Scientist specializing in computational methodology analysis.
        Your task is to analyze scientific papers and extract implementable methodologies.

        OUTPUT FORMAT:
        Provide a structured analysis with clear sections.
        1. METHODOLOGY SUMMARY
        2. KEY COMPONENTS
        3. IMPLEMENTATION REQUIREMENTS
        4. PSEUDOCODE

        Be precise and technical. Focus on what can be implemented in code.
        """
        self.agent = None

    async def initialize(self):
        """Initialize agent without external tools."""
        # Pass an empty tool list to disable external search
        self.agent = create_react_agent(
            client_orchestrator,
            []
        )

```

---

## Option 2: Host or Point to a Local MCP Server

If you want to keep the MCP architecture but run your own local MCP server (for example, using FastMCP serving a local database or local search engine on `http://localhost:8000/mcp`), you only need to update the URL variable.

### Code Changes in `agents.py`

Update `MCP_SERVER_URL` at the top of `agents.py` to point to your local endpoint:

```python
# Point to your local FastMCP instance instead of the cloud endpoint
MCP_SERVER_URL = "http://localhost:8000/mcp"

```

---

## Option 3: Replace MCP with an Alternative Search Tool

If you want to replace the current MCP with a standard Python search library (like DuckDuckGo Search or Tavily), you can wrap it as a LangChain tool and pass it directly to `create_react_agent`.

### Step 1: Install a local search package

```bash
pip install duckduckgo-search langchain-community

```

### Step 2: Update `agents.py`

Replace the MCP tool discovery with the standard LangChain search tool:

```python
from langchain_community.tools import DuckDuckGoSearchRun

class DocumentAnalysisAgent:
    def __init__(self):
        # Update prompt to mention DuckDuckGo search
        self.prompt = """
        You are a Senior Research Scientist specializing in computational methodology analysis.
        Your task is to analyze scientific papers and extract implementable methodologies.

        TOOLS AVAILABLE:
        You have access to 'duckduckgo_search'.
        If the paper references a specific library, concept, or mathematical constant not explained
        clearly in the text, use this tool to find accurate information. Do NOT hallucinate.

        OUTPUT FORMAT:
        Provide a structured analysis with clear sections.
        1. METHODOLOGY SUMMARY
        2. KEY COMPONENTS
        3. IMPLEMENTATION REQUIREMENTS
        4. PSEUDOCODE
        """
        self.agent = None

    async def initialize(self):
        """Initialize agent with local/alternative tools."""
        # Replace MCP tools with DuckDuckGo Search
        search_tool = DuckDuckGoSearchRun()

        self.agent = create_react_agent(
            client_orchestrator,
            [search_tool]
        )

```

### Missing Features & Roadmap

The current pipeline is highly functional for text-based algorithmic implementation, but it has several known limitations that will be addressed in future releases:

* **Multimodal Parsing:** The current `pypdf` extraction ignores charts, plots, and complex mathematical block equations (LaTeX). Visual methodology extraction is not yet supported.
* **Dynamic Dependency Resolution:** If the Coder Agent hallucinates a package name or requests a library with strict system-level C++ compilation requirements, the sandbox execution will simply fail without allowing the agent to self-correct and try alternative libraries.
* **Multi-File State Tracking:** The current workflow handles standard single-file scripts and an accompanying `requirements.txt`. Complex repository generation involving deep modular directory structures is prone to context-loss.
* **Cross-Paper Memory Synthesis:** While ChromaDB currently stores single-paper methodologies, the Orchestrator cannot yet synthesize contradicting methods across multiple papers during a single run.
* **Automated Model Lifecycle Management:** The user must manually boot the `llama-server` instances on ports 8080 and 8081 before running the pipeline. Automatic spawning and VRAM allocation of models is not yet built into the main orchestrator script.
