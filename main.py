import os
import json
import re
import asyncio
from pathlib import Path
from agents import WorkflowOrchestrator
from sandbox import execute_in_sandbox

async def main():
    # Setup directories - using local directory to match Podman mount
    WORKSPACE_DIR = Path("./agent_workspace").resolve()
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Multi-Agent Scientific Implementation System ===")

    # Get PDF path
    pdf_path = input("Enter path to scientific paper (PDF): ").strip()
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found.")
        return

    # Initialize Orchestrator
    orchestrator = WorkflowOrchestrator()

    try:
        # Run the async workflow
        final_state = await orchestrator.run(pdf_path)

        print("\n[System] Saving generated code...")

        code_string = final_state.get("code", "")
        matches = re.findall(r'<file path="(.*?)">\s*(.*?)\s*</file>', code_string, re.DOTALL)

        for filepath, code in matches:
            full_path = WORKSPACE_DIR / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(code, encoding="utf-8")
            print(f"  -> Saved: {filepath}")

        # Execute in Sandbox
        if matches:
            target_file = matches[0][0] # Execute the first file
            target_code = matches[0][1]

            print(f"\n[System] Executing {target_file} in Podman Sandbox...")
            exec_result = await execute_in_sandbox(target_file, target_code)
            print(f"Output:\n{exec_result}")

            # Save execution results natively
            result_file = WORKSPACE_DIR / "execution_results.json"
            result_file.write_text(json.dumps({"result": exec_result}, indent=2), encoding="utf-8")
        else:
            print("[System] No code generated. Agent response:")
            print(code_string)

    except Exception as e:
        print(f"[System] Workflow failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Start the async event loop
    asyncio.run(main())
