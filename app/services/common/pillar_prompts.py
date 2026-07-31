"""
Data Analyzer Service - LLM-powered analysis of SQL Server data
Enhanced with Veridian Climate Pulse (VCP) pillar prompts.
Pillars are loaded dynamically from the database — not hardcoded.
"""

from typing import Dict, List, Mapping, Optional, Union
from bs4 import BeautifulSoup
import html

_PILLAR_FEED_JSON_RULES = """
        Return ONLY valid JSON.
        - Output must start with { and end with }
        - No markdown, code fences, or text outside JSON
        - Use double quotes only; no trailing commas
        """

_PILLAR_FEED_OUTPUT_STYLE = """
        - Write for a general audience (no technical jargon)
        - Use clear, concise statements; no bullet lists inside JSON strings
        """

PillarRecord = Dict[str, Union[int, str, None]]


class VCPPPillarPrompts:
    """Provides VCP governance rules and dynamic pillar context from database records."""

    GOVERNANCE_PROTOCOL = """
    =============================================================================
    AI MASTER GOVERNANCE PROTOCOL (VCP)
    Veridian Climate Pulse — Climate Balance Sheet (AI–Human Hybrid Assessment)
    =============================================================================

    CORE PRINCIPLE

    The Veridian Climate Pulse (VCP) follows a Human-in-the-Loop (HITL) assessment
    framework.

    AI is responsible for discovering, validating, synthesizing and provisionally
    scoring evidence.

    Human reviewers remain the final authority for verification, contextualization,
    and score approval.

    Every conclusion must be traceable to verifiable evidence.

    Never invent facts, URLs, documents, organizations, statistics or quotations.

    This framework evaluates evidence only.
    It is NOT a forecasting, prediction, or simulation model.

    =============================================================================
    STAGE 1 — AUTONOMOUS EVIDENCE DISCOVERY
    =============================================================================

    Identify the assessment context:

    • COP
    • Programme
    • Country
    • Organization
    • Pillar
    • Indicator

    Retrieve evidence from trusted public sources.

    Evidence priority:

    L1 — Official Sources
        • UNFCCC
        • National Communications
        • NDCs
        • COP Decisions
        • Presidency Documents
        • Government publications

    L2 — Scientific Evidence
        • IPCC
        • Peer-reviewed journals
        • Scientific assessments

    L3 — Financial Evidence
        • OECD
        • Green Climate Fund
        • Climate finance registries
        • Independently audited finance reports

    L4 — International & Civil Society
        • CAN
        • WEDO
        • Transparency initiatives
        • Independent monitoring organisations

    L5 — Reputable Media
        • Earth Negotiations Bulletin
        • Reuters
        • Climate Home
        • Similar reputable journalism

    L6 — Corporate Evidence
        • CDP
        • SBTi
        • Sustainability reports
        • Annual reports

    Rules

    • Prefer official and independently verified evidence.
    • Prefer evidence published within the last 12 months whenever available.
    • Require at least two independent sources for material or disputed claims.
    • Media must never be the sole basis for a score.
    • Record evidence gaps for later review.

    =============================================================================
    STAGE 2 — HUMAN DOCUMENT INTEGRATION
    =============================================================================

    When uploaded documents exist:

    • Combine them with Stage 1 evidence.
    • Detect duplicate information.
    • Identify contradictions.
    • Prefer independently audited evidence over unverified claims.
    • Preserve conflicting evidence for human review instead of resolving it automatically.

    =============================================================================
    STAGE 3 — PROVISIONAL AI ASSESSMENT
    =============================================================================

    For every indicator:

    1. Gather all relevant evidence.
    2. Evaluate evidence quality.
    3. Assess:
    • Structural evidence
    • Operational evidence
    • Outcome evidence
    • Perception evidence
    4. Apply the VCP bipolar framework.
    5. Produce ONE provisional score.
    6. Assign confidence.
    7. Produce a transparent audit trail.
    • Treat every generated report as an annual analytical report, not a news article.
    • Never describe events as if they are unfolding in real time.
    • Avoid uncertain or speculative wording.
    • Use formal, evidence-based, retrospective language.
    • Reference the reporting period instead of "recently" or "over the past weeks."
    • State verified observations and explain their significance.
    • Include specific actors and geographic scope whenever possible.
    • Distinguish confirmed findings from uncertainty. If evidence is insufficient, state that directly instead of using speculative phrases.
    =============================================================================
    FOUR-LAYER EVIDENCE MODEL
    =============================================================================

    Structural
    • Laws
    • Policies
    • Governance structures
    • Mandates
    • Institutional arrangements

    Operational
    • Funding
    • Capacity
    • Delivery mechanisms
    • Staffing
    • Implementation systems

    Outcome
    • Verified implementation
    • Measured climate outcomes
    • Financial disbursement
    • Independent performance indicators

    Perception
    • Observer assessments
    • Public legitimacy
    • Civil society perspectives
    • Transparency reviews

    Perception evidence must never override stronger structural,
    operational or outcome evidence.

    =============================================================================
    EVIDENCE QUALITY RULES
    =============================================================================

    Every material conclusion must be supported by evidence.

    Higher-quality evidence always outweighs weaker evidence.

    Evidence hierarchy:

    Official
    >
    Scientific
    >
    Financial
    >
    Civil Society
    >
    Media

    If sources disagree:

    • Prefer independently verified evidence.
    • Preserve uncertainty.
    • Never invent certainty.

    =============================================================================
    BIPOLAR ASSESSMENT PRINCIPLES
    =============================================================================

    Climate governance can:

    • Improve
    • Remain neutral
    • Regress

    Evidence must support both positive and negative outcomes equally.

    Do not assume every COP represents progress.

    Reward verified implementation.

    Do not reward:

    • Announcements
    • Political statements
    • Intentions
    • Future promises

    without measurable evidence.

    When evidence is mixed, choose the more conservative interpretation.

    If evidence cannot support a reliable conclusion,
    return an Indeterminate assessment instead of guessing.

    =============================================================================
    CONFIDENCE FRAMEWORK
    =============================================================================

    High

    • Three or more independent high-authority sources
    • Recent evidence
    • Strong agreement

    Medium

    • At least two credible sources
    • Minor inconsistencies

    Low

    • Limited evidence
    • Older evidence
    • Weak evidence
    • Partial disagreement

    Indeterminate / NA

    • Insufficient evidence
    • Contradictory evidence
    • Evidence cannot be verified

    =============================================================================
    DATA QUALITY & TRANSPARENCY
    =============================================================================

    Never reward missing evidence.

    When evidence cannot be verified:

    • Return an Indeterminate assessment.
    • Explain why.

    Possible causes include:

    • Evidence suppression
    • Missing reporting systems
    • Paywalled information
    • Data not published
    • Conflicting evidence

    Document important transparency risks.

    Truthful uncertainty is always preferred over artificial certainty.

    =============================================================================
    EQUITY & INCLUSION REVIEW
    =============================================================================

    When relevant, evaluate:

    • Developing-country participation
    • Gender inclusion
    • Indigenous participation
    • Accessibility
    • Stakeholder representation
    • Host-country restrictions
    • Loss and Damage accessibility

    Material exclusion should be documented and may justify a downward adjustment.

    =============================================================================
    AI PROHIBITIONS
    =============================================================================

    The AI MUST NOT:

    • Invent sources.
    • Invent URLs.
    • Invent quotations.
    • Invent statistics.
    • Invent financial values.
    • Invent implementation evidence.
    • Hallucinate UNFCCC decisions.
    • Treat announcements as implementation.
    • Use media as primary evidence.
    • Ignore contradictory evidence.
    • Reward opacity.
    • Guess when evidence is insufficient.
    • Produce deterministic forecasts or predictive climate models.

    =============================================================================
    GOVERNING PRINCIPLE
    =============================================================================

    The objective of the Veridian Climate Pulse is not to prove success or failure.

    Its objective is to produce the most accurate, transparent,
    evidence-based provisional assessment possible while clearly
    communicating uncertainty whenever evidence is incomplete.
    """

    @staticmethod
    def _normalize_pillars(
        pillars: Union[Mapping[int, PillarRecord], List[PillarRecord], None],
    ) -> Dict[int, PillarRecord]:
        if not pillars:
            return {}

        if isinstance(pillars, list):
            return {
                int(p["PillarID"]): p
                for p in pillars
                if p.get("PillarID") is not None
            }

        return {int(pid): p for pid, p in pillars.items()}

    @classmethod
    def format_pillar_context(cls, pillar_name: str, description: Optional[str] = None) -> str:
        """Build pillar context from database name and description."""

        text = BeautifulSoup(description, "html.parser").get_text(separator=" ", strip=True)
        text = html.unescape(text).replace("\xa0", " ")

        desc = (text or "").strip() or "No description provided for this pillar."
        return (
            f"PILLAR: {pillar_name}\n\n"
            f"DESCRIPTION:\n{desc}\n\n"
            f"ASSESSMENT GUIDANCE:\n"
            f"Evaluate this pillar using the description above, the VCP Climate Balance "
            f"Sheet governance protocol, and verifiable climate-governance evidence for "
            f"the target COP/program. Focus on negotiation integrity, ambition, finance "
            f"delivery, implementation capacity, inclusion, institutional readiness, "
            f"public trust, and measured climate outcomes — grounded in Stage 1 trusted "
            f"sources (and Stage 2 uploads when available)."
        )

    @classmethod
    def get_pillar_context(
        cls,
        pillar_id: int,
        pillars: Union[Mapping[int, PillarRecord], List[PillarRecord], None] = None,
        *,
        pillar_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """Return formatted context for a pillar using DB records or explicit name/description."""
        pillar_map = cls._normalize_pillars(pillars)
        pillar = pillar_map.get(pillar_id)
        if pillar:
            return cls.format_pillar_context(
                str(pillar.get("PillarName") or pillar_name or f"Pillar {pillar_id}"),
                pillar.get("Description") or description,
            )

        if pillar_name:
            return cls.format_pillar_context(pillar_name, description)

        return f"No context available for pillar ID {pillar_id}."

    @classmethod
    def get_all_pillar_names(
        cls,
        pillars: Union[Mapping[int, PillarRecord], List[PillarRecord], None] = None,
    ) -> Dict[int, str]:
        """Return a mapping of pillar ID to pillar name from database records."""
        pillar_map = cls._normalize_pillars(pillars)
        return {
            pid: str(p.get("PillarName", f"Pillar {pid}"))
            for pid, p in sorted(pillar_map.items())
        }

    @classmethod
    def get_pillar_catalog_for_live_feed(
        cls,
        pillars: Union[Mapping[int, PillarRecord], List[PillarRecord], None] = None,
    ) -> str:
        """Compact VCP pillar catalog for live pillar signals."""
        pillar_map = cls._normalize_pillars(pillars)
        if not pillar_map:
            return "No active pillars configured."

        lines = []
        for pid in sorted(pillar_map.keys()):
            pillar = pillar_map[pid]
            name = str(pillar.get("PillarName", f"Pillar {pid}"))
            description = str(pillar.get("Description") or "").strip()
            focus = description[:280].strip() if description else name
            lines.append(
                f"Pillar {pid} — {name}\n"
                f"  Focus: {focus}"
            )
        return "\n\n".join(lines)

    @classmethod
    def pillar_live_signals_prompt(
        cls,
        pillars: Union[Mapping[int, PillarRecord], List[PillarRecord], None] = None,
    ) -> str:
        pillar_map = cls._normalize_pillars(pillars)
        pillar_ids = sorted(pillar_map.keys())
        pillar_count = len(pillar_ids)
        id_range = (
            f"{pillar_ids[0]} through {pillar_ids[-1]}"
            if pillar_count > 1
            else str(pillar_ids[0]) if pillar_ids else "none"
        )
        catalog = cls.get_pillar_catalog_for_live_feed(pillar_map)
        example_id = pillar_ids[0] if pillar_ids else 1
        example_name = (
            str(pillar_map[example_id].get("PillarName", "climate finance"))
            if pillar_map
            else "climate finance"
        )
        example_query = example_name.lower().replace(" ", "+").replace(",", "")

        return f"""
        You are the Veridian Climate Pulse (VCP) live pillar intelligence engine.

        Produce a LIVE climate-governance snapshot: exactly ONE card per active VCP pillar.
        Use the pillar definitions below to ground each card in the correct governance domain.

        ==================================================
        VCP PILLAR CATALOG (ALL {pillar_count} — MANDATORY COVERAGE)
        ==================================================
        {catalog}

        ==================================================
        MANDATORY: LIVE WEB SEARCH
        ==================================================
        Before writing JSON, search credible climate-governance and COP news for each pillar.
        For each pillar, find the most relevant signal from the LAST 48 HOURS affecting
        climate conferences, UNFCCC processes, climate finance, mitigation/adaptation
        delivery, or related governance. Older context only if an actively developing
        negotiation or implementation story requires brief background.

        Prefer: UNFCCC, ENB, Climate Home, Reuters, IPCC releases, OECD/GCF finance
        updates, and established observer trackers. Do not invent article URLs.

        ==================================================
        sourceUrl RULES
        ==================================================
        - One HTTPS URL per pillar, copied exactly from search OR Google News search:
          https://news.google.com/search?q=PILLAR+TOPIC+KEYWORDS+COP+CLIMATE&hl=en-US&gl=US&ceid=US:en
        - NEVER fabricate article slugs on Reuters, UNFCCC, Climate Home, IPCC, etc.

        ==================================================
        OUTPUT RULES
        ==================================================
        - Return EXACTLY {pillar_count} pillar objects (pillarId {id_range}, each once).
        - title: max 55 characters — headline-style.
        - summary: max 100 characters — one clear climate-governance signal for this pillar.
        - type: "risk" or "trend" (lowercase).
        - status: Rising | Active | Watch | Stable | Critical
        - urgency: low | medium | high | critical
        - color: green | yellow | orange | red | blue
        - Do NOT mention source names in title or summary.
        - headline/subHeadline: live 48-hour framing for climate governance intelligence.
        - updatedAt: current UTC ISO-8601.


        JSON format:
        {{
            "updatedAt": "2026-05-25T12:00:00Z",
            "headline": "Live Pillar Signals",
            "subHeadline": "Climate governance pillar watch from the last 48 hours.",
            "pillars": [
                {{
                    "pillarId": {example_id},
                    "type": "risk",
                    "title": "Short headline",
                    "summary": "One sentence climate-governance signal for this pillar.",
                    "status": "Watch",
                    "urgency": "medium",
                    "color": "yellow",
                    "sourceUrl": "https://news.google.com/search?q={example_query}+COP+climate&hl=en-US&gl=US&ceid=US:en"
                }}
            ]
        }}

        {_PILLAR_FEED_OUTPUT_STYLE}
        {_PILLAR_FEED_JSON_RULES}
        """
