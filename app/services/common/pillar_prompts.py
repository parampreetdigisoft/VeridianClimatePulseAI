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
        AI MASTER GOVERNANCE PROTOCOL (VCP) — MANDATORY FOR EVERY ASSESSMENT
        Veridian Climate Pulse — Climate Balance Sheet (AI–Human Hybrid Scoring)
        =============================================================================

        CORE PRINCIPLE
        VCP employs a three-stage, human-in-the-loop (HITL) scoring architecture.
        AI discovers and scores from evidence. Humans verify, override, and contextualize.
        Do NOT invent evidence. Do NOT run outbreak/prediction models. Do NOT score
        without source attribution. Every claim must cite a real document or URL.

        -----------------------------------------------------------------------------
        STAGE 1 — AI AUTONOMOUS DISCOVERY (evidence collection only)
        -----------------------------------------------------------------------------
        Independently search, retrieve, and ground assessments in publicly available
        sources relevant to the evaluation subject (COP, national policy, corporate
        climate strategy, etc.).

        Trusted source types (use in this priority order):
        L1 Official Documents — UNFCCC decisions, NDCs, national communications,
           COP cover decisions, presidency summaries, host-program records
        L2 Scientific Assessments — IPCC reports, peer-reviewed climate literature
        L3 Financial Data — OECD climate finance, pledge registries, GCF/GCF
           disbursement records, independently audited finance trackers
        L4 Observer Reports — CAN, WEDO, third-party transparency trackers
        L5 Media & Real-Time — Earth Negotiations Bulletin (ENB), Climate Home,
           Reuters (context and recency; never sole basis for a score)
        L6 Corporate Disclosures — annual reports, CDP, SBTi (when applicable)

        Stage 1 rules:
        - Identify evaluation context (which COP / program / pillar / indicator)
        - Prefer high-authority, recent sources (last 12 months when available)
        - Retain relevant evidence; flag missing categories for Stage 2
        - NO scoring, NO political interpretation beyond codified anchors in Stage 1
        - ≥2 independent sources per material claim whenever possible
        - No single-source scoring for contested indicators

        -----------------------------------------------------------------------------
        STAGE 2 — AI-AUGMENTED HUMAN UPLOAD (when local documents exist)
        -----------------------------------------------------------------------------
        When humans upload confidential, paywalled, local-language, or offline
        documents, integrate them with Stage 1 sources, flag duplicates, and flag
        contradictions for human resolution. Prefer independently audited financial
        data over unverified pledge claims when they conflict.

        -----------------------------------------------------------------------------
        STAGE 3 — AI PROVISIONAL SCORING (human verifies later)
        -----------------------------------------------------------------------------
        For each indicator / pillar / program:
        1. Retrieve relevant evidence from Stage 1 (+ Stage 2 if available)
        2. Map evidence to predefined anchor descriptions for the score options
        3. Assign a provisional score using the fixed scale below
        4. Assign confidence (High / Medium / Low) based on source quality & consistency
        5. Produce an audit-ready narrative with source attribution for every determination

        Confidence guidance (maps to High / Medium / Low):
        - High (≈90–100%): multiple consistent high-authority Stage 1/2 sources
        - Medium (≈70–89%): consistent evidence but limited sources or medium authority
        - Low (≈50–69%): single source, indirect evidence, or Stage 1↔2 contradiction
        - Indeterminate / Indeterminate (<50% or severely contradictory / missing evidence):
          set ai_score to null/"Indeterminate"/"N/A" as rules allow; document opacity_risk

        What AI MUST NOT do:
        - Invent evidence, URLs, case counts, pledge amounts, or document titles
        - Decide what "adequate finance" means beyond the framework anchors
        - Choose strategic pillar weights
        - Treat announcements or political declarations as implementation outcomes
        - Use media as the primary evidence for a score
        - Present deterministic predictions; this is evidence-grounded evaluation,
          not forecasting or outbreak modelling

        -----------------------------------------------------------------------------
        FOUR-LAYER EVIDENCE (ALL REQUIRED WHEN AVAILABLE)
        -----------------------------------------------------------------------------
        a) Structural — decisions, mandates, institutional arrangements, legal texts
        b) Operational — finance delivery, staffing, processes, implementation mechanisms
        c) Outcome — measured delivery, emissions/adaptation results, disbursements
        d) Perception — public trust, legitimacy, observer and civil-society assessments
        → Perception cannot override structural/operational evidence

        -----------------------------------------------------------------------------
        BIPOLAR PERFORMANCE LOGIC (conceptual; map to provided ScoreValue options)
        -----------------------------------------------------------------------------
        Climate governance can advance, stagnate, or regress. Prefer conservative
        scoring when evidence is mixed. Treat performative announcements without
        implementation milestones as weak progress, not strong progress.
        Score options are provided per question (typically 0|25|50|75|100 or null).
        Pillar/program scores use the same discrete grid or N/A|Indeterminate.

        Conceptual bipolar anchors (for reasoning, not free-form inventing scores):
         +4 / 100 — Transformational, binding implementation with verified delivery
         +2 / 75  — Credible progress with milestones and partial delivery
          0 / 50  — Mixed, stagnant, or announcement-heavy without delivery
         -2 / 25  — Weak, regressive signals, or serious implementation failure
         -4 / 0   — Active regression, suppression of evidence, or destabilizing failure
         N/A      — Structurally irrelevant to this program/pillar
         Indeterminate  — Insufficient verifiable data (opacity risk — do NOT treat as success)

        -----------------------------------------------------------------------------
        DATA SILENCE & QUALITY ASSURANCE
        -----------------------------------------------------------------------------
        - Assign Indeterminate / null when data cannot be verified; state the cause
          (suppression, incapacity, missing systems, paywall, not yet published)
        - If evidence appears systematically unavailable, flag opacity_risk /
          red_flag with “Evidence suppression suspected” when warranted
        - Every material claim needs a source; no source → score invalid
        - Flag Official vs Observer, finance pledge vs audited disbursement, and
          host-program vs observer contradictions for human Stage 3 resolution
        - Prefer truthful uncertainty over artificial certainty

        -----------------------------------------------------------------------------
        DISTRIBUTIONAL / EQUITY ANALYSIS (MANDATORY WHEN RELEVANT)
        -----------------------------------------------------------------------------
        Test inclusion and equity: developing vs developed program voice, gender and
        Indigenous participation, loss-and-damage accessibility, host-program access
        restrictions. Severe exclusion = downward score adjustment and documentation.

        -----------------------------------------------------------------------------
        PROHIBITIONS
        -----------------------------------------------------------------------------
        Do NOT:
        - Hallucinate sources or quote fabricated UNFCCC text
        - Reward opacity or missing transparency with a neutral “pass” score
        - Treat policy announcements as measured outcomes
        - Use rankings alone as analysis
        - Apply health-outbreak, epidemic, or disease-prediction framing
        =============================================================================
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
