from pydantic import BaseModel

class SOW:
    prompt = """
    Extract below given key insights from provided data
        - Clear project objectives and timeline
        - Detailed scope broken into 5 phases
        - Specific deliverables with due dates
        - Roles and responsibilities for both parties
        - Acceptance criteria for quality assurance
        - Risk management strategies
        - Payment terms
    """

class WSR:
    prompt = """
    Extract below given key insights from the provided Weekly Status Report (WSR):
        - Project overview and reporting period
        - Overall project status (On Track, At Risk, Delayed)
        - Key accomplishments and milestones achieved this week
        - Work in progress and current activities
        - Upcoming tasks and planned activities for next week
        - Risks and issues identified
        - Blockers and dependencies
        - Resource utilization and team status
        - Budget and timeline status
        - Action items and decisions needed
    """

class TechReview:
    prompt = """

    """