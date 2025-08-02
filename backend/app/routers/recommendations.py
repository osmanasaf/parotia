from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.db import get_db
from app.core.auth import get_current_user
from app.core.exceptions import BaseAppException
from app.services.recommendation_service import RecommendationService
from app.schemas.movie import (
    EmotionBasedRecommendation, HistoryBasedRecommendation, HybridRecommendation, HybridRecommendationRequest
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

def handle_exception(e: Exception) -> HTTPException:
    """Handle exceptions and convert to HTTPException"""
    if isinstance(e, BaseAppException):
        return HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

# ============================================================================
# KULLANICI ÖNERİ ENDPOINT'LERİ
# ============================================================================

@router.post("/history")
def get_history_based_recommendations(
    history_data: HistoryBasedRecommendation,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Kullanıcının izleme geçmişine göre öneriler
    - Kullanıcının rate ettiği filmlerin benzerlerini önerir
    - %100 geçmiş odaklı
    """
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.get_history_based_recommendations(current_user_id, history_data)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.post("/current-emotion")
def get_current_emotion_recommendations(
    emotion_text: str = Query(..., description="Kullanıcının anlık duygu durumu"),
    content_type: str = Query("movie", description="İçerik türü: 'movie', 'tv', 'all'"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Kullanıcının anlık duygu durumuna göre öneriler
    - %100 anlık duygu odaklı
    - Geçmiş verileri kullanmaz
    """
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.get_emotion_based_recommendations(
            current_user_id, 
            EmotionBasedRecommendation(
                emotion=emotion_text,
                content_type=content_type,
                page=1
            )
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.post("/hybrid")
def get_hybrid_recommendations(
    request: HybridRecommendationRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Hibrit öneriler: %70-80 duygu durumu + %20-30 izleme geçmişi
    - Kullanıcının anlık duygu durumu ve geçmişini birleştirir
    - En dengeli öneri sistemi
    """
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.get_hybrid_recommendations(
            current_user_id, 
            request.emotion_text, 
            request.content_type
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.post("/profile-based")
def get_profile_based_recommendations(
    content_type: str = Query("movie", description="İçerik türü: 'movie', 'tv', 'all'"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Kullanıcının emotion profile'ına göre öneriler
    - Emotion text gerektirmez
    - Kullanıcının geçmiş duygu analizlerini kullanır
    - %100 profile odaklı
    """
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.get_profile_based_recommendations(
            current_user_id, 
            content_type
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

# ============================================================================
# KULLANICI GEÇMİŞ ENDPOINT'İ
# ============================================================================

@router.get("/my/history")
def get_my_recommendation_history(
    recommendation_type: Optional[str] = Query(None, description="Öneri türüne göre filtrele"),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının öneri geçmişini getir"""
    try:
        recommendation_service = RecommendationService(db)
        history = recommendation_service.get_user_recommendation_history(current_user_id, recommendation_type)
        return {"success": True, "data": history}
    except Exception as e:
        raise handle_exception(e)

# ============================================================================
# ADMIN ENDPOINT'LERİ (Sistem Yönetimi)
# ============================================================================

@router.post("/admin/embedding/populate")
def populate_embedding_index(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    pages: int = Query(5, ge=1, le=20, description="Doldurulacak sayfa sayısı"),
    db: Session = Depends(get_db)
):
    """Embedding index'ini popüler içerikle doldur (Admin)"""
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.populate_embedding_index(content_type, pages)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.post("/admin/embedding/populate-detailed")
def populate_embedding_index_detailed(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    pages: int = Query(3, ge=1, le=10, description="Doldurulacak sayfa sayısı (detaylı daha uzun sürer)"),
    db: Session = Depends(get_db)
):
    """Embedding index'ini detaylı içerik bilgileriyle doldur (Admin)"""
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.populate_embedding_index_with_details(content_type, pages)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.post("/admin/embedding/populate-genre")
def populate_embedding_index_by_genre(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    genre_id: int = Query(None, description="TMDB genre ID (opsiyonel)"),
    pages: int = Query(3, ge=1, le=10, description="Doldurulacak sayfa sayısı"),
    db: Session = Depends(get_db)
):
    """Belirli genre'dan embedding index'ini doldur (Admin)"""
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.populate_embedding_index_by_genre(content_type, genre_id, pages)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise handle_exception(e)

@router.get("/admin/embedding/stats")
def get_embedding_stats(
    db: Session = Depends(get_db)
):
    """Embedding index istatistiklerini getir (Admin)"""
    try:
        recommendation_service = RecommendationService(db)
        stats = recommendation_service.get_embedding_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        raise handle_exception(e)

@router.get("/admin/embedding/content-list")
def get_embedding_content_list(
    content_type: Optional[str] = Query(None, description="İçerik türüne göre filtrele: 'movie' veya 'tv'"),
    limit: int = Query(20, ge=1, le=100, description="Döndürülecek öğe sayısı"),
    offset: int = Query(0, ge=0, description="Sayfalama için offset"),
    db: Session = Depends(get_db)
):
    """Embedding index'indeki içerik listesini getir (Admin)"""
    try:
        recommendation_service = RecommendationService(db)
        content_list = recommendation_service.get_embedding_content_list(content_type, limit, offset)
        return {"success": True, "data": content_list}
    except Exception as e:
        raise handle_exception(e)

# ============================================================================
# TEST ENDPOINT'LERİ (Geliştirme)
# ============================================================================

@router.post("/test/embedding")
def test_embedding(
    text: str = Query(..., description="Embedding'e çevrilecek metin"),
    db: Session = Depends(get_db)
):
    """Metni embedding'e çevir (Test)"""
    try:
        recommendation_service = RecommendationService(db)
        embedding = recommendation_service.test_embedding(text)
        return {
            "success": True,
            "data": {
                "text": text,
                "embedding_dimension": len(embedding),
                "embedding_sample": embedding[:10].tolist() if len(embedding) > 10 else embedding.tolist()
            }
        }
    except Exception as e:
        raise handle_exception(e)

class EmbeddingTestRequest(BaseModel):
    """Test embedding request"""
    text: str = Field(..., description="Embedding'e çevrilecek metin")

@router.post("/test/embedding-body")
def test_embedding_body(
    request: EmbeddingTestRequest,
    db: Session = Depends(get_db)
):
    """Metni embedding'e çevir (Request body ile) (Test)"""
    try:
        recommendation_service = RecommendationService(db)
        embedding = recommendation_service.test_embedding(request.text)
        return {
            "success": True,
            "data": {
                "text": request.text,
                "embedding_dimension": len(embedding),
                "embedding_sample": embedding[:10].tolist() if len(embedding) > 10 else embedding.tolist()
            }
        }
    except Exception as e:
        raise handle_exception(e) 

@router.get("/tracking/stats")
async def get_recommendation_tracking_stats(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get recommendation tracking statistics"""
    try:
        recommendation_service = RecommendationService(db)
        stats = recommendation_service.get_recommendation_tracking_stats(current_user_id)
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting tracking stats: {str(e)}"
        )

@router.post("/{tmdb_id}/add-to-watchlist")
async def add_recommendation_to_watchlist(
    tmdb_id: int,
    content_type: str = "movie",
    recommendation_id: Optional[int] = None,
    recommendation_type: Optional[str] = None,
    recommendation_score: Optional[float] = None,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Add a recommended content to watchlist with tracking"""
    try:
        recommendation_service = RecommendationService(db)
        success = recommendation_service.add_recommendation_to_watchlist(
            user_id=current_user_id,
            tmdb_id=tmdb_id,
            content_type=content_type,
            recommendation_id=recommendation_id,
            recommendation_type=recommendation_type,
            recommendation_score=recommendation_score
        )
        
        if success:
            return {
                "success": True,
                "message": f"Film watchlist'e eklendi ve recommendation tracking aktif",
                "data": {
                    "tmdb_id": tmdb_id,
                    "content_type": content_type,
                    "recommendation_type": recommendation_type,
                    "recommendation_score": recommendation_score
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Film watchlist'e eklenemedi"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding to watchlist: {str(e)}"
        ) 

@router.post("/select")
async def select_recommendation(
    selection_data: dict,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """User selects a recommendation from the list"""
    try:
        from app.services.recommendation_selection_service import RecommendationSelectionService
        
        selection_service = RecommendationSelectionService(db)
        
        result = selection_service.select_recommendation(
            user_id=current_user_id,
            tmdb_id=selection_data["tmdb_id"],
            content_type=selection_data.get("content_type", "movie"),
            recommendation_type=selection_data["recommendation_type"],
            source=selection_data["source"],
            recommendation_score=selection_data.get("recommendation_score"),
            selected_rank=selection_data.get("selected_rank")
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error selecting recommendation: {str(e)}"
        )

@router.get("/selections")
async def get_user_selections(
    limit: int = 20,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get user's recommendation selections"""
    try:
        from app.services.recommendation_selection_service import RecommendationSelectionService
        
        selection_service = RecommendationSelectionService(db)
        selections = selection_service.get_user_selections(current_user_id, limit)
        
        return {
            "success": True,
            "data": {
                "selections": [
                    {
                        "id": s.id,
                        "tmdb_id": s.tmdb_id,
                        "content_type": s.content_type,
                        "recommendation_type": s.recommendation_type,
                        "source": s.source,
                        "recommendation_score": s.recommendation_score,
                        "selected_rank": s.selected_rank,
                        "watched": s.watched,
                        "feedback_provided": s.feedback_provided,
                        "created_at": s.created_at.isoformat() if s.created_at else None
                    }
                    for s in selections
                ],
                "count": len(selections)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting selections: {str(e)}"
        )

@router.get("/selections/stats")
async def get_selection_stats(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get statistics about user's recommendation selections"""
    try:
        from app.services.recommendation_selection_service import RecommendationSelectionService
        
        selection_service = RecommendationSelectionService(db)
        stats = selection_service.get_selection_stats(current_user_id)
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting selection stats: {str(e)}"
        )

@router.post("/selections/{selection_id}/feedback")
async def provide_selection_feedback(
    selection_id: int,
    feedback_data: dict,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Provide feedback for a recommendation selection"""
    try:
        from app.services.recommendation_selection_service import RecommendationSelectionService
        
        selection_service = RecommendationSelectionService(db)
        success = selection_service.provide_feedback(selection_id, feedback_data)
        
        if success:
            return {
                "success": True,
                "message": "Feedback başarıyla kaydedildi"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback kaydedilemedi"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error providing feedback: {str(e)}"
        ) 

@router.post("/admin/send-notifications")
async def send_pending_notifications(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Admin endpoint to send pending notifications (24 hours after selection)"""
    try:
        from app.services.recommendation_selection_service import RecommendationSelectionService
        
        selection_service = RecommendationSelectionService(db)
        pending_selections = selection_service.get_pending_notifications()
        
        sent_count = 0
        notifications_sent = []
        for selection in pending_selections:
            result = selection_service.send_notification(selection.id)
            if result["success"]:
                sent_count += 1
                notifications_sent.append(result)
        
        return {
            "success": True,
            "message": f"{sent_count} notification gönderildi",
            "data": {
                "pending_count": len(pending_selections),
                "sent_count": sent_count,
                "notifications": notifications_sent
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notifications: {str(e)}"
        ) 

@router.post("/admin/test-notification/{selection_id}")
async def test_notification(
    selection_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Test endpoint - direkt selection ID ile notification gönder"""
    try:
        from app.services.recommendation_selection_service import RecommendationSelectionService
        
        selection_service = RecommendationSelectionService(db)
        result = selection_service.send_notification(selection_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Test notification sent successfully",
                "data": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending test notification: {str(e)}"
        ) 