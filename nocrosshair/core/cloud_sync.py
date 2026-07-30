#!/usr/bin/env python3

import json
import os
import hashlib
import subprocess
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from nocrosshair.core.config import PROFILES_DIR


@dataclass
class CloudProfile:
    name: str
    data: Dict[str, Any]
    hash: str
    last_modified: float
    device_id: str = "local"
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data": self.data,
            "hash": self.hash,
            "last_modified": self.last_modified,
            "device_id": self.device_id,
            "version": self.version,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CloudProfile":
        return CloudProfile(
            name=d.get("name", ""),
            data=d.get("data", {}),
            hash=d.get("hash", ""),
            last_modified=d.get("last_modified", 0),
            device_id=d.get("device_id", "local"),
            version=d.get("version", 1),
        )


class SyncBackend:
    """Base class for sync backends."""

    def push(self, local_path: str) -> bool:
        raise NotImplementedError

    def pull(self, local_path: str) -> bool:
        raise NotImplementedError

    def is_available(self) -> bool:
        return False


class GitSyncBackend(SyncBackend):
    """Sync via git add/commit/push/pull."""

    def __init__(self, repo_path: str, remote: str = "origin", branch: str = "main"):
        self._repo_path = repo_path
        self._remote = remote
        self._branch = branch
        self._last_error = ""

    def _run_git(self, *args: str) -> tuple:
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0, result.stdout.strip() + result.stderr.strip()
        except FileNotFoundError:
            self._last_error = "git not found"
            return False, "git not found"
        except subprocess.TimeoutExpired:
            self._last_error = "git timed out"
            return False, "timeout"
        except Exception as e:
            self._last_error = str(e)
            return False, str(e)

    def is_available(self) -> bool:
        ok, _ = self._run_git("rev-parse", "--git-dir")
        return ok

    def init_repo(self) -> bool:
        if os.path.exists(os.path.join(self._repo_path, ".git")):
            return True
        ok, msg = self._run_git("init")
        if ok:
            ok, msg = self._run_git("branch", "-M", self._branch)
        return ok

    def push(self, local_path: str = "") -> bool:
        target = local_path or self._repo_path
        ok, msg = self._run_git("-C", target, "add", "-A")
        if not ok:
            self._last_error = f"git add failed: {msg}"
            return False

        ok, msg = self._run_git("-C", target, "commit", "-m", f"sync {time.strftime('%Y-%m-%d %H:%M:%S')}")
        if not ok and "nothing to commit" not in msg:
            self._last_error = f"git commit failed: {msg}"
            return False

        ok, msg = self._run_git("-C", target, "push", self._remote, self._branch)
        if not ok:
            self._last_error = f"git push failed: {msg}"
            return False

        return True

    def pull(self, local_path: str = "") -> bool:
        target = local_path or self._repo_path
        ok, msg = self._run_git("-C", target, "pull", self._remote, self._branch)
        if not ok:
            self._last_error = f"git pull failed: {msg}"
            return False
        return True

    def get_last_error(self) -> str:
        return self._last_error


