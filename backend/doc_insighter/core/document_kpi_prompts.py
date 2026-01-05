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
    Analyze the provided technical document and extract key insights for a Technical Review Report:
        - Proposed Architecture and Design Patterns (e.g., Microservices vs Monolith)
        - Technology Stack Assessment (Suitability of languages, frameworks, and databases)
        - Scalability and High Availability Strategy (Load balancing, caching, replication)
        - Integration Interfaces (API standards, external system dependencies)
        - Security and Compliance (Authentication, authorization, data encryption)
        - Infrastructure and DevOps (Deployment strategy, CI/CD, containerization)
        - Critical Technical Risks and Single Points of Failure

    """

class CodeQuality:
    prompt = """
    Analyze the provided code and extract key insights for a technical quality report:
        - Architectural structural analysis (modularity and separation of concerns)
        - Adherence to language-specific best practices (e.g., PEP8 for Python)
        - Potential security vulnerabilities and sensitive data exposure
        - Performance bottlenecks and algorithmic complexity issues
        - Error handling robustness and edge case coverage
        - Maintainability score and technical debt assessment
        - Actionable refactoring recommendations
    """
class BestPractices:
    prompt = """
    Analyze the provided Engineering Guidelines or Process Document and generate a Best Practices Audit Report:
        - Version Control Strategy: Evaluation of branching strategies (e.g., GitFlow, Trunk-based) and commit standards.
        - Testing Maturity: Assessment of required testing layers (Unit, Integration, E2E) and coverage requirements.
        - CI/CD & Automation: Analysis of deployment pipelines, automated checks, and release procedures.
        - Code Review Standards: Evaluation of the peer review process, checklists, and approval requirements.
        - Security & Compliance: Check for "Security by Design" principles, dependency scanning, and secret management policies.
        - Documentation Standards: Requirements for API docs (Swagger), Readmes, and architecture decision records (ADRs).
        - GAP ANALYSIS: Identify missing industry standards or areas where the process is manual/outdated.
    """