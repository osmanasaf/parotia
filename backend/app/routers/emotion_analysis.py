from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.core.auth import get_current_user
from app.db import get_db
from app.models.user import User
from app.services.emotion_analysis_service import EmotionAnalysisService
from app.schemas.movie import EmotionInsightsResponse

router = APIRouter(prefix="/emotion", tags=["Emotion Analysis & Feedback"])

@router.post("/analyze")
async def analyze_emotion(
    emotion_text: str,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Analyze user's emotional state from text"""
    try:
        emotion_service = EmotionAnalysisService(db)
        analysis = emotion_service.analyze_user_emotion(emotion_text)
        
        return {
            "success": True,
            "data": {
                "emotion_text": emotion_text,
                "analysis": analysis
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing emotion: {str(e)}"
        )

@router.post("/content-tone/{tmdb_id}")
async def analyze_content_emotional_tone(
    tmdb_id: int,
    content_type: str,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Analyze emotional tone of content"""
    try:
        emotion_service = EmotionAnalysisService(db)
        analysis = emotion_service.analyze_content_emotional_tone(tmdb_id, content_type)
        
        return {
            "success": True,
            "data": {
                "tmdb_id": tmdb_id,
                "content_type": content_type,
                "emotional_analysis": analysis
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing content tone: {str(e)}"
        )

@router.post("/user-watched-content")
async def get_user_emotion_from_watched_content(
    content_type: str = "movie",
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get user's emotional state based on their watched content"""
    try:
        emotion_service = EmotionAnalysisService(db)
        result = emotion_service.get_user_emotion_from_watched_content(
            current_user_id, content_type
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user emotion from watched content: {str(e)}"
        )

@router.post("/profile/update-realtime")
async def update_emotion_profile_realtime(
    tmdb_id: int,
    rating: float,
    content_type: str = "movie",
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update user's emotion profile in real-time when they watch/rate content"""
    try:
        emotion_service = EmotionAnalysisService(db)
        success = emotion_service.update_user_emotion_profile_realtime(
            current_user_id, tmdb_id, rating, content_type
        )
        
        if success:
            return {
                "success": True,
                "message": "Emotion profile updated successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update emotion profile"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating emotion profile: {str(e)}"
        )

@router.get("/profile/cached")
async def get_cached_emotion_profile(
    content_type: str = "movie",
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get cached user emotion profile"""
    try:
        emotion_service = EmotionAnalysisService(db)
        profile = emotion_service.get_cached_user_emotion_profile(current_user_id, content_type)
        
        return {
            "success": True,
            "data": profile
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cached emotion profile: {str(e)}"
        )

@router.post("/feedback")
async def submit_post_viewing_feedback(
    feedback_data: dict,  # PostViewingFeedbackRequest yerine dict kullan
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Submit post-viewing feedback for content"""
    try:
        emotion_service = EmotionAnalysisService(db)
        success = emotion_service.save_post_viewing_feedback(current_user_id, feedback_data)
        
        if success:
            return {
                "success": True,
                "message": "Feedback submitted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit feedback"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting feedback: {str(e)}"
        )

@router.get("/insights")
async def get_emotion_insights(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get user's emotion insights and patterns"""
    try:
        emotion_service = EmotionAnalysisService(db)
        insights = emotion_service.get_user_emotion_insights(current_user_id)
        
        return {
            "success": True,
            "data": insights
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting emotion insights: {str(e)}"
        )

# Öneri sonrası bildirim istatistik endpointi kaldırıldı

@router.post("/profile/update")
async def update_emotion_profile(
    learning_rate: float = 0.1,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update user's emotion profile with new learning rate"""
    try:
        emotion_service = EmotionAnalysisService(db)
        # This would trigger a profile update with the new learning rate
        # Implementation depends on your specific needs
        
        return {
            "success": True,
            "message": "Emotion profile update initiated",
            "learning_rate": learning_rate
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating emotion profile: {str(e)}"
        ) 