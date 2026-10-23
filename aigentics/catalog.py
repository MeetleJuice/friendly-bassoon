"""One metadata GET per unique configured connection. No inference or hidden retries."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import platform
import threading
import time
from uuid import uuid4
from urllib.parse import urlsplit

from . import __version__
from .providers import Provider, ProviderError
from .store import Store, now


def catalog_age(fetched):
    return max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(fetched)).total_seconds()))


def provider_label(profile):
    if profile.kind == "ollama":
        return "ollama"
    return {
        "api.groq.com": "groq",
        "openrouter.ai": "openrouter",
        "integrate.api.nvidia.com": "nvidia",
        "generativelanguage.googleapis.com": "gemini",
        "api.openai.com": "openai",
    }.get(urlsplit(profile.base_url).hostname, "custom_openai")


class CatalogRunner:
    def __init__(self, store, credentials, provider_factory=Provider):
        self.store, self.credentials, self.provider_factory = store, credentials, provider_factory

    def run(self, cancel=None, emit=lambda event: None):
        cancel = cancel or threading.Event()
        profiles = self.store.profiles()
        if len(profiles) > 32:
            raise ValueError("Test at most 32 configured provider profiles at once")
        started = time.monotonic()
        report = {
            "schema_version": 1,
            "suite_version": "api-models-1",
            "kind": "api_models",
            "id": str(uuid4()),
            "created": now(),
            "app_version": __version__,
            "state": "running",
            "environment": {
                "os": platform.system(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
            },
            "checks": [],
            "recent_runs": {},
            "privacy": "Model-list metadata only. No prompts, generation, credentials or endpoint URLs.",
        }
        self.store.save_diagnostic(report)
        # Duplicate profiles sharing endpoint, adapter and credential reference use one request.
        groups = {}
        for profile in profiles:
            groups.setdefault(Store.catalog_signature(profile), []).append(profile)

        def probe(group):
            profile = group[0]
            began = time.monotonic()
            models, partial, status_code = None, False, None
            status, code = "passed", "MODEL_LIST_OK"
            message = "Model list fetched. Generation and tool support were not tested."
            request_count = 0
            provider = None
            try:
                if cancel.is_set():
                    raise InterruptedError
                if profile.credential_ref:
                    try:
                        self.credentials.get(profile.credential_ref)
                    except Exception:
                        status, code = "skipped", "CREDENTIAL_UNAVAILABLE"
                        message = (
                            "Credential unavailable. Load your key file or save the key in the OS vault."
                        )
                if status != "skipped":
                    provider = self.provider_factory(
                        profile.model_copy(update={"timeout_seconds": 8}), self.credentials
                    )
                    if cancel.is_set():
                        raise InterruptedError
                    request_count = 1
                    models = provider.discover()
                    status_code = getattr(provider, "last_http_status", None)
                    partial = bool(getattr(provider, "discovery_partial", False))
                    if partial:
                        status, code = "warning", "MODEL_LIST_PARTIAL"
                        message = "First page fetched. More models exist; no extra request was made."
                    elif not models:
                        status, code = "warning", "MODEL_LIST_EMPTY"
                        message = "Connection responded with an empty model list."
            except InterruptedError:
                status, code, message = "skipped", "CANCELLED", "Cancelled before requesting the model list."
            except ProviderError as exc:
                status = "failed"
                status_code = (
                    exc.http_status
                    if exc.http_status is not None
                    else getattr(provider, "last_http_status", None)
                )
                code = {
                    401: "AUTHENTICATION_FAILED",
                    403: "ACCESS_DENIED",
                    404: "MODELS_ENDPOINT_UNAVAILABLE",
                    429: "RATE_LIMITED",
                }.get(status_code, exc.code)
                message = "Model list could not be fetched. Previous successful catalog is retained."
            except Exception:
                status, code = "failed", "CATALOG_CHECK_FAILED"
                message = "Model-list check failed. No provider response body was retained."
            return (
                group,
                models,
                partial,
                {
                    "id": "api_" + str(profiles.index(profile) + 1),
                    "status": status,
                    "code": code,
                    "message": message,
                    "duration_ms": round((time.monotonic() - began) * 1000),
                    "evidence": {
                        "provider": provider_label(profile),
                        "profile_ids": [p.id for p in group],
                        "model_count": len(models or []),
                        "http_status": status_code,
                        "request_count": request_count,
                        "generation_requests": 0,
                        "partial_catalog": partial,
                    },
                },
            )

        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="catalog") as pool:
            pending = [pool.submit(probe, group) for group in groups.values()]
            for future in as_completed(pending):
                group, models, partial, check = future.result()
                if models is not None and not cancel.is_set():
                    for profile in group:
                        self.store.save_catalog(profile, models, partial)
                report["checks"].append(check)
                self.store.save_diagnostic(report)
                emit({"kind": "diagnostic.result", "data": check})
        report["checks"].sort(key=lambda check: int(check["id"].split("_")[-1]))
        report["summary"] = {
            status: sum(c["status"] == status for c in report["checks"])
            for status in ("passed", "failed", "warning", "skipped")
        }
        report["state"] = (
            "cancelled"
            if cancel.is_set()
            else "needs_attention"
            if report["summary"]["failed"] or report["summary"]["warning"] or report["summary"]["skipped"]
            else "passed"
            if report["checks"]
            else "no_profiles"
        )
        report["duration_ms"] = round((time.monotonic() - started) * 1000)
        report["finished"] = now()
        self.store.save_diagnostic(report)
        self.store.event(
            None,
            "catalog.completed",
            {
                "report_id": report["id"],
                "state": report["state"],
                "summary": report["summary"],
                "generation_requests": 0,
            },
        )
        self.store.prune()
        return report
