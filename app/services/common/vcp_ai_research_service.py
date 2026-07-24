"""
    vcp_ai_research_service.py  (refactored)
    -----------------------------------------
    Orchestrates question / pillar / program-level AI research.

    Depends on:
        llm_base_service.LLMBaseService       — all LLM mechanics
        prompt_templates.VCPPromptTemplates   — all prompt text
        json_response_parser                  — JSON cleaning, validation, mapping
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from app.services.common.llm_base_service import LLMBaseService
from app.services.common.pillar_prompts import VCPPPillarPrompts
from app.services.common.program_prompt import VCPPromptTemplates
from app.services.common import json_response_parser as jrp
from app.services.core.repository import db_repository
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  User message templates (kept here; only the system prompt lives in         #
#  VCPPromptTemplates so service context stays visible)                       #
# --------------------------------------------------------------------------- #

_QUESTION_USER_TMPL = """
    Program: {program_name}
    program_description: {program_description}
    Location: {location}
    Pillar: {pillar_name}
    Question: {question_text}
    Year: {year}

    Return ONLY valid JSON.
"""

_PILLAR_USER_TMPL = """
    Program: {program_name}
    program_description: {program_description}
    Location: {location}
    Pillar: {pillar_name}
    Year: {year}

    Return ONLY valid JSON.
"""

_COUNTRY_USER_TMPL = """
    Program: {program_name}
    program_description: {program_description}
    Location: {location}
    Year: {year}
"""


# =========================================================================== #
class VCPResearchService:
    """
    AI service that conducts independent research and evidence-based scoring.

    All LLM calls are delegated to LLMBaseService.
    All prompt text comes from VCPPromptTemplates.
    All JSON parsing/mapping comes from json_response_parser.
    """

    def __init__(self) -> None:
        self._llm_svc = LLMBaseService(max_retries=3, retry_delay=1.0)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def research_and_score_question(
        self,
        program_name: str,
        program_description: str,
        location: str,
        pillarID: int,
        pillar_name: str,
        question_text: str,
        year: int = None,
    ) -> Dict[str, Any]:
        """Score a single question for a given program + pillar."""
        try:
            year = year or datetime.now().year
            pillars = await db_repository.get_active_pillars_map()
            pillar_context = VCPPPillarPrompts.get_pillar_context(pillarID, pillars)
            system_prompt = VCPPromptTemplates.question_system_prompt(pillar_context)

            label = f"question|{program_name}|pillar{pillarID}"
            raw = await self._llm_svc.invoke_chain(
                system_prompt=system_prompt,
                user_template=_QUESTION_USER_TMPL,
                variables={
                    "program_name": program_name,
                    "program_description": {program_description},
                    "location": location,
                    "pillar_name": pillar_name,
                    "question_text": question_text,
                    "year": year,
                },
                label=label,
            )

            analysis = json.loads(jrp.clean_json_response(raw))
            jrp.validate_question_response(analysis)
            return jrp.map_question_response(analysis, pillarID, year)

        except Exception as exc:
            logger.error("research_and_score_question failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def research_and_score_pillar(
        self,
        program_name: str,
        program_description: str,
        location: str,
        pillarId: int,
        pillar_name: str,
        year: int = None,
    ) -> Dict[str, Any]:
        """Score an entire pillar for a given program."""
        try:
            year = year or datetime.now().year
            pillars = await db_repository.get_active_pillars_map()
            pillar_context = VCPPPillarPrompts.get_pillar_context(pillarId, pillars)
            system_prompt = VCPPromptTemplates.pillar_system_prompt(pillar_context)

            label = f"pillar|{program_name}|pillar{pillarId}"
            raw = await self._llm_svc.invoke_chain(
                system_prompt=system_prompt,
                user_template=_PILLAR_USER_TMPL,
                variables={
                    "program_name": program_name,
                    "program_description": {program_description},
                    "location": location,
                    "pillar_name": pillar_name,
                    "year": year
                },
                label=label,
            )

            analysis = json.loads(jrp.clean_json_response(raw))
            jrp.validate_pillar_response(analysis)
            return jrp.map_pillar_response(analysis, pillarId, year)

        except Exception as exc:
            logger.error("research_and_score_pillar failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def research_and_score_program(
        self,
        program_name: str,
        program_description: str,
        location: str,
        year: int = None,
    ) -> Dict[str, Any]:
        """Produce a cross-pillar program-level Healthassessment."""
        try:
            year = year or datetime.now().year
            pillars = await db_repository.get_active_pillars_map()
            pillar_names = VCPPPillarPrompts.get_all_pillar_names(pillars)
            pillar_list_str = "\n".join(
                f"{k}. {v}" for k, v in pillar_names.items()
            )
            system_prompt = VCPPromptTemplates.program_system_prompt(
                pillar_list_str=pillar_list_str
            )

            label = f"program|{program_name}"
            raw = await self._llm_svc.invoke_chain(
                system_prompt=system_prompt,
                user_template=_COUNTRY_USER_TMPL,
                variables={
                    "program_name": program_name,
                    "program_description": program_description,
                    "location": location,
                    "year": year,
                },
                label=label,
            )

            analysis = json.loads(jrp.clean_json_response(raw))
            jrp.validate_program_response(analysis)
            return jrp.map_program_response(analysis, year)

        except Exception as exc:
            logger.error("research_and_score_program failed: %s", exc)
            return {"success": False, "error": str(exc)}
        

    async def immediate_situation(
        self,
        program_name: str,
        program_description: str,
        location: str,
        ai_program_context: str,
        documentContext: Optional[str],
        year: int = None,
    ) -> Dict[str, Any]:
        """Produce a cross-pillar program-level Healthassessment."""
        try:
            # Fix: Proper length check
            if not documentContext or len(documentContext) < 100:
                pillars = await db_repository.get_active_pillars_map()
                pillar_names = VCPPPillarPrompts.get_all_pillar_names(pillars)
                pillar_list_str = "\n".join(
                    f"{k}. {v}" for k, v in pillar_names.items()
                )

                system_prompt = VCPPromptTemplates.program_situation_awareness_system_prompt(
                    pillar_list_str
                )
            else:
                system_prompt = VCPPromptTemplates.program_summery_system_prompt(
                    publicContext=ai_program_context,
                    documentContext=documentContext
                )

            label = f"program|{program_name}"

            raw = await self._llm_svc.invoke_chain(
                system_prompt=system_prompt,
                user_template=_COUNTRY_USER_TMPL,
                variables={
                    "program_name": program_name,
                    "program_description": {program_description},
                    "location": location,
                    "year": year,
                },
                label=label,
            )

            analysis = json.loads(jrp.clean_json_response(raw))
            return jrp.build_immediateSituation_record(analysis)

        except Exception as exc:
            logger.error("immediate_situation failed: %s", exc)
            return {"success": False, "error": str(exc)}



# Module-level singleton — import and use this in routers / tasks.
vcp_ai_research_service = VCPResearchService()
