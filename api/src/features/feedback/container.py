from shared.infrastructure.smtp_mailer import email_service
from features.feedback.application.feedback import ListPublicFeedback, SubmitFeedback
from features.feedback.infrastructure.feedback_repository import SqlFeedbackRepository


def get_submit_feedback() -> SubmitFeedback:
    return SubmitFeedback(SqlFeedbackRepository(), email_service)


def get_list_public_feedback() -> ListPublicFeedback:
    return ListPublicFeedback(SqlFeedbackRepository())
