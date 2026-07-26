import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Any

from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from fastmcp import Client

# Import the newly modernized memory module
from memory import AgentMemory

# Initialize OpenAI clients pointing to local instances
client_orchestrator = ChatOpenAI(
    base_url="http://localhost:8080/v1",
    model="qwen3.5-35b-a3b",
    api_key="local",
    temperature=0.2
)
client_agent = ChatOpenAI(
    base_url="http://localhost:8081/v1",
    model="qwen3.5-9b",
    api_key="local",
    temperature=0.3
)

# MCP Configuration
MCP_SERVER_URL = "https://rivalsearchmcp.fastmcp.app/mcp"


class MCPTool(BaseTool):
    """
    A dynamic wrapper that connects to the RivalSearch MCP server
    and executes specific tools defined by the server.
    """
    name: str
    description: str
    url: str

    def _run(self, **kwargs) -> str:
        """Execute the tool call synchronously (fallback)."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Execute the tool call asynchronously."""
        try:
            async with Client(self.url) as session:
                # Call the tool on the server
                result = await session.call_tool(self.name, arguments=kwargs)

                # Extract text content from result blocks
                if isinstance(result, list):
                    return " ".join([block.text for block in result if hasattr(block, 'text')])
                return str(result)
        except Exception as e:
            return f"ERROR: Failed to execute MCP tool '{self.name}': {str(e)}"


class MCPClientManager:
    """Manages the connection and tool discovery for the MCP server."""

    def __init__(self, url: str):
        self.url = url
        self.tools: list[BaseTool] = []

    async def discover_and_bind(self):
        """Fetch available tools from the MCP server and bind them to LangChain."""
        try:
            async with Client(self.url) as session:
                mcp_tools_response = await session.list_tools()

                for tool in mcp_tools_response:
                    lang_tool = MCPTool(
                        name=tool.name,
                        description=tool.description,
                        url=self.url
                    )
                    self.tools.append(lang_tool)

                print(f"[System] Connected to MCP Server. Loaded {len(self.tools)} tools.")
        except Exception as e:
            print(f"[System] Failed to connect to MCP Server: {str(e)}")

    def get_tools(self) -> list[BaseTool]:
        return self.tools


