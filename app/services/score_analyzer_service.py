"""
Score Analyzer Service
----------------------
Orchestrates AI scoring for questions, pillars, and programs.
Delegates all LLM calls to VCPResearchService.
Persists results via DatabaseRepository.
"""

import math
import logging
from datetime import datetime
from typing import Any, Optional
logger = logging.getLogger(__name__)
from app.services.core.repository import DatabaseRepository
from app.services.common.vcp_ai_research_service import VCPResearchService
from app.services.rag_query_service import rag_query_service
#  To DB after every N records (currently 1 = immediate upsert).
#  Increase for bulk jobs to reduce round-trips.
_BATCH_SIZE = 5


# =========================================================================== #
class ScoreAnalyzerService:
    """
    Coordinates AI scoring workflows across questions, pillars, and programs.

    Responsibilities
    ----------------
    - Fetch evaluation data from DB views
    - Call VCPResearchService for AI scoring
    - Build DB-ready records
    - Upsert results in configurable batches
    """

    __slots__ = ("_db", "_ai")

    def __init__(self) -> None:
        self._db = DatabaseRepository()
        self._ai = VCPResearchService()

    # ------------------------------------------------------------------ #
    #  Safe type converters                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_float(value) -> float:
        """Convert any value to a finite float, defaulting to 0.0."""
        if value is None:
            return 0.0
        if isinstance(value, float):
            return 0.0 if (math.isnan(value) or math.isinf(value)) else round(value, 2)
        if isinstance(value, int):
            return float(value)
        if isinstance(value, str):
            s = value.strip().lower()
            if s in {"", "null", "none", "nan", "inf", "-inf", "infinity", "-infinity"}:
                return 0.0
            try:
                val = float(s.replace(",", ""))
                return 0.0 if (math.isnan(val) or math.isinf(val)) else round(val, 2)
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    @staticmethod
    def _to_int(value) -> int:
        """Convert any value to an int, defaulting to 0."""
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return 0 if (math.isnan(value) or math.isinf(value)) else int(value)
        if isinstance(value, str):
            s = value.strip().lower()
            if s in {"", "null", "none", "nan", "inf", "-inf", "infinity", "-infinity"}:
                return 0
            try:
                return int(float(s.replace(",", "")))
            except (ValueError, TypeError):
                return 0
        return 0

    @staticmethod
    def _discrepancy(ai_progress: float, evaluator_score: Optional[float]) -> float:
        """Absolute difference between AI and evaluator scores."""
        if evaluator_score is not None:
            return abs(ai_progress - evaluator_score)
        return ai_progress

    # ------------------------------------------------------------------ #
    #  Data fetch helpers                                                 #
    # ------------------------------------------------------------------ #

    async def _fetch_programs(self, program_id: Optional[int] = None):
        where = (
            f"WHERE IsDeleted = 0 AND ClimateProgramID = {program_id}"
            if program_id
            else "WHERE IsDeleted = 0"
        )
        return await self._db.engine.fetch_df_async(
            f"SELECT ClimateProgramID, ProgramName, Description, Year, Location FROM ClimatePrograms {where}"
        )

    @staticmethod
    def _continent_label(program) -> str:
        return f"Location: {program.Location}, Program: {program.ProgramName}"

    # ------------------------------------------------------------------ #
    #  Public entry points                                                #
    # ------------------------------------------------------------------ #

    async def analyze_all_programs(self, program_id: Optional[int] = None) -> bool:
        """
        Run full analysis (questions → pillars → program) for all programs,
        or a single program when program_id is provided.
        """
        try:
            programs = await self._fetch_programs(program_id)
            if programs.empty:
                logger.error("No programs found for analysis.")
                return False

            for program in programs.itertuples(index=False):
                try:
                    await self._analyze_questions(program)
                    await self._analyze_pillars(program)
                    await self._analyze_program(program)
                except Exception as exc:
                    logger.error(
                        "Program %d (%s) analysis failed: %s",
                        program.ClimateProgramID,
                        program.ProgramName,
                        exc,
                    )
            return True

        except Exception as exc:
            logger.error("analyze_all_programs failed: %s", exc, exc_info=True)
            raise

    async def analyze_single_program(self, program_id: int) -> bool:
        """Score overall program-level assessment only."""
        return await self._run_for_program(program_id, self._analyze_program)

    async def analyze_program_pillars(
        self, program_id: int, pillar_id: Optional[int] = None
    ) -> bool:
        """Score all pillars (or a single pillar) for a program."""
        return await self._run_for_program(
            program_id, self._analyze_pillars, pillar_id=pillar_id
        )

    async def analyze_program_questions(
        self, program_id: int, pillar_id: Optional[int] = None
    ) -> bool:
        """Score all questions (or a single pillar's questions) for a program."""
        return await self._run_for_program(
            program_id, self._analyze_questions, pillar_id=pillar_id
        )
    
    async def import_missing_program_questions(
        self, program_id: int, pillar_id: Optional[int] = None
    ) -> bool:
        """Score all questions (or a single pillar's questions) for a program."""
        return await self._run_for_program(
            program_id, self._analyze_questions, pillar_id=pillar_id,missing_only=True
        )
    # ------------------------------------------------------------------ #
    #  Internal dispatcher                                                #
    # ------------------------------------------------------------------ #

    async def _run_for_program(self, program_id: int, handler, **kwargs) -> bool:
        """Fetch a single program row then call *handler* on it."""
        try:
            programs = await self._fetch_programs(program_id)
            if programs.empty:
                return False
            for program in programs.itertuples(index=False):
                await handler(program, **kwargs)
            return True
        except Exception as exc:
            logger.error(
                "%s failed for program %d: %s",
                handler.__name__,
                program_id,
                exc,
                exc_info=True,
            )
            raise

    # ------------------------------------------------------------------ #
    #  Core analyzers                                                     #
    # ------------------------------------------------------------------ #

    async def _analyze_questions(
        self,
        program: Any,
        pillar_id: Optional[int] = None,
        missing_only = False
    ) -> bool:

        programID = int(program.ClimateProgramID)
        year = datetime.now().year

        where = f"ClimateProgramID = {programID}"

        if pillar_id is not None:
            where += f" AND PillarID = {pillar_id}"

        if missing_only:
            where += f"""
                AND QuestionID NOT IN
                (
                    SELECT QuestionID
                    FROM AIEstimatedQuestionScores
                    WHERE Year = {year}
                )
            """
        df = await self._db.get_view_data("vw_AiProgramPillarQuestionEvaluations", where)
        if df.empty:
            logger.info("No questions found: program %d", program.ClimateProgramID)
            return False

        target_pillars = (
            [pillar_id] if pillar_id is not None else df["PillarID"].unique().tolist()
        )

        for pid in target_pillars:
            batch: list[dict] = []

            for row in df[df["PillarID"] == pid].itertuples(index=False):
                try:
                    ai_data = await self._ai.research_and_score_question(
                        program_name=program.ProgramName,
                        program_description = program.Description,
                        location=self._continent_label(program),
                        pillarID=row.PillarID,
                        pillar_name=row.PillarName,
                        question_text=row.QuestionText,
                        year=program.Year
                    )
                    if not ai_data.get("success"):
                        logger.warning(
                            "AI failed for question %d, program %d",
                            row.QuestionID,
                            program.ClimateProgramID,
                        )
                        continue

                    normalized = self._safe_normalized(0)
                    batch.append(self._build_question_record(row, ai_data, normalized))
                    batch = await self._flushQuestion (
                        program.ClimateProgramID, batch ,self._db.bulk_upsert_question_evaluations
                    )
                except Exception as exc:
                    logger.error(
                        "Question %d, program %d: %s",
                        row.QuestionID,
                        program.ClimateProgramID,
                        exc,
                        exc_info=True,
                    )

            await self._flushQuestion(
                program.ClimateProgramID, batch ,self._db.bulk_upsert_question_evaluations, force=True
            )
            await self._db.AiInsertAnalyticalLayerResults(program.ClimateProgramID)

        return True

    async def _analyze_pillars(
        self,
        program: Any,
        pillar_id: Optional[int] = None,
    ) -> bool:
        """Score every pillar for a program."""
        where = f"climateProgramID = {program.ClimateProgramID}"
        if pillar_id is not None:
            where += f" AND PillarID = {pillar_id}"

        df = await self._db.get_view_data("vw_AiProgramPillarEvaluation", where)
        if df.empty:
            logger.info("No pillar evaluations found: program %d", program.ClimateProgramID)
            return False

        pillar_batch: list[dict] = []
        source_batch: list[dict] = []

        for row in df.itertuples(index=False):
            try:
                ai_data = await self._ai.research_and_score_pillar(
                    program_name=program.ProgramName,
                    program_description = program.Description,
                    location=self._continent_label(program),
                    pillarId=row.PillarID,
                    pillar_name=row.PillarName,
                    year=program.Year
                )
                if not ai_data.get("success"):
                    continue

                pillar_batch.append(
                    self._build_pillar_record(row, ai_data, program.ClimateProgramID)
                )
                source_batch.extend(self._build_source_records(row, ai_data))

                pillar_batch, source_batch = await self._flush_pillar(
                    pillar_batch, source_batch
                )

            except Exception as exc:
                logger.error(
                    "Pillar %d, program %d: %s",
                    row.PillarID,
                    program.ClimateProgramID,
                    exc,
                    exc_info=True,
                )
        try:             
            await self._flush_pillar(pillar_batch, source_batch, force=True)
            await self._db.AiRecalculateProgramScore(program.ClimateProgramID)
        except Exception as exc:
            logger.error(
                "Pillar %d, program %d: %s",
                program.ClimateProgramID,
                exc,
                exc_info=True,
            )
        
        return True

    async def _analyze_program(self, program: Any, **_) -> bool:
        """Score the overall program-level Healthassessment."""
        df = await self._db.get_view_data(
            "vw_AiProgramEvaluations", f"climateProgramID = {program.ClimateProgramID}"
        )
        if df.empty:
            logger.info("No program evaluations found: program %d", program.ClimateProgramID)
            return False

        batch: list[dict] = []

        for row in df.itertuples(index=False):
            try:
                ai_data = await self._ai.research_and_score_program(
                    program_name=program.ProgramName,
                    program_description = program.Description,
                    location=self._continent_label(program),
                    year=program.Year
                )
                if not ai_data.get("success"):
                    continue

                batch.append(self._build_program_record(row, ai_data))
                batch = await self._flush(
                    batch, self._db.bulk_upsert_program_evaluations
                )

            except Exception as exc:
                logger.error(
                    "Program evaluation %d: %s",
                    program.ClimateProgramID,
                    exc,
                    exc_info=True,
                )

        await self._flush(batch, self._db.bulk_upsert_program_evaluations, force=True)

        await self.immediateSituation(program.ClimateProgramID)
        await self._db.AiRecalculateProgramScore(program.ClimateProgramID)
        
        return True

    async def immediateSituation(self, program_id: int, **_) -> bool:
        """Score the overall program-level Healthassessment."""
        year = datetime.now().year        

        ai_program= await self._db.get_ai_program_context(program_id, year)
        program_Name = ai_program["ProgramName"]
        description = ai_program["Description"]
        location =ai_program["Location"]

        question = f"""
        What are the most critical recent developments, emerging risks, structural weaknesses, and key strengths across all major sectors in {program_Name}? Include insights on governance, security, economy, social cohesion, infrastructure, and institutional effectiveness. Focus on cross-pillar patterns and high-impact information relevant for executive-level program assessment and situational awareness.
        """

        document_context = await rag_query_service.get_program_document_context(program_id, question)

        if ai_program:
            ai_program_context = "\n".join(f"{key}: {value}" for key, value in ai_program.items())
        else:
            ai_program_context = ""

        ai_data = await self._ai.immediate_situation(
                    program_name=program_Name,
                    program_description=description,
                    location =location,
                    ai_program_context=ai_program_context,
                    documentContext=document_context,
                    year=year
                )

        result = self._build_immediateSituation_record(program_id, ai_data)
        
        await self._db.save_immediate_situation_summary(program_id,year,result)
        
        
        return True

    # ------------------------------------------------------------------ #
    #  Record builders                                                   #
    # ------------------------------------------------------------------ #

    def _build_question_record(
        self,
        row: Any,
        ai: dict,
        normalized_value: float,
    ) -> dict:
        ai_progress = self._to_float(ai.get("AIProgress") or 0)
        evaluator_score = self._to_float(normalized_value * 100)

        return {
            "ClimateProgramID": row.ClimateProgramID,
            "PillarID": row.PillarID,
            "QuestionID": row.QuestionID,
            "Year": self._to_int(ai.get("Year")),
            "AIScore": self._to_float(ai.get("AIScore")),
            "AIProgress": ai_progress,
            "EvaluatorScore": evaluator_score,
            "Discrepancy": self._discrepancy(ai_progress, evaluator_score),
            "ConfidenceLevel": ai.get("ConfidenceLevel"),
            "EvidenceSummary": ai.get("EvidenceSummary"),
            "StructuralEvidence": ai.get("StructuralEvidence"),
            "OperationalEvidence": ai.get("OperationalEvidence"),
            "OutcomeEvidence": ai.get("OutcomeEvidence"),
            "PerceptionEvidence": ai.get("PerceptionEvidence"),
            "TemporalScope": ai.get("TemporalScope"),
            "DistortionScreening": ai.get("DistortionScreening"),
            "RelationalDependencies": ai.get("RelationalDependencies"),
            "StressGeopoliticalShock": ai.get("StressGeopoliticalShock"),
            "StressFinanceShock": ai.get("StressFinanceShock"),
            "StressLegitimacyShock": ai.get("StressLegitimacyShock"),
            "StressOverallResilienceShock": ai.get("StressOverallResilienceShock"),
            "InclusionEquityAdjustment": ai.get("InclusionEquityAdjustment"),
            "OpacityRisk": ai.get("OpacityRisk"),
            "RedFlag": ai.get("RedFlag"),
            "SourceName": ai.get("SourceName"),
            "SourceType": ai.get("SourceType"),
            "SourceURL": ai.get("SourceURL"),
            "SourceDataYear": self._to_int(ai.get("SourceDataYear")),
            "SourceHierarchyLevel": self._to_int(ai.get("SourceHierarchyLevel")),
            "SourceDataExtract": ai.get("SourceDataExtract"),
            "SourcesConsulted": self._to_int(ai.get("SourcesConsulted")),
        }

    def _build_pillar_record(self, row: Any, ai: dict, program_id: int) -> dict:
        ai_progress = self._to_float(ai.get("AIProgress") or 0)
        evaluator_score = self._to_float(0)

        return {
            "ClimateProgramID": program_id,
            "PillarID": row.PillarID,
            "Year": ai.get("Year"),
            "AIScore": self._to_float(ai.get("AIScore")),
            "AIProgress": ai_progress,
            "EvaluatorScore": evaluator_score,
            "Discrepancy": self._discrepancy(ai_progress, evaluator_score),
            "ConfidenceLevel": ai.get("ConfidenceLevel"),
            "EvidenceSummary": ai.get("EvidenceSummary"),
            "StructuralEvidence": ai.get("StructuralEvidence"),
            "OperationalEvidence": ai.get("OperationalEvidence"),
            "OutcomeEvidence": ai.get("OutcomeEvidence"),
            "PerceptionEvidence": ai.get("PerceptionEvidence"),
            "TemporalScope": ai.get("TemporalScope"),
            "DistortionScreening": ai.get("DistortionScreening"),
            "RelationalIntegrity": ai.get("RelationalIntegrity"),
            "StressGeopoliticalShock": ai.get("StressGeopoliticalShock"),
            "StressFinanceShock": ai.get("StressFinanceShock"),
            "StressLegitimacyShock": ai.get("StressLegitimacyShock"),
            "StressOverallResilience": ai.get("StressOverallResilience"),
            "StressScoreAdjustment": ai.get("StressScoreAdjustment"),
            "InclusionEquityAdjustment": ai.get("InclusionEquityAdjustment"),
            "OpacityRisk": ai.get("OpacityRisk"),
            "NonCompensationNote": ai.get("NonCompensationNote"),
            "InclusionAccessNote": ai.get("InclusionAccessNote"),
            "InstitutionalAssessment": ai.get("InstitutionalAssessment"),
            "DataGapAnalysis": ai.get("DataGapAnalysis"),
            "RedFlag": ai.get("RedFlag"),
        }

    def _build_program_record(self, row: Any, ai: dict) -> dict:
        ai_progress = self._to_float(ai.get("AIProgress") or 0)
        evaluator_score = self._to_float(row.EvaluatorScore)

        return {
            "ClimateProgramID": row.ClimateProgramID,
            "Year": self._to_int(ai.get("Year") or datetime.now().year),
            "AIScore": self._to_float(ai.get("AIScore")),
            "AIProgress": ai_progress,
            "EvaluatorScore": evaluator_score,
            "Discrepancy": self._discrepancy(ai_progress, evaluator_score),
            "ConfidenceLevel": ai.get("ConfidenceLevel", "Indeterminate"),
            "EvidenceSummary": ai.get("ExecutiveSummary"),
            "StructuralEvidence": ai.get("StructuralEvidence"),
            "OperationalEvidence": ai.get("OperationalEvidence"),
            "OutcomeEvidence": ai.get("OutcomeEvidence"),
            "PerceptionEvidence": ai.get("PerceptionEvidence"),
            "TemporalScope": ai.get("TemporalScope"),
            "DistortionScreening": ai.get("DistortionScreening"),
            "GeopoliticalShock": ai.get("GeopoliticalShock"),
            "FinanceShock": ai.get("FinanceShock"),
            "LegitimacyShock": ai.get("LegitimacyShock"),
            "OverallStressResilience": ai.get("OverallStressResilience"),
            "StressScoreAdjustment": ai.get("StressScoreAdjustment"),
            "InclusionEquityAdjustment": ai.get("InclusionEquityAdjustment"),
            "OpacityRisk": ai.get("OpacityRisk"),
            "NonCompensationNote": ai.get("NonCompensationNote"),
            "CrossPillarPatterns": ai.get("CrossPillarPatterns"),
            "RelationalIntegrity": ai.get("RelationalIntegrity"),
            "InstitutionalCapacity": ai.get("InstitutionalCapacity"),
            "EquityAssessment": ai.get("EquityAssessment"),
            "GovernanceTrajectory": ai.get("GovernanceTrajectory"),
            "StrategicRecommendation": ai.get("StrategicRecommendation"),
            "AssessmentValueNote": ai.get("AssessmentValueNote"),
            "PrimarySource": ai.get("PrimarySource"),
            "VerifiedBy": None,
        }

    def _build_source_records(self, row: Any, ai: dict) -> list[dict]:
        """Expand the Sources list from a pillar AI response into flat DB records."""
        return [
            {
                "ClimateProgramID": row.ClimateProgramID,
                "PillarID": row.PillarID,
                "DataYear": self._to_int(src.get("data_year")),
                "SourceType": src.get("source_type"),
                "SourceName": src.get("source_name"),
                "SourceURL": src.get("source_url"),
                "DataExtract": src.get("data_extract"),
                "TrustLevel": self._to_int(src.get("source_trust_level")),
            }
            for src in ai.get("Sources", [])
        ]


    def _build_immediateSituation_record(self, climateProgramID: int, ai: dict) -> dict:
        summary = ai.get("executive_summary", "")

        return {
            "ClimateProgramID": climateProgramID,
            "immediateSituationSummary": ai.get("immediateSituationSummary", "Indeterminate"),
            "key_developments": ai.get("key_developments", "Indeterminate"),
            "critical_risks": ai.get("critical_risks"),
            "gaps": ai.get("gaps"),
            "executive_summary": summary if isinstance(summary, str) and len(summary) > 50 else ""
        }

    # ------------------------------------------------------------------ #
    #  Batch flush helpers                                               #
    # ------------------------------------------------------------------ #

    async def _flushQuestion(
        self,
        programID:int,
        batch: list[dict],
        upsert_fn,
        *,
        force: bool = False,
    ) -> list[dict]:
        """
        Upsert *batch* when it reaches _BATCH_SIZE (or when force=True).
        Returns an empty list after flushing, or the original list if not yet full.
        """
        if batch and (force or len(batch) >= _BATCH_SIZE):
            await upsert_fn(batch,programID)
            return []
        return batch
    
    async def _flush(
        self,
        batch: list[dict],
        upsert_fn,
        *,
        force: bool = False,
    ) -> list[dict]:
        """
        Upsert *batch* when it reaches _BATCH_SIZE (or when force=True).
        Returns an empty list after flushing, or the original list if not yet full.
        """
        if batch and (force or len(batch) >= _BATCH_SIZE):
            await upsert_fn(batch)
            return []
        return batch

    async def _flush_pillar(
        self,
        pillar_batch: list[dict],
        source_batch: list[dict],
        *,
        force: bool = False,
    ) -> tuple[list[dict], list[dict]]:
        """Paired flush for pillar records + their source records."""
        if pillar_batch and (force or len(pillar_batch) >= _BATCH_SIZE):
            await self._db.bulk_upsert_pillar_evaluations(pillar_batch, source_batch)
            return [], []
        return pillar_batch, source_batch

    # ------------------------------------------------------------------ #
    #  Utility                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _safe_normalized(value) -> float:
        """Return 0.0 if NormalizedValue is None or NaN, otherwise the value."""
        if value is None:
            return 0.0
        if isinstance(value, float) and math.isnan(value):
            return 0.0
        return float(value)


# Module-level singleton
score_analyzer_service = ScoreAnalyzerService()
