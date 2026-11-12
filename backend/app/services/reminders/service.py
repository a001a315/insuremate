import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.base import utcnow
from app.models import Claim, Notification, Policy, Reminder, User
from app.repositories.entities import ClaimRepository, PolicyRepository, ReminderRepository
from app.schemas.reminder import ReminderCreate, ReminderUpdate
from app.services.errors import NotFound

RENEWAL_WINDOW_DAYS = 30
FOLLOWUP_AFTER_DAYS = 14


class ReminderService:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db, self.user_id = db, user_id
        self.repo = ReminderRepository(db, user_id)

    def get(self, rid: uuid.UUID) -> Reminder:
        r = self.repo.get(rid)
        if not r:
            raise NotFound("Reminder not found")
        return r

    def list(self, include_completed: bool = True) -> list[Reminder]:
        q = self.repo.query().order_by(Reminder.is_completed, Reminder.due_date)
        if not include_completed:
            q = q.where(Reminder.is_completed.is_(False))
        return list(self.db.scalars(q))

    def create(self, data: ReminderCreate) -> Reminder:
        if data.policy_id and not PolicyRepository(self.db, self.user_id).get(data.policy_id):
            raise NotFound("Policy not found")
        if data.claim_id and not ClaimRepository(self.db, self.user_id).get(data.claim_id):
            raise NotFound("Claim not found")
        return self.repo.add(Reminder(**data.model_dump()))

    def update(self, rid: uuid.UUID, data: ReminderUpdate) -> Reminder:
        r = self.get(rid)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(r, k, v)
        return self.repo.save(r)

    def delete(self, rid: uuid.UUID) -> None:
        self.repo.delete(self.get(rid))

    # ---- scheduler logic ----
    def _has_auto(self, kind: str, policy_id=None, claim_id=None) -> bool:
        q = select(Reminder.id).where(Reminder.user_id == self.user_id, Reminder.is_auto.is_(True), Reminder.kind == kind,
                                      Reminder.is_completed.is_(False), Reminder.deleted_at.is_(None))
        if policy_id:
            q = q.where(Reminder.policy_id == policy_id)
        if claim_id:
            q = q.where(Reminder.claim_id == claim_id)
        return self.db.scalar(q) is not None

    def generate_auto(self, today: date | None = None) -> int:
        """Create reminders derived from the user's own recorded data. Idempotent."""
        today = today or date.today()
        created = 0
        for p in PolicyRepository(self.db, self.user_id).list():
            due = p.renewal_date or p.expiry_date
            if p.status == "active" and due and today <= due <= today + timedelta(days=RENEWAL_WINDOW_DAYS) \
                    and not self._has_auto("renewal", policy_id=p.id):
                self.repo.add(Reminder(title=f"Renew {p.name}", kind="renewal", due_date=due, policy_id=p.id, is_auto=True,
                                       description=f"Renewal date you recorded for {p.insurer} policy."))
                created += 1
        for c in ClaimRepository(self.db, self.user_id).list():
            if c.status == "additional_documents_required" and not self._has_auto("claim_documents", claim_id=c.id):
                self.repo.add(Reminder(title=f"Documents needed for claim {c.claim_ref}", kind="claim_documents",
                                       due_date=today, claim_id=c.id, policy_id=c.policy_id, is_auto=True,
                                       description="You marked this claim as needing additional documents."))
                created += 1
            if c.status == "pre_auth_requested" and (today - c.created_at.date()) >= timedelta(days=1) \
                    and not self._has_auto("preauth_followup", claim_id=c.id):
                self.repo.add(Reminder(title=f"Pre-authorisation pending for {c.patient_name} ({c.claim_ref})", kind="preauth_followup",
                                       due_date=today, claim_id=c.id, policy_id=c.policy_id, is_auto=True,
                                       description="Pre-authorisation was requested and no outcome is recorded yet. Update the status when you hear back."))
                created += 1
            if c.status in {"submitted", "under_review"} and c.submission_date \
                    and today - c.submission_date >= timedelta(days=FOLLOWUP_AFTER_DAYS) \
                    and not self._has_auto("claim_followup", claim_id=c.id):
                self.repo.add(Reminder(title=f"Follow up on claim {c.claim_ref}", kind="claim_followup", due_date=today,
                                       claim_id=c.id, policy_id=c.policy_id, is_auto=True,
                                       description="Submitted over 14 days ago. Check with your insurer and update the status manually."))
                created += 1
        return created

    def notify_due(self, today: date | None = None) -> int:
        """In-app notification (one per reminder) when a reminder becomes due."""
        today = today or date.today()
        n = 0
        for r in self.list(include_completed=False):
            if r.due_date > today:
                continue
            exists = self.db.scalar(select(Notification.id).where(Notification.user_id == self.user_id,
                                                                  Notification.reminder_id == r.id))
            if exists:
                continue
            self.db.add(Notification(user_id=self.user_id, reminder_id=r.id, title=r.title, body=r.description))
            n += 1
        self.db.commit()
        return n

    def run_checks(self) -> dict:
        return {"reminders_created": self.generate_auto(), "notifications_created": self.notify_due()}


def run_all_users() -> None:
    """Scheduled job: runs the checks for every active user."""
    from app.database.session import SessionLocal
    with SessionLocal() as db:
        for uid in db.scalars(select(User.id).where(User.deleted_at.is_(None), User.is_active.is_(True))):
            ReminderService(db, uid).run_checks()


def start_scheduler():
    if not get_settings().scheduler_enabled:
        return None
    from apscheduler.schedulers.background import BackgroundScheduler
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(run_all_users, "interval", hours=1, next_run_time=utcnow() + timedelta(seconds=30),
                  id="reminder-checks", max_instances=1, coalesce=True)
    sched.start()
    return sched
