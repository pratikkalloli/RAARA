# RAARA WSL Access Diagnostic Report

**Date:** 2026-11-15  
**Investigation type:** Read-only Windows PowerShell diagnostics  
**Result:** WSL launch failure remains undiagnosed at the distribution/service level because this session cannot query those protected resources.

## Summary

All three WSL CLI probes (`--status`, `--list --verbose`, and the minimal shell launch) failed immediately with the same sanitized output:

```text
Access is denied.
Error code: Wsl/E_ACCESSDENIED
```

No WSL shell or Python process started. The current Windows identity was `LAPTOP-IB0VNU55\Pratik Kalloli` (SID `S-1-5-21-2464117186-3492043139-4291117835-1001`). Its `HKCU\Software\Microsoft\Windows\CurrentVersion\Lxss` key exists but contains no registered distribution entries. This confirms only that no distro registration is visible in the current user's key from this session; it does **not** prove Ubuntu is unregistered elsewhere or damaged.

The WSL service registry key exists, but service status could not be queried: Service Control Manager returned access denied. `LxssManager` is not installed in this environment (error 1060). Recent System/Application event queries and `Get-AppxPackage` were also denied. Consequently, the actual service state, Ubuntu package visibility, and event-based cause remain unknown.

## Commands executed and results

| Command/check | Result |
|---|---|
| `wsl.exe --status` | Exit 1; `Access is denied. Error code: Wsl/E_ACCESSDENIED` |
| `wsl.exe --list --verbose` | Exit 1; same access-denied error |
| `wsl.exe -e bash -lc "echo WSL_LAUNCH_OK"` | Exit 1; same access-denied error; shell did not start |
| `Get-Service -Name WslService` and `Get-Service -Name LxssManager` | Could not establish status from this session; queries returned no visible service objects. Follow-up `sc.exe` distinguishes access denied for WslService and service-not-found for LxssManager. |
| `sc.exe query WslService; sc.exe qc WslService` | `OpenService FAILED 5: Access is denied.` |
| `sc.exe query LxssManager; sc.exe qc LxssManager` | `OpenService FAILED 1060: The specified service does not exist as an installed service.` |
| Read `HKLM\SYSTEM\CurrentControlSet\Services\WslService` | Read succeeded. Service key exists; `Start=2` (automatic). This registry value does not establish current running state. |
| Read `HKLM\SYSTEM\CurrentControlSet\Services\LxssManager` | Key absent. |
| Read current user's `HKCU\Software\Microsoft\Windows\CurrentVersion\Lxss` | Key exists; no distribution entries. |
| `Get-AppxPackage` filtered for Ubuntu/WSL/Canonical | `Get-AppxPackage: Access is denied.` |
| Recent System/Application error event query (last 7 days, WSL-related providers) | Both log queries returned `Attempted to perform an unauthorized operation.` No event contents were obtained. |
| `Get-Command wsl.exe` / file version | `C:\Windows\system32\wsl.exe`, version `10.0.26100.8737 (WinBuild.160101.0800)` |

No credentials were read or displayed.

## Confirmed findings

- The WSL command-line utility is present at `C:\Windows\system32\wsl.exe`.
- WSL CLI invocations fail before producing status, distro list, or shell output.
- The current user's WSL registration key contains no distro records.
- `WslService` has a machine service registry key configured with automatic start (`Start=2`), but its running state is inaccessible.
- `LxssManager` is not registered as an installed service on this machine; the newer `WslService` entry is present.
- The current session cannot read service state through SCM, query AppX packages, or query relevant event logs.

## Most likely cause (inference)

The evidence points to a Windows execution-context or access-control restriction affecting WSL service/distro enumeration, rather than demonstrating a broken RAARA environment. The same `E_ACCESSDENIED` occurs even for `wsl --status`, while this session also receives access-denied responses from SCM, AppX, and event log queries. However, the evidence is insufficient to distinguish a Codex/sandbox token restriction from a Windows account/service ACL problem. The distro's existence, registration under another account, and service running state are **not confirmed**.

## Safest recommended recovery

1. In a normal, non-elevated PowerShell window opened as the same Windows account, run:

   ```powershell
   whoami
   wsl.exe --status
   wsl.exe --list --verbose
   wsl.exe -e bash -lc "echo WSL_LAUNCH_OK"
   ```

2. If the same access-denied error occurs there, ask the Windows administrator to inspect the WSL service state/permissions, the distribution registration for the current SID, and the WSL-related System event logs. Do not unregister, reset, reinstall, or recreate the distribution as a diagnostic step.

No administrator action or system configuration change was attempted here.

## Modification confirmation

No RAARA source code, production database, ChromaDB collection, uploads, or Phase 9A assets were modified. No WSL distribution, virtual environment, cache, service, or Windows system setting was changed. No live Gemini request or acceptance scenario was run.
