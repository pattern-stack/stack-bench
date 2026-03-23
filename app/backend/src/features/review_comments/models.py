from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field


class ReviewComment(BasePattern):
    __tablename__ = "review_comments"

    class Pattern:
        entity = "review_comment"
        reference_prefix = "RC"
        track_changes = True

    pull_request_id = Field(UUID, foreign_key="pull_requests.id", required=True, index=True)
    branch_id = Field(UUID, foreign_key="branches.id", required=True, index=True)
    path = Field(str, required=True, max_length=500)
    line_key = Field(str, required=True, max_length=200)
    line_number = Field(int, nullable=True)
    side = Field(str, nullable=True, max_length=10)
    body = Field(str, required=True)
    author = Field(str, required=True, max_length=200)
    external_id = Field(int, nullable=True)
    resolved = Field(bool, default=False)
