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

# ============================================================================
# ADMIN - Güncel içerik populate (scheduled kullanım için)
# ============================================================================

@router.post("/admin/embedding/populate-recent")
def populate_recent_content(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    days: int = Query(1, ge=1, le=14, description="Kaç gün geriden başlasın (UTC)"),
    pages: int = Query(3, ge=1, le=20, description="TMDB discover sayfa sayısı"),
    use_details: bool = Query(False, description="Detay çekerek daha zengin embedding"),
    db: Session = Depends(get_db)
):
    """Son X günde eklenen/başlayan içerikleri FAISS indeksine ekle.

    Not: Rate limit güvenliği için pages üst limiti konservatif tutuldu.
    Cron/scheduled çağrılar için uygundur.
    """
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.populate_recent_content(
            content_type=content_type,
            days=days,
            pages=pages,
            use_details=use_details
        )
        if result.get("success"):
            return result
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "populate_recent_content failed")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error populating recent content: {str(e)}"
        )

@router.post("/admin/embedding/bulk-popular")
def bulk_populate_popular(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    start_page: int = Query(1, ge=1, le=500, description="Başlangıç sayfası"),
    end_page: int = Query(100, ge=1, le=500, description="Bitiş sayfası"),
    use_details: bool = Query(False, description="Detay çekerek daha zengin embedding"),
    db: Session = Depends(get_db)
):
    """'Popular' akışını sayfa aralığı ile toplu populate eder."""
    try:
        if end_page < start_page:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_page start_page'den küçük olamaz")
        recommendation_service = RecommendationService(db)
        result = recommendation_service.bulk_populate_popular(
            content_type=content_type,
            start_page=start_page,
            end_page=end_page,
            use_details=use_details
        )
        if result.get("success"):
            return result
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "bulk_populate_popular failed")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in bulk_popular: {str(e)}"
        )

@router.post("/admin/embedding/bulk-year")
def bulk_populate_by_year(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    year: int = Query(2020, ge=1900, le=2100, description="Yıl"),
    pages: int = Query(100, ge=1, le=500, description="Sayfa sayısı"),
    use_details: bool = Query(False, description="Detay çekerek daha zengin embedding"),
    db: Session = Depends(get_db)
):
    """Belirli yıl için discover ile toplu populate eder."""
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.bulk_populate_by_year(
            content_type=content_type,
            year=year,
            pages=pages,
            use_details=use_details
        )
        if result.get("success"):
            return result
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "bulk_populate_by_year failed")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in bulk_year: {str(e)}"
        )

@router.post("/admin/embedding/bulk-popular/continue")
def continue_bulk_popular(
    content_type: str = Query("movie", description="İçerik türü: 'movie' veya 'tv'"),
    batch_pages: int = Query(25, ge=1, le=100, description="Bugün işlenecek sayfa sayısı"),
    use_details: bool = Query(False, description="Detay çekerek daha zengin embedding"),
    db: Session = Depends(get_db)
):
    """Dün kaldığı sayfadan itibaren 'popular' ingest'e devam eder (Redis ile)."""
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.continue_bulk_popular(
            content_type=content_type,
            batch_pages=batch_pages,
            use_details=use_details
        )
        if result.get("success"):
            return result
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "continue_bulk_popular failed")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in continue_bulk_popular: {str(e)}"
        )
@router.post("/current-emotion")
def get_current_emotion_recommendations(
    payload: EmotionBasedRecommendation,
    page: int = Query(1, ge=1, le=5, description="Page number (1-5)"),
    db: Session = Depends(get_db)
):
    """
    Kullanıcının anlık duygu durumuna göre öneriler
    - %100 anlık duygu odaklı
    - Geçmiş verileri kullanmaz
    """
    try:
        recommendation_service = RecommendationService(db)
        result = recommendation_service.get_emotion_based_recommendations_public(
            emotion_text=payload.emotion,
            content_type=payload.content_type,
            page=page
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to get recommendations")
            )
    except Exception as e:
        raise handle_exception(e)

@router.post("/hybrid")
def get_hybrid_recommendations(
    request: HybridRecommendationRequest,
    page: int = Query(1, ge=1, le=5, description="Page number (1-5)"),
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
        # Servise page bilgisini iletmek için geçici alan set ediliyor
        recommendation_service._page = page
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
    pages: int = Query(5, ge=1, le=500, description="Doldurulacak sayfa sayısı"),
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
    pages: int = Query(3, ge=1, le=100, description="Doldurulacak sayfa sayısı (detaylı daha uzun sürer)"),
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

# Öneri sonrası bildirim endpointleri kaldırıldı