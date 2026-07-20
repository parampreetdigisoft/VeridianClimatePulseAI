"""
Score analysis Router - API endpoints with database exception logging
Fire-and-forget pattern for long-running analysis tasks
"""

import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.view_models.MissingPillarQuestionRequest import MissingPillarQuestionRequest
from app.view_models.AnalysisRequest import AnalysisResponse
from app.services.score_analyzer_service import score_analyzer_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/programs-score-analysis", tags=["Score Analysis"])


# Background task wrapper with error handling
async def run_analysis_task(task_name: str, coro):
    """
    Wrapper to run analysis tasks in background with proper error handling
    """
    try:
        await coro

    except Exception as e:
        error_msg = f"Background task '{task_name}' failed: {str(e)}"
        logger.error(error_msg, exc_info=True)


@router.post("/analyze/full", response_model=AnalysisResponse)
async def analyze_all_countries_full():
    """
    Analyze table data and provide global summary for the assessment result for all programs
    Returns immediately while analysis runs in background
    """
    try:
        # Start analysis in background
        asyncio.create_task(
            run_analysis_task(
                "analyze_all_countries_full",
                score_analyzer_service.analyze_all_countries(),
            )
        )

        return AnalysisResponse(
            success=True,
            message="Program analysis started successfully. Processing in background.",
        )

    except Exception as e:
        error_msg = f"Error starting program analysis: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/missing-pillar-questions",response_model=AnalysisResponse)
async def analyze_missing_pillar_questions(request: MissingPillarQuestionRequest):
    """
    Analyze only missing AI pillar question evaluations
    for a program and optional pillar.
    Runs in background.
    """

    try:

        asyncio.create_task(
            run_analysis_task(
                f"analyze_missing_pillar_questions_{request.programID}",
                score_analyzer_service.import_missing_program_questions(
                    program_id=request.programID,
                    pillar_id=request.pillarID
                )
            )
        )

        return AnalysisResponse(
            success=True,
            message=(
                "Missing pillar question analysis started "
                "successfully in background."
            ),
        )

    except HTTPException:
        raise

    except Exception as e:
        error_msg = (
            f"Error starting missing pillar question analysis: {str(e)}"
        )

        logger.error(error_msg, exc_info=True)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@router.post("/analyze/{program_id}/full", response_model=AnalysisResponse)
async def analyze_single_program_full(program_id: int):
    """
    Analyze table data and provide global summary for a single Program
    Returns immediately while analysis runs in background
    """
    try:
        if not program_id:
            raise HTTPException(status_code=400, detail="Program ID is required")

        # Start analysis in background
        asyncio.create_task(
            run_analysis_task(
                f"analyze_single_program_full_{program_id}",
                score_analyzer_service.analyze_all_countries(program_id),
            )
        )

        return AnalysisResponse(
            success=True,
            message=f"Program {program_id} analysis started successfully. Processing in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = (
            f"Error starting single program analysis (ID: {program_id}): {str(e)}"
        )
        logger.error(error_msg, exc_info=True)

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{program_id}", response_model=AnalysisResponse)
async def analyze_single_program(program_id: int):
    """
    Analyze only the program summary (no pillars/questions)
    Returns immediately while analysis runs in background
    """
    try:
        if not program_id:
            raise HTTPException(status_code=400, detail="Program ID is required")

        # Start analysis in background
        asyncio.create_task(
            run_analysis_task(
                f"analyze_single_program_{program_id}",
                score_analyzer_service.analyze_single_program(program_id),
            )
        )

        return AnalysisResponse(
            success=True,
            message=f"Program {program_id} analysis started successfully. Processing in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = (
            f"Error starting single program analysis (ID: {program_id}): {str(e)}"
        )
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{program_id}/pillars", response_model=AnalysisResponse)
async def analyze_program_pillars(program_id: int):
    """
    Analyze pillars for a specific program
    Returns immediately while analysis runs in background
    """
    try:
        if not program_id:
            raise HTTPException(status_code=400, detail="Program ID is required")

        # Start analysis in background
        asyncio.create_task(
            run_analysis_task(
                f"analyze_program_pillars_{program_id}",
                score_analyzer_service.analyze_program_pillars(program_id),
            )
        )

        return AnalysisResponse(
            success=True,
            message=f"Program {program_id} pillar analysis started successfully. Processing in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error starting pillar analysis (ID: {program_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{program_id}/questions", response_model=AnalysisResponse)
async def analyze_questions_of_program(program_id: int):
    """
    Analyze all questions for all pillars of a program
    Returns immediately while analysis runs in background
    """
    try:
        if not program_id:
            raise HTTPException(status_code=400, detail="Program ID is required")

        # Start analysis in background
        asyncio.create_task(
            run_analysis_task(
                f"analyze_questions_of_program_{program_id}",
                score_analyzer_service.analyze_program_questions(program_id),
            )
        )

        return AnalysisResponse(
            success=True,
            message=f"Program {program_id} questions analysis started successfully. Processing in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error starting questions analysis (ID: {program_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/analyze/{program_id}/pillars/{pillar_id}/questions",
    response_model=AnalysisResponse,
)
async def analyze_questions_of_program_pillar(program_id: int, pillar_id: int):
    """
    Analyze all questions of a particular pillar for a program
    Returns immediately while analysis runs in background
    """
    try:
        if not program_id:
            raise HTTPException(status_code=400, detail="Program ID is required")

        # Start analysis in background
        asyncio.create_task(
            run_analysis_task(
                f"analyze_questions_program_{program_id}_pillar_{pillar_id}",
                score_analyzer_service.analyze_program_questions(
                    program_id, pillar_id
                ),
            )
        )

        return AnalysisResponse(
            success=True,
            message=f"Program {program_id} pillar {pillar_id} questions analysis started successfully. Processing in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error starting pillar questions analysis (Program: {program_id}, Pillar: {pillar_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{program_id}/single-pillar/{pillar_id}", response_model=AnalysisResponse)
async def analyze_single_pillar(program_id: int, pillar_id: int):
    """
    Analyze single pillar for a program
    Returns immediately while analysis runs in background
    """
    try:
        if not program_id and not pillar_id:
            raise HTTPException(status_code=400, detail="provide required parameter")

        # Start analysis in background
        asyncio.create_task(
            run_analysis_task(
                f"analyze single program{program_id}_pillar_{pillar_id}",
                score_analyzer_service.analyze_program_pillars(program_id, pillar_id),
            )
        )

        return AnalysisResponse(
            success=True,
            message=f"Program {program_id} pillar {pillar_id} analysis started successfully. Processing in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error starting pillar analysis (Program: {program_id}, Pillar: {pillar_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/{program_id}/immediateSituation", response_model=AnalysisResponse)
async def analyze_immediateSituation(program_id: int):
    """
    Analyze single pillar for a program
    Returns immediately while analysis runs in background
    """
    try:
        if not program_id:
            raise HTTPException(status_code=400, detail="provide required parameter")

        # Start analysis in background
        asyncio.create_task(
            run_analysis_task(
                f"analyze single program{program_id}",
                score_analyzer_service.immediateSituation(program_id),
            )
        )

        return AnalysisResponse(
            success=True,
            message=f"Program {program_id} analysis started successfully. Processing in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error starting pillar analysis (Program: {program_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
