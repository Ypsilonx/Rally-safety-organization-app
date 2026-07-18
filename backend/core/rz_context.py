"""Persistent RZ context shared by backend API, frontend UI and logging."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


class RzContext(BaseModel):
    """Persistent race context used across app modules.

    Attributes:
        rz_name: Human-readable race stage name displayed in UI and logs.
        communication_reset_version: Monotonic version incremented on every global chat reset.
        communication_reset_at: Timestamp of last communication reset.
        updated_at: Timestamp of the latest context update.
    """

    rz_name: str = Field(default="Nezadaná RZ", min_length=1, max_length=120)
    communication_reset_version: int = Field(default=0, ge=0)
    communication_reset_at: str | None = None
    updated_at: str | None = None


class RzContextManager:
    """Load, persist and mutate RZ context in local JSON storage."""

    def __init__(self, storage_file: str = "data/rz_context.json") -> None:
        """Initialize manager and load current context.

        Args:
            storage_file: JSON file path for context persistence.
        """
        self.storage_path = Path(storage_file)
        self.storage_path.parent.mkdir(exist_ok=True)
        self._context = self._load()

    def _load(self) -> RzContext:
        """Load context from storage.

        Returns:
            Loaded context or default one when storage is missing/corrupted.
        """
        if not self.storage_path.exists():
            context = RzContext(updated_at=datetime.now(UTC).isoformat())
            self._save(context)
            return context

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            context = RzContext.model_validate(payload)
            if not context.updated_at:
                context.updated_at = datetime.now(UTC).isoformat()
                self._save(context)
            return context
        except Exception:
            context = RzContext(updated_at=datetime.now(UTC).isoformat())
            self._save(context)
            return context

    def _save(self, context: RzContext) -> None:
        """Persist context JSON payload.

        Args:
            context: Context object to write.
        """
        self.storage_path.write_text(
            json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_context(self) -> RzContext:
        """Return current in-memory context snapshot.

        Returns:
            Current context object.
        """
        return self._context

    def set_rz_name(self, rz_name: str) -> RzContext:
        """Update RZ display name.

        Args:
            rz_name: New human-readable RZ name.

        Returns:
            Updated context.

        Raises:
            ValueError: If the provided name is empty after trimming.
        """
        normalized = " ".join(str(rz_name or "").split())
        if not normalized:
            raise ValueError("Název RZ nesmí být prázdný")

        self._context.rz_name = normalized
        self._context.updated_at = datetime.now(UTC).isoformat()
        self._save(self._context)
        return self._context

    def reset_communication_history(self) -> RzContext:
        """Increment reset version and mark global communication reset timestamp.

        Returns:
            Updated context after reset marker update.
        """
        now = datetime.now(UTC).isoformat()
        self._context.communication_reset_version += 1
        self._context.communication_reset_at = now
        self._context.updated_at = now
        self._save(self._context)
        return self._context

    def slug_for_filename(self, rz_name: str) -> str:
        """Create filesystem-safe slug from RZ name.

        Args:
            rz_name: Human-readable RZ name.

        Returns:
            Lowercase ASCII slug suitable for log filenames.
        """
        normalized = unicodedata.normalize("NFKD", str(rz_name or ""))
        ascii_only = "".join(char for char in normalized if not unicodedata.combining(char))
        lowered = ascii_only.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
        return slug or "nezadana-rz"


rz_context_manager = RzContextManager()
