import threading
from enum import Enum
from typing import Any, Callable, Dict, Optional

from common.log import get_logger

logger = get_logger(__name__)


class IngestionPhase(str, Enum):
    INITIALIZATION = "initialization"
    DOWNLOADING = "downloading"
    TRANSCRIPTION = "transcription"
    EMBEDDING = "embedding"
    STORING = "storing"


class PhaseProgress:
    def __init__(self, current: int = 0, total: Optional[int] = None):
        """
        Initialize phase progress tracker

        Args:
            current: Current progress count (default: 0)
            total: Total items to process (default: None)
        """
        self.current = current
        self.total = total
        self._lock = threading.Lock()

    @property
    def percentage(self) -> Optional[float]:
        """
        Calculate progress percentage

        Returns:
            Optional[float]: Progress percentage (0-100) or None if total not set
        """
        with self._lock:
            if self.total is None or self.total == 0:
                return None
            return (self.current / self.total) * 100

    def set_progress(self, current: int) -> None:
        """
        Set current progress count

        Args:
            current: New current progress value
        """
        with self._lock:
            self.current = current

    def increment(self, amount: int = 1) -> None:
        """
        Increment progress by specified amount

        Args:
            amount: Amount to increment by (default: 1)
        """
        with self._lock:
            self.current += amount

    def set_total(self, total: int) -> None:
        """
        Set total items count

        Args:
            total: Total number of items to process
        """
        with self._lock:
            self.total = total