class RcloneSyncBackend(SyncBackend):
    """Sync via rclone sync local→remote."""

    def __init__(self, remote_name: str = "nocrosshair", remote_path: str = "profiles"):
        self._remote_name = remote_name
        self._remote_path = remote_path
        self._last_error = ""

    def _run_rclone(self, *args: str) -> tuple:
        try:
            result = subprocess.run(
                ["rclone"] + list(args),
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0, result.stdout.strip() + result.stderr.strip()
        except FileNotFoundError:
            self._last_error = "rclone not found"
            return False, "rclone not found"
        except subprocess.TimeoutExpired:
            self._last_error = "rclone timed out"
            return False, "timeout"
        except Exception as e:
            self._last_error = str(e)
            return False, str(e)

    def is_available(self) -> bool:
        ok, _ = self._run_rclone("version")
        return ok

    def push(self, local_path: str) -> bool:
        remote_spec = f"{self._remote_name}:{self._remote_path}"
        ok, msg = self._run_rclone("sync", local_path, remote_spec, "--progress")
        if not ok:
            self._last_error = f"rclone sync failed: {msg}"
            return False
        return True

    def pull(self, local_path: str) -> bool:
        remote_spec = f"{self._remote_name}:{self._remote_path}"
        ok, msg = self._run_rclone("sync", remote_spec, local_path, "--progress")
        if not ok:
            self._last_error = f"rclone sync failed: {msg}"
            return False
        return True

    def configure_remote(self, remote_type: str = "s3", **kwargs) -> bool:
        args = ["config", "create", self._remote_name, remote_type]
        for k, v in kwargs.items():
            args.extend([k, str(v)])
        ok, msg = self._run_rclone(*args)
        if not ok:
            self._last_error = f"rclone config failed: {msg}"
        return ok

    def get_last_error(self) -> str:
        return self._last_error


class CloudSyncClient:

    def __init__(self):
        self._authenticated = False
        self._device_id = self._generate_device_id()
        self._sync_history: List[Dict[str, Any]] = []
        self._conflict_resolution = "latest"
        self._backends: Dict[str, SyncBackend] = {}
        self._active_backend: Optional[str] = None

    def _generate_device_id(self) -> str:
        import platform
        import uuid
        system_info = f"{platform.node()}-{platform.system()}-{uuid.getnode()}"
        return hashlib.md5(system_info.encode()).hexdigest()[:16]

    def register_backend(self, name: str, backend: SyncBackend) -> None:
        self._backends[name] = backend

    def set_active_backend(self, name: str) -> bool:
        if name in self._backends:
            self._active_backend = name
            return True
        return False

    def get_active_backend(self) -> Optional[SyncBackend]:
        if self._active_backend:
            return self._backends.get(self._active_backend)
        return None

    def get_backends(self) -> Dict[str, bool]:
        return {name: b.is_available() for name, b in self._backends.items()}

    def authenticate(self, token: Optional[str] = None) -> bool:
        if token:
            self._authenticated = True
            return True

        self._authenticated = False
        return False

    def logout(self) -> None:
        self._authenticated = False

    def is_authenticated(self) -> bool:
        return self._authenticated

    def calculate_hash(self, data: Dict[str, Any]) -> str:
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def upload_profile(self, name: str, data: Dict[str, Any]) -> bool:
        if not self._authenticated:
            return False

        profile = CloudProfile(
            name=name,
            data=data,
            hash=self.calculate_hash(data),
            last_modified=time.time(),
            device_id=self._device_id,
        )

        self._sync_history.append({
            "action": "upload",
            "name": name,
            "timestamp": time.time(),
            "success": True,
        })

        return True

    def download_profile(self, name: str) -> Optional[Dict[str, Any]]:
        if not self._authenticated:
            return None

        self._sync_history.append({
            "action": "download",
            "name": name,
            "timestamp": time.time(),
            "success": True,
        })

        return None

    def sync_profiles(self, local_profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        if not self._authenticated:
            return {"synced": 0, "conflicts": 0}

        synced = 0
        conflicts = 0

        for name, data in local_profiles.items():
            local_hash = self.calculate_hash(data)

            cloud_data = self.download_profile(name)
            if cloud_data:
                cloud_hash = self.calculate_hash(cloud_data)
                if local_hash != cloud_hash:
                    if self._conflict_resolution == "latest":
                        self.upload_profile(name, data)
                        synced += 1
                    else:
                        conflicts += 1
            else:
                self.upload_profile(name, data)
                synced += 1

        return {"synced": synced, "conflicts": conflicts}

    def sync_with_backend(self, local_path: str, direction: str = "push") -> bool:
        backend = self.get_active_backend()
        if not backend:
            return False

        if direction == "push":
            return backend.push(local_path)
        elif direction == "pull":
            return backend.pull(local_path)
        return False

    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._sync_history[-limit:]

    def set_conflict_resolution(self, strategy: str) -> None:
        if strategy in ["latest", "manual"]:
            self._conflict_resolution = strategy

    def get_conflict_resolution(self) -> str:
        return self._conflict_resolution

    def get_device_id(self) -> str:
        return self._device_id

    def get_devices(self) -> List[Dict[str, Any]]:
        return [{"id": self._device_id, "name": "Local Device"}]


class CloudSyncManager:

    def __init__(self):
        self._client = CloudSyncClient()
        self._auto_sync = False
        self._sync_interval = 300
        self._profiles_dir = os.path.join(PROFILES_DIR, "profiles")

    def get_client(self) -> CloudSyncClient:
        return self._client

    def enable_auto_sync(self, enabled: bool) -> None:
        self._auto_sync = enabled

    def is_auto_sync_enabled(self) -> bool:
        return self._auto_sync

    def set_sync_interval(self, seconds: int) -> None:
        self._sync_interval = seconds

    def get_sync_interval(self) -> int:
        return self._sync_interval

    def setup_git_backend(self, repo_path: str, remote: str = "origin", branch: str = "main") -> GitSyncBackend:
        backend = GitSyncBackend(repo_path, remote, branch)
        self._client.register_backend("git", backend)
        return backend

    def setup_rclone_backend(self, remote_name: str = "nocrosshair", remote_path: str = "profiles") -> RcloneSyncBackend:
        backend = RcloneSyncBackend(remote_name, remote_path)
        self._client.register_backend("rclone", backend)
        return backend

    def sync_profiles(self, local_profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        return self._client.sync_profiles(local_profiles)

    def sync_with_backend(self, local_path: str = "", direction: str = "push") -> bool:
        path = local_path or self._profiles_dir
        return self._client.sync_with_backend(path, direction)

    def get_sync_status(self) -> Dict[str, Any]:
        return {
            "authenticated": self._client.is_authenticated(),
            "auto_sync": self._auto_sync,
            "device_id": self._client.get_device_id(),
            "conflict_resolution": self._client.get_conflict_resolution(),
            "backends": self._client.get_backends(),
            "active_backend": self._client._active_backend,
        }


cloud_sync_manager = CloudSyncManager()