class DocumentAnalysisAgent:
    """
    Agent responsible for analyzing scientific papers and extracting methodologies.
    Uses MCP to perform web research if the paper lacks context.
    """

    def __init__(self):
        self.mcp_manager = MCPClientManager(MCP_SERVER_URL)

        self.prompt = """
        You are a Senior Research Scientist specializing in computational methodology analysis.
        Your task is to analyze scientific papers and extract implementable methodologies.

        TOOLS AVAILABLE:
        You have access to 'web_search' and other tools via the RivalSearch MCP server.
        If the paper references a specific library, concept, or mathematical constant not explained
        clearly in the text, you MUST use the 'web_search' tool to find accurate, up-to-date information.
        Do NOT hallucinate missing context.

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
        """Async initialization to discover tools and create the graph agent."""
        await self.mcp_manager.discover_and_bind()
        mcp_tools = self.mcp_manager.get_tools()

        # VERSION-PROOF FIX: Initialize without the volatile parameter
        self.agent = create_react_agent(
            client_orchestrator,
            mcp_tools
        )

    async def analyze(self, state: dict) -> dict:
        """Analyze the paper text."""
        if not self.agent:
            await self.initialize()

        paper_text = state.get("paper_text", "")
        metadata = state.get("paper_metadata", {})

        # Prepare the input
        input_text = f"Analyze the following paper:\n\nMetadata:\n{json.dumps(metadata)}\n\nPaper Content:\n{paper_text[:80000]}"

        print("[Analyst] Starting analysis (searching if necessary)...")

        # VERSION-PROOF FIX: Pass the system prompt directly in the message array
        messages = [
            SystemMessage(content=self.prompt),
            HumanMessage(content=input_text)
        ]

        # Use ainvoke for async execution
        result = await self.agent.ainvoke({"messages": messages})

        # Extract the final answer (last message)
        final_response = result["messages"][-1].content

        # Update state with structured data
        state["methodology_summary"] = self._extract_section(final_response, "METHODOLOGY SUMMARY")
        state["key_components"] = self._extract_section(final_response, "KEY COMPONENTS").split("\n")
        state["implementation_requirements"] = self._extract_section(final_response, "IMPLEMENTATION REQUIREMENTS").split("\n")

        return state
    # async def initialize(self):
    #     """Async initialization to discover tools and create the graph agent."""
    #     await self.mcp_manager.discover_and_bind()
    #     mcp_tools = self.mcp_manager.get_tools()
    #
    #     # Modern langgraph uses `state_modifier` instead of `prompt`
    #     self.agent = create_react_agent(
    #         model=client_orchestrator,
    #         tools=mcp_tools,
    #         state_modifier=self.prompt
    #     )
    #
    # async def analyze(self, state: dict) -> dict:
    #     """Analyze the paper text."""
    #     if not self.agent:
    #         await self.initialize()
    #
    #     paper_text = state.get("paper_text", "")
    #     metadata = state.get("paper_metadata", {})
    #
    #     # Prepare the input
    #     input_text = f"Analyze the following paper:\n\nMetadata:\n{json.dumps(metadata)}\n\nPaper Content:\n{paper_text[:80000]}"
    #
    #     print("[Analyst] Starting analysis (searching if necessary)...")
    #     # Use ainvoke for async execution
    #     result = await self.agent.ainvoke({"messages": [HumanMessage(content=input_text)]})
    #
    #     # Extract the final answer (last message)
    #     final_response = result["messages"][-1].content
    #
    #     # Update state with structured data
    #     state["methodology_summary"] = self._extract_section(final_response, "METHODOLOGY SUMMARY")
    #     state["key_components"] = self._extract_section(final_response, "KEY COMPONENTS").split("\n")
    #     state["implementation_requirements"] = self._extract_section(final_response, "IMPLEMENTATION REQUIREMENTS").split("\n")
    #
    #     return state

    def _extract_section(self, text: str, section_title: str) -> str:
        """Simple helper to extract text between section headers."""
        start_idx = text.find(section_title)
        if start_idx == -1:
            return ""
        return text[start_idx:].strip()

class CodeImplementationAgent:
    """
    Agent responsible for generating code based on the Analyst's summary.
    """
    def __init__(self):
        self.llm = client_agent
        self.prompt = """
        You are a Senior Python Developer.
        Implement the methodology described in the following analysis.

        ## METHODOLOGY SUMMARY
        {methodology_summary}

        ## KEY COMPONENTS
        {key_components}

        ## IMPLEMENTATION REQUIREMENTS
        {implementation_requirements}

        OUTPUT FORMAT:
        You MUST output your code using the following XML format for EVERY file you create.

        CRITICAL DEPENDENCY RULE:
        You MUST generate a `requirements.txt` file. Review every single `import` statement in your Python code. If the library is NOT a standard Python built-in (e.g., Pyomo, Numpy, Pandas, SciPy, Torch), it MUST be listed in your `requirements.txt` file. The code will execute in an empty sandbox and WILL CRASH if you forget to list a dependency.

        <file path="requirements.txt">
        pyomo
        numpy
        pandas
        </file>

        <file path="filename.py">
        [code here]
        </file>

        Do not use markdown backticks. Only use the XML tags.
        Ensure production-ready quality, type hints, and error handling.
        """
# class CodeImplementationAgent:
#     """
#     Agent responsible for generating code based on the Analyst's summary.
#     """
#     # def __init__(self):
#     #     self.llm = client_agent
#     #     self.prompt = """
#     #     You are a Senior Python Developer.
#     #     Implement the methodology described in the following analysis.
#     #
#     #     ## METHODOLOGY SUMMARY
#     #     {methodology_summary}
#     #
#     #     ## KEY COMPONENTS
#     #     {key_components}
#     #
#     #     ## IMPLEMENTATION REQUIREMENTS
#     #     {implementation_requirements}
#     #
#     #     OUTPUT FORMAT:
#     #     You MUST output your code using the following XML format for EVERY file you create:
#     #
#     #     <file path="filename.py">
#     #     [code here]
#     #     </file>
#     #
#     #     Do not use markdown backticks. Only use the XML tags.
#     #     Ensure production-ready quality, type hints, and error handling.
#     #     """
#     def __init__(self):
#         self.llm = client_agent
#         self.prompt = """
#         You are a Senior Python Developer.
#         Implement the methodology described in the following analysis.
#
#         ## METHODOLOGY SUMMARY
#         {methodology_summary}
#
#         ## KEY COMPONENTS
#         {key_components}
#
#         ## IMPLEMENTATION REQUIREMENTS
#         {implementation_requirements}
#
#         OUTPUT FORMAT:
#         You MUST output your code using the following XML format for EVERY file you create.
#         You MUST include a `requirements.txt` file listing all external Python libraries needed.
#
#         <file path="requirements.txt">
#         numpy>=1.24.0
#         pandas
#         scipy
#         </file>
#
#         <file path="filename.py">
#         [code here]
#         </file>
#
#         Do not use markdown backticks. Only use the XML tags.
#         Ensure production-ready quality, type hints, and error handling.
#         """
    async def implement(self, state: dict) -> dict:
        prompt = self.prompt.format(
            methodology_summary=state.get("methodology_summary", ""),
            key_components="\n".join(state.get("key_components", [])),
            implementation_requirements="\n".join(state.get("implementation_requirements", []))
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a coder."),
            HumanMessage(content=prompt)
        ])
        state["code"] = response.content
        return state


class WorkflowOrchestrator:
    def __init__(self):
        self.doc_agent = DocumentAnalysisAgent()
        self.code_agent = CodeImplementationAgent()
        # Initialize our modernized memory module
        self.memory = AgentMemory()

    async def run(self, pdf_path: str) -> dict:
        from document_parser import DocumentParser

        # 1. Parse Document
        print("[System] Parsing document...")
        parser = DocumentParser()
        paper_text = parser.parse(pdf_path)

        state = {
            "paper_text": paper_text,
            "paper_metadata": parser.extract_metadata(pdf_path),
            "methodology_summary": "",
            "key_components": [],
            "implementation_requirements": [],
            "code": ""
        }

        # 2. Analyst Phase
        print("\n[Orchestrator] Analyst Agent is working...")
        state = await self.doc_agent.analyze(state)

        # 3. Coder Phase
        print("\n[Orchestrator] Coding Agent is working...")
        state = await self.code_agent.implement(state)

        # 4. Memory Phase: Store the methodology for future recall
        if state.get("methodology_summary"):
            print("\n[Orchestrator] Committing methodology to memory...")
            await self.memory.remember(
                text=state["methodology_summary"],
                metadata={
                    "source": os.path.basename(pdf_path),
                    "type": "methodology_extraction"
                }
            )

        return state
