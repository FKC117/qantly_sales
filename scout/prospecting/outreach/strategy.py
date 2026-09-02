from dataclasses import dataclass

from ..models import Prospect, ProspectAssessment


@dataclass(frozen=True)
class OutreachStrategy:
    entry_person: str
    motion: str
    cta: str


def build_outreach_strategy(prospect: Prospect) -> OutreachStrategy:
    """Choose a sales motion from the stored strategic assessment, not generic copy."""
    assessment = prospect.assessment
    account_type = assessment.account_type
    if account_type in {ProspectAssessment.AccountType.RECRUITER, ProspectAssessment.AccountType.CHANNEL_PARTNER}:
        return OutreachStrategy("Partnerships Lead", "referral or channel partnership", "referral_partnership")
    if account_type in {ProspectAssessment.AccountType.CONSULTING, ProspectAssessment.AccountType.TECHNOLOGY_PARTNER}:
        return OutreachStrategy("Partnerships or Practice Lead", "technology partnership or embedded analytics", "partnership_discussion")
    if account_type == ProspectAssessment.AccountType.INSTITUTIONAL:
        return OutreachStrategy("Research Director or Department Lead", "department-level research analytics pilot", "research_pilot")
    if assessment.customization_opportunity >= 60:
        return OutreachStrategy("Head of Data or Analytics", "customized enterprise pilot", "custom_deployment")
    if assessment.technical_fit >= 60:
        return OutreachStrategy("Data Science or Analytics Manager", "bottom-up technical evaluation with safe test data", "technical_feedback")
    return OutreachStrategy("Head of Data or Analytics", "invite to try Qantly", "try_qantly")
