class GraphException(Exception):
    """Base exception for Knowledge Graph errors."""
    pass


class ConceptNotFoundError(GraphException):
    """Raised when a concept ID does not exist in the graph."""
    def __init__(self, concept_id: str):
        self.concept_id = concept_id
        super().__init__(f"Concept with ID '{concept_id}' was not found in the graph.")


class DuplicateConceptError(GraphException):
    """Raised when attempting to add a concept ID that already exists."""
    def __init__(self, concept_id: str):
        self.concept_id = concept_id
        super().__init__(f"Concept with ID '{concept_id}' already exists in the graph.")


class InvalidDependencyError(GraphException):
    """Raised when creating a dependency edge between invalid concepts."""
    pass


class SelfLoopError(InvalidDependencyError):
    """Raised when creating a dependency from a concept to itself."""
    def __init__(self, concept_id: str):
        self.concept_id = concept_id
        super().__init__(f"Self-loop detected: Concept '{concept_id}' cannot be a prerequisite of itself.")


class CycleDetectedError(GraphException):
    """Raised when a graph operation requires an acyclic graph (DAG), but a cycle was detected."""
    def __init__(self, cycle_path: list):
        self.cycle_path = cycle_path
        path_str = " -> ".join(cycle_path)
        super().__init__(f"Circular dependency cycle detected in graph: {path_str}")