class IngestionState:
    data_source_id: str
    current_phase: Optional[IngestionPhase]
    phase_progress: Dict[IngestionPhase, PhaseProgress]
    success_callback: Optional[Callable[[], None]]
    failure_callback: Optional[Callable[[], None]]

    def __init__(
        self,
        data_source_id: str,
        success_callback: Optional[Callable[[], None]] = None,
        failure_callback: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize ingestion state for a data source

        Args:
            data_source_id: Unique identifier for the data source
            success_callback: Function to call on successful completion
            failure_callback: Function to call on failure
        """
        self.data_source_id = data_source_id
        self.current_phase = None
        self.phase_progress = {}
        self.success_callback = success_callback
        self.failure_callback = failure_callback
        self._lock = threading.Lock()

    def get_or_create_phase(self, phase: IngestionPhase, is_current_phase: bool = True) -> PhaseProgress:
        """
        Get existing phase progress or create new one

        Args:
            phase: Ingestion phase to get or create
            is_current_phase: Whether to set this as current phase (default: True)

        Returns:
            PhaseProgress: Progress tracker for the phase
        """
        with self._lock:
            if phase not in self.phase_progress:
                self.phase_progress[phase] = PhaseProgress()
            if is_current_phase:
                self.current_phase = phase
            return self.phase_progress[phase]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ingestion state to dictionary representation

        Returns:
            Dict[str, Any]: Dictionary with data source id and phase progresses
        """
        phase_progresses = []
        for phase, progress in self.phase_progress.items():
            phase_progresses.append(
                {
                    "phase": phase.value,
                    "is_current_phase": phase == self.current_phase,
                    "percentage": progress.percentage,
                }
            )

        return {"data_source_id": self.data_source_id, "phase_progresses": phase_progresses}


class SourceIngestionProgressManager:
    def __init__(self):
        """
        Initialize source ingestion progress manager
        """
        self._states: Dict[str, IngestionState] = {}

    def create_state(
        self,
        data_source_id: str,
        success_callback: Optional[Callable[[], None]] = None,
        failure_callback: Optional[Callable[[], None]] = None,
    ) -> IngestionState:
        """
        Create new ingestion state for a data source

        Args:
            data_source_id: Unique identifier for the data source
            success_callback: Function to call on successful completion
            failure_callback: Function to call on failure

        Returns:
            IngestionState: Newly created ingestion state
        """
        ingestion_state = IngestionState(data_source_id, success_callback, failure_callback)
        self._states[data_source_id] = ingestion_state
        return ingestion_state

    def add_phase(
        self, data_source_id: str, phase: IngestionPhase, is_current_phase: bool = True, total: Optional[int] = None
    ) -> IngestionState:
        """
        Add phase to data source ingestion tracking

        Args:
            data_source_id: Unique identifier for the data source
            phase: Ingestion phase to add
            is_current_phase: Whether to set as current phase (default: True)
            total: Total items for this phase (default: None)

        Returns:
            IngestionState: Updated ingestion state
        """
        if data_source_id not in self._states:
            logger.debug(f"Adding source to ingestion state manager: {data_source_id}")
            ingestion_state = IngestionState(data_source_id)
            self._states[data_source_id] = ingestion_state
        else:
            ingestion_state = self._states[data_source_id]
        ingestion_state.get_or_create_phase(phase, is_current_phase)
        if total is not None:
            logger.debug(f"Setting total for phase {phase}: {total} for source {data_source_id}")
            ingestion_state.get_or_create_phase(phase).set_total(total)
        return ingestion_state

    def get_state(self, data_source_id: str) -> Optional[IngestionState]:
        """
        Get ingestion state for a data source

        Args:
            data_source_id: Unique identifier for the data source

        Returns:
            Optional[IngestionState]: Ingestion state or None if not found
        """
        state = self._states.get(data_source_id)
        if state is None:
            logger.warning(f"Ingestion state for data source {data_source_id} not found")
            return None
        return state

    def set_phase_total(self, data_source_id: str, phase: IngestionPhase, total: int) -> None:
        """
        Set total items for a specific phase

        Args:
            data_source_id: Unique identifier for the data source
            phase: Phase to update
            total: Total number of items
        """
        state = self.get_state(data_source_id)
        if not state:
            return None
        logger.debug(f"Setting total for phase {phase}: {total} for source {data_source_id}")
        state.get_or_create_phase(phase).set_total(total)

    def increment_phase_progress(self, data_source_id: str, phase: IngestionPhase, amount: int = 1) -> None:
        """
        Increment progress for a specific phase

        Args:
            data_source_id: Unique identifier for the data source
            phase: Phase to increment progress for
            amount: Amount to increment by (default: 1)
        """
        state = self.get_state(data_source_id)
        if not state:
            return None
        logger.debug(f"Incrementing phase {phase} for source {data_source_id} by {amount}")
        state.get_or_create_phase(phase).increment(amount)

    def set_phase_progress(self, data_source_id: str, phase: IngestionPhase, current: int) -> None:
        """
        Set progress value for a specific phase

        Args:
            data_source_id: Unique identifier for the data source
            phase: Phase to update progress for
            current: Current progress value
        """
        state = self.get_state(data_source_id)
        if not state:
            return None
        logger.debug(f"Setting progress for phase {phase}: {current} for source {data_source_id}")
        state.get_or_create_phase(phase).set_progress(current)

    def get_phase_percentage(self, data_source_id: str, phase: Optional[IngestionPhase] = None) -> Optional[float]:
        """
        Get percentage progress for a phase

        Args:
            data_source_id: Unique identifier for the data source
            phase: Specific phase or None for current phase

        Returns:
            Optional[float]: Progress percentage or None if not available
        """
        state = self.get_state(data_source_id)
        if not state:
            return None
        target_phase = phase or state.current_phase
        if not target_phase:
            return None
        return state.phase_progress[target_phase].percentage

    def remove_source_state(self, data_source_id: str) -> None:
        """
        Remove ingestion state for a data source

        Args:
            data_source_id: Unique identifier for the data source
        """
        if self._states.pop(data_source_id, None) is None:
            logger.warning(f"Ingestion state for data source {data_source_id} not found")

    def mark_as_completed(self, data_source_id: str) -> None:
        """
        Mark data source ingestion as completed and trigger callback

        Args:
            data_source_id: Unique identifier for the data source
        """
        state = self.get_state(data_source_id)
        if not state:
            return None

        if state.success_callback:
            state.success_callback()
        self.remove_source_state(data_source_id)

    def mark_as_failed(self, data_source_id: str) -> None:
        """
        Mark data source ingestion as failed and trigger callback

        Args:
            data_source_id: Unique identifier for the data source
        """
        state = self.get_state(data_source_id)
        if not state:
            return None

        if state.failure_callback:
            state.failure_callback()
        self.remove_source_state(data_source_id)
