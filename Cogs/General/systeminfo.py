import os
import platform
import time
from pathlib import Path

import cpuinfo
import psutil


class SystemInfo:

    @staticmethod
    def is_docker() -> bool:
        return (
            Path("/.dockerenv").exists()
            or Path("/run/.containerenv").exists()
            or Path("/proc/1/cgroup").exists()
            and "docker" in Path("/proc/1/cgroup").read_text(errors="ignore")
        )

    @staticmethod
    def is_pterodactyl() -> bool:
        # Pterodactyl/Wings normally runs servers inside Docker.
        # P_SERVER_UUID is a useful indicator.
        return bool(os.getenv("P_SERVER_UUID"))

    @classmethod
    def environment(cls) -> str:
        if cls.is_pterodactyl():
            return "Pterodactyl"

        return "Docker" if cls.is_docker() else "Bare Metal / VM"

    @staticmethod
    def cpu_name():
        cpu: dict = cpuinfo.get_cpu_info()
        return cpu.get("brand_raw", "Unknown CPU")

    @classmethod
    def cpu(cls):

        usage = psutil.cpu_percent(interval=0.5)

        logical = psutil.cpu_count(logical=True)
        physical = psutil.cpu_count(logical=False)

        return {
            "name": cls.cpu_name(),
            "usage": usage,
            "physical": physical,
            "logical": logical,
        }

    @classmethod
    def memory(cls):
        memory = psutil.virtual_memory()

        usage = memory.used
        if limit := cls.container_memory_limit():
            percentage = usage / limit * 100
            total = limit
        else:
            percentage = memory.percent
            total = memory.total

        return {
            "used": usage,
            "total": total,
            "available": memory.available,
            "percent": percentage,
        }

    @staticmethod
    def disk():

        path = os.path.abspath(os.sep)

        disk = psutil.disk_usage(path)

        return {
            "used": disk.used,
            "total": disk.total,
            "free": disk.free,
            "percent": disk.percent,
        }

    @staticmethod
    def platform():

        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }

    @staticmethod
    def uptime():

        return time.time() - psutil.boot_time()

    @staticmethod
    def container_memory_limit():

        path = Path("/sys/fs/cgroup/memory.max")

        if not path.exists():
            return None

        value = path.read_text().strip()

        if value == "max":
            return None

        try:
            return int(value)
        except ValueError:
            return None
