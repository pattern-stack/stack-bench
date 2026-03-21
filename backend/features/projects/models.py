from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class Project(EventPattern):
    __tablename__ = "projects"

    class Pattern:
        entity = "project"
        reference_prefix = "PROJ"
        initial_state = "setup"
        states = {
            "setup": ["active"],
            "active": ["archived"],
            "archived": [],
        }
        state_phases = {
            "setup": StatePhase.INITIAL,
            "active": StatePhase.ACTIVE,
            "archived": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    name = Field(str, required=True, max_length=200, unique=True, index=True)
    description = Field(str, nullable=True)
    metadata_ = Field(dict, default=dict)
