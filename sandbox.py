# import asyncio
# from pathlib import Path
#
# # Use the current project directory to perfectly match your Podman mount
# WORKSPACE_DIR = Path("./agent_workspace").resolve()
#
# async def execute_in_sandbox(filename: str, code: str, container_name: str, timeout: int = 15) -> str:
#     """Writes code to the mounted volume and executes it asynchronously inside a specific Podman container."""
#     filepath = WORKSPACE_DIR / filename
#     filepath.parent.mkdir(parents=True, exist_ok=True)
#
#     # Write code to the mapped volume
#     filepath.write_text(code, encoding="utf-8")
#
#     try:
#         process = await asyncio.create_subprocess_exec(
#             "podman", "exec", container_name, "python", f"/workspace/{filename}",
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE
#         )
#
#         try:
#             stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
#         except asyncio.TimeoutError:
#             process.kill()
#             return f"ERROR: Execution timed out after {timeout} seconds."
#
#         if process.returncode == 0:
#             output = stdout.decode().strip()
#             return output if output else "Execution completed with no output."
#         else:
#             return f"ERROR:\n{stderr.decode().strip()}"
#
#     except Exception as e:
#         return f"ERROR: Failed to run sandbox command. {str(e)}"
#
# async def install_requirements(requirements_file: str, container_name: str, timeout: int = 180) -> str:
#     """Installs dependencies inside a specific Podman sandbox via pip."""
#     try:
#         process = await asyncio.create_subprocess_exec(
#             "podman", "exec", container_name, "pip", "install", "-r", f"/workspace/{requirements_file}",
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE
#         )
#
#         try:
#             stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
#         except asyncio.TimeoutError:
#             process.kill()
#             return f"ERROR: pip install timed out after {timeout} seconds."
#
#         if process.returncode == 0:
#             output = stdout.decode().strip()
#             return output if output else "Requirements installed successfully."
#         else:
#             return f"ERROR:\n{stderr.decode().strip()}"
#
#     except Exception as e:
#         return f"ERROR: Failed to run pip install. {str(e)}"
import asyncio
from pathlib import Path

WORKSPACE_DIR = Path("./agent_workspace").resolve()

async def execute_in_sandbox(filename: str, code: str, container_name: str, timeout: int = 180) -> str:
    """Executes python code inside the specific podman container with correct WORKDIR."""
    filepath = WORKSPACE_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(code, encoding="utf-8")

    # Extract directory relative to /workspace (e.g. /workspace/paper_stem)
    file_path_obj = Path(filename)
    container_workdir = f"/workspace/{file_path_obj.parent}"
    script_name = file_path_obj.name

    try:
        process = await asyncio.create_subprocess_exec(
            "podman", "exec",
            "-w", container_workdir,  # Set working directory to the paper's folder
            container_name,
            "python", script_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            return f"ERROR: Execution timed out after {timeout} seconds."

        if process.returncode == 0:
            output = stdout.decode().strip()
            return output if output else "Execution completed with no output."
        else:
            return f"ERROR:\n{stderr.decode().strip()}"

    except Exception as e:
        return f"ERROR: Failed to run sandbox command. {str(e)}"

async def install_requirements(requirements_file: str, container_name: str, timeout: int = 300) -> str:
    """Installs dependencies inside the specific Podman sandbox."""
    file_path_obj = Path(requirements_file)
    container_workdir = f"/workspace/{file_path_obj.parent}"

    try:
        process = await asyncio.create_subprocess_exec(
            "podman", "exec",
            "-w", container_workdir,
            container_name,
            "pip", "install", "--no-cache-dir", "-r", "requirements.txt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            return f"ERROR: pip install timed out after {timeout} seconds."

        if process.returncode == 0:
            return stdout.decode().strip() or "Requirements installed successfully."
        else:
            return f"ERROR:\n{stderr.decode().strip()}"

    except Exception as e:
        return f"ERROR: Failed to run pip install. {str(e)}"
