import streamlit as st
import asyncio
import os
import json
import re
from pathlib import Path

from agents import WorkflowOrchestrator
from sandbox import execute_in_sandbox, install_requirements

st.set_page_config(page_title="AI Research Implementation System", layout="wide")

WORKSPACE_DIR = Path("./agent_workspace").resolve()
# Define our 4 concurrent sandbox containers
CONTAINER_POOL = ["qwen-sandbox-1", "qwen-sandbox-2", "qwen-sandbox-3", "qwen-sandbox-4"]

async def process_paper(pdf_path: str, container_name: str, status_container):
    """Wraps the orchestrator execution for a single paper."""
    orchestrator = WorkflowOrchestrator()

    with status_container:
        st.info(f"📄 [{container_name}] **Parsing and Analyzing:** `{os.path.basename(pdf_path)}`...")

    final_state = await orchestrator.run(pdf_path)
    paper_stem = Path(pdf_path).stem

    code_string = final_state.get("code", "")
    matches = re.findall(r'<file path="(.*?)">\s*(.*?)\s*</file>', code_string, re.DOTALL)

    execution_results = {}
    saved_files = []
    has_requirements = False

    if matches:
        for filepath, code in matches:
            isolated_filepath = f"{paper_stem}/{filepath}"
            full_path = WORKSPACE_DIR / isolated_filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(code, encoding="utf-8")
            saved_files.append({"path": isolated_filepath, "code": code})

            if filepath.lower() == "requirements.txt":
                has_requirements = True

        python_files = [m for m in matches if m[0].endswith('.py')]

        if python_files:
            target_file = f"{paper_stem}/{python_files[0][0]}"
            target_code = python_files[0][1]

            if has_requirements:
                req_file = f"{paper_stem}/requirements.txt"
                with status_container:
                    st.warning(f"📦 [{container_name}] **Installing dependencies from `{req_file}`...**")

                install_output = await install_requirements(req_file, container_name)
                execution_results["install_output"] = install_output

                if "ERROR" in install_output:
                    execution_results["file"] = target_file
                    execution_results["output"] = "Execution aborted due to dependency installation failure."
                    return final_state, saved_files, execution_results

            with status_container:
                st.info(f"🐳 [{container_name}] **Executing `{target_file}`...**")

            exec_output = await execute_in_sandbox(target_file, target_code, container_name)
            execution_results["file"] = target_file
            execution_results["output"] = exec_output

            result_file = WORKSPACE_DIR / paper_stem / "execution_results.json"
            result_file.write_text(json.dumps(execution_results, indent=2), encoding="utf-8")

    return final_state, saved_files, execution_results

async def worker(pdf_path: str, queue: asyncio.Queue, status_ph, result_ph):
    """Worker task that grabs a container from the queue and processes a paper."""
    container_name = await queue.get()
    try:
        state, saved_files, exec_results = await process_paper(pdf_path, container_name, status_ph)

        # Render the UI once data is returned
        with result_ph:
            tab_methodology, tab_code, tab_sandbox = st.tabs(["Methodology", "Code", "Sandbox"])

            with tab_methodology:
                st.markdown("### Methodology Summary")
                st.info(state.get("methodology_summary", "No summary generated."))
                st.markdown("### Key Components")
                for comp in state.get("key_components", []):
                    if comp.strip(): st.markdown(f"- {comp}")
                st.markdown("### Implementation Requirements")
                for req in state.get("implementation_requirements", []):
                    if req.strip(): st.markdown(f"- {req}")

            with tab_code:
                if saved_files:
                    for sf in saved_files:
                        st.markdown(f"**Saved as:** `{sf['path']}`")
                        st.code(sf['code'], language="python")
                else:
                    st.warning("No code generated.")

            with tab_sandbox:
                if exec_results:
                    if "install_output" in exec_results:
                        with st.expander("Dependency Installation Logs"):
                            st.code(exec_results["install_output"], language="text")
                    st.markdown(f"**Executed File:** `{exec_results.get('file', '')}`")
                    output_text = exec_results.get('output', '')
                    if "ERROR" in output_text:
                        st.error(output_text)
                    else:
                        st.success("Execution completed successfully.")
                        st.code(output_text, language="text")
                else:
                    st.info("No execution results.")

        status_ph.success(f"✅ Completed `{os.path.basename(pdf_path)}` in `{container_name}`")

    except Exception as e:
        status_ph.error(f"❌ Failed `{os.path.basename(pdf_path)}`: {str(e)}")
    finally:
        # Return the container to the pool for the next paper
        queue.put_nowait(container_name)

async def run_batch(paths: list, placeholders: list):
    """Initializes the container pool and manages concurrent tasks."""
    queue = asyncio.Queue()
    for container in CONTAINER_POOL:
        queue.put_nowait(container)

    tasks = [worker(path, queue, ph[0], ph[1]) for path, ph in zip(paths, placeholders)]
    await asyncio.gather(*tasks)

def main():
    st.title("🔬 Concurrent AI Research Implementation Dashboard")
    st.markdown("Batch process up to 4 papers concurrently. Each executes in an isolated pod.")

    with st.sidebar:
        st.header("Configuration")
        st.info(f"**Workspace:** `{WORKSPACE_DIR}`\n\n**Pods Available:**\n" + "\n".join([f"- `{c}`" for c in CONTAINER_POOL]))

    default_paths = "./agent_workspace/papers/paper1.pdf\n./agent_workspace/papers/paper2.pdf\n./agent_workspace/papers/paper3.pdf\n./agent_workspace/papers/paper4.pdf"
    file_paths_input = st.text_area("File Paths (One per line)", value=default_paths, height=150)

    if st.button("🚀 Run Concurrent Analysis", type="primary"):
        paths = [p.strip() for p in file_paths_input.split("\n") if p.strip()]

        if not paths:
            st.warning("Please enter at least one file path.")
            return

        invalid = [p for p in paths if not os.path.exists(p)]
        if invalid:
            for p in invalid: st.error(f"File not found: {p}")
            st.stop()

        st.success(f"Starting concurrent analysis for {len(paths)} papers...")

        # Pre-allocate UI layout so asynchronous updates remain perfectly organized
        placeholders = []
        for path in paths:
            with st.expander(f"Paper: {os.path.basename(path)}", expanded=True):
                status_ph = st.empty()
                result_ph = st.container()
                placeholders.append((status_ph, result_ph))

        # Launch concurrent tasks
        asyncio.run(run_batch(paths, placeholders))

if __name__ == "__main__":
    main()
