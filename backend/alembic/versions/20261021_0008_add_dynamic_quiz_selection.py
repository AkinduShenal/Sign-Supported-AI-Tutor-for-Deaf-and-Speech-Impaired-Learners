"""Add versioned Quiz items and persistent per-session question selection.

The existing Quiz content/session tables predate this Alembic chain. This
migration requires those tables to exist and never creates or reseeds them.
Apply only after checking the target database schema and taking a backup.
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021_0008"
down_revision = "20261011_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quiz_questions", sa.Column("bank_version", sa.String(80), nullable=True))
    op.add_column("quiz_questions", sa.Column("logical_slot", sa.String(10), nullable=True))
    op.create_index("ix_quiz_questions_bank_slot", "quiz_questions", ["bank_version", "logical_slot"])
    op.add_column("quiz_sessions", sa.Column("bank_version", sa.String(80), nullable=True))
    op.create_table(
        "quiz_session_questions",
        sa.Column("quiz_session_id", sa.String(100), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("quiz_session_id", "question_order", name="quiz_session_questions_pkey"),
        sa.UniqueConstraint("quiz_session_id", "question_id", name="quiz_session_questions_session_question_key"),
        sa.CheckConstraint("question_order BETWEEN 1 AND 10", name="quiz_session_questions_order_check"),
        sa.ForeignKeyConstraint(["quiz_session_id"], ["quiz_sessions.quiz_session_id"], ondelete="CASCADE", name="quiz_session_questions_session_fkey"),
        sa.ForeignKeyConstraint(["question_id"], ["quiz_questions.id"], ondelete="RESTRICT", name="quiz_session_questions_question_fkey"),
    )


def downgrade() -> None:
    # Only use on an isolated database: this removes saved dynamic selections.
    op.drop_table("quiz_session_questions")
    op.drop_column("quiz_sessions", "bank_version")
    op.drop_index("ix_quiz_questions_bank_slot", table_name="quiz_questions")
    op.drop_column("quiz_questions", "logical_slot")
    op.drop_column("quiz_questions", "bank_version")
