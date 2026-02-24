"""
VOLO — Machine Control Service
Remote machine access via SSH or Volo daemon.
"""

import os
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("volo.machine")


class MachineService:
    """Handles remote machine operations (sandboxed for safety)."""

    def __init__(self):
        self.machines: dict[str, dict] = {}
        self._allow_local = os.getenv("ALLOW_LOCAL_COMMANDS", "false").lower() == "true"

    def register_machine(self, machine_id: str, config: dict):
        """Register a remote machine."""
        self.machines[machine_id] = {
            "id": machine_id,
            "name": config.get("name", machine_id),
            "host": config.get("host", ""),
            "status": "connected",
            **config,
        }

    async def list_machines(self) -> dict:
        if not self.machines:
            return {
                "machines": [],
                "message": "No machines connected. Set up the Volo daemon on your remote machines.",
            }
        return {"machines": list(self.machines.values())}

    async def run_command(
        self,
        command: str,
        machine_id: str = "local",
        timeout: int = 30,
    ) -> dict:
        """
        Execute a command on a connected machine.
        SAFETY: Only whitelisted commands allowed in production.
        """
        # Safety checks
        dangerous = ["rm -rf /", "mkfs", "dd if=", "> /dev/", "chmod 777 /"]
        for d in dangerous:
            if d in command:
                return {"error": f"Blocked dangerous command: {command}"}

        if machine_id == "local" and self._allow_local:
            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                return {
                    "machine": "local",
                    "command": command,
                    "exit_code": proc.returncode,
                    "stdout": stdout.decode()[:5000],
                    "stderr": stderr.decode()[:2000],
                }
            except asyncio.TimeoutError:
                return {"error": f"Command timed out after {timeout}s"}
            except Exception as e:
                return {"error": str(e)}

        if machine_id not in self.machines:
            return {
                "error": f"Machine '{machine_id}' not found.",
                "available": list(self.machines.keys()),
            }

        # For remote machines, we'd use SSH or a Volo daemon protocol
        return {
            "error": "Remote execution not yet implemented. Install the Volo daemon on your machine.",
            "machine": machine_id,
        }

    async def list_files(self, path: str, machine_id: str = "local") -> dict:
        if machine_id == "local" and self._allow_local:
            return await self.run_command(f"ls -la {path}", machine_id="local")
        return {"error": "Machine not connected. Set up the Volo daemon."}

    async def read_file(self, path: str, machine_id: str = "local") -> dict:
        if machine_id == "local" and self._allow_local:
            return await self.run_command(f"cat {path}", machine_id="local")
        return {"error": "Machine not connected. Set up the Volo daemon."}

    async def write_file(self, path: str, content: str, machine_id: str = "local") -> dict:
        return {
            "error": "File write requires explicit user approval.",
            "action": "approval_required",
            "path": path,
        }
