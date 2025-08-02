import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import faiss
import pickle
import os
from app.core.config import get_settings
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating and managing content embeddings"""
    
    def __init__(self):
        self.settings = get_settings()
        self.model_name = "all-MiniLM-L6-v2"  # Lightweight but effective model
        self.model = None
        self.index = None
        self.content_data = []
        self.embedding_cache_path = "embeddings_cache.pkl"
        self.index_cache_path = "faiss_index.bin"
        
        self._load_model()
        self._load_or_create_index()
    
    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading embedding model: {str(e)}")
            raise
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create new one"""
        try:
            if os.path.exists(self.index_cache_path) and os.path.exists(self.embedding_cache_path):
                logger.info("Loading existing FAISS index")
                self.index = faiss.read_index(self.index_cache_path)
                with open(self.embedding_cache_path, 'rb') as f:
                    self.content_data = pickle.load(f)
                logger.info(f"Loaded {len(self.content_data)} content items")
            else:
                logger.info("Creating new FAISS index")
                self._create_new_index()
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        try:
            dimension = self.model.get_sentence_embedding_dimension()
            
            # Büyük veri için optimize edilmiş index
            if len(self.content_data) > 100000:  # 100K'dan fazla kayıt varsa
                # IVF index kullan (memory'yi azaltır)
                nlist = min(4096, len(self.content_data) // 100)  # Cluster sayısı
                quantizer = faiss.IndexFlatIP(dimension)
                self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
                logger.info(f"Created optimized FAISS index (IVF) with {nlist} clusters")
            else:
                # Küçük veri için basit index
                self.index = faiss.IndexFlatIP(dimension)
                logger.info(f"Created simple FAISS index with dimension {dimension}")
                
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise
    
    def _save_index(self):
        """Save FAISS index and content data"""
        try:
            faiss.write_index(self.index, self.index_cache_path)
            with open(self.embedding_cache_path, 'wb') as f:
                pickle.dump(self.content_data, f)
            logger.info("Index and content data saved successfully")
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")
    
    def generate_content_text(self, content: Dict[str, Any]) -> str:
        """Generate text representation of content for embedding"""
        content_type = content.get("content_type", "movie")
        
        if content_type == "movie":
            title = content.get("title", "")
            overview = content.get("overview", "")
            genres = ", ".join([genre.get("name", "") for genre in content.get("genres", [])])
            year = content.get("release_date", "")[:4] if content.get("release_date") else ""
            
            # Add additional context if available
            tagline = content.get("tagline", "")
            
            # Combine all text elements
            text_parts = [title, overview, genres, year]
            if tagline:
                text_parts.append(tagline)
            
            text = " ".join([part for part in text_parts if part])
        else:  # TV Show
            name = content.get("name", "")
            overview = content.get("overview", "")
            genres = ", ".join([genre.get("name", "") for genre in content.get("genres", [])])
            year = content.get("first_air_date", "")[:4] if content.get("first_air_date") else ""
            
            # Add TV-specific context
            tagline = content.get("tagline", "")
            keywords = ", ".join([keyword.get("name", "") for keyword in content.get("keywords", {}).get("keywords", [])])
            cast = ", ".join([cast.get("name", "") for cast in content.get("credits", {}).get("cast", [])[:5]])
            network = content.get("networks", [{}])[0].get("name", "") if content.get("networks") else ""
            
            # Combine all text elements
            text_parts = [name, overview, genres, year]
            if tagline:
                text_parts.append(tagline)
            if keywords:
                text_parts.append(keywords)
            if cast:
                text_parts.append(f"Cast: {cast}")
            if network:
                text_parts.append(f"Network: {network}")
            
            text = " ".join(text_parts)
        
        return text.strip()
    
    def add_content_with_details(self, content: Dict[str, Any], db: Session = None) -> bool:
        """Add content with full details and generate embedding"""
        try:
            # Filter out low-rated content (IMDB 6.0 altı)
            vote_average = content.get('vote_average', 0)
            if vote_average < 6.0:
                logger.info(f"Skipping low-rated content {content.get('tmdb_id')} (vote_average: {vote_average})")
                return False
            
            # Generate text representation
            text = self.generate_content_text(content)
            if not text:
                logger.warning(f"Could not generate text for content {content.get('tmdb_id')}")
                return False
            
            # Generate embedding
            embedding = self.model.encode([text])[0]
            
            # Normalize embedding for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)
            
            # Store embedding vector in content data
            content["embedding_vector"] = embedding
            
            # Add to FAISS index
            self.index.add(embedding.reshape(1, -1))
            
            # Store content data
            self.content_data.append(content)
            
            # Also save to database if db session provided
            if db:
                self._save_content_to_db(content, embedding, db)
            
            logger.info(f"Added content {content.get('tmdb_id')} ({content.get('content_type')}) to embedding index")
            return True
            
        except Exception as e:
            logger.error(f"Error adding content with details: {str(e)}")
            return False
    
    def _save_content_to_db(self, content: Dict[str, Any], embedding: np.ndarray, db: Session) -> bool:
        """Save content embedding to database"""
        try:
            from app.models.content_embeddings import ContentEmbedding
            
            # Filter out low-rated content (IMDB 6.0 altı)
            vote_average = content.get('vote_average', 0)
            if vote_average < 6.0:
                logger.info(f"Skipping low-rated content {content.get('tmdb_id')} from database (vote_average: {vote_average})")
                return False
            
            # Check if already exists
            existing = db.query(ContentEmbedding).filter(
                ContentEmbedding.tmdb_id == content.get('tmdb_id'),
                ContentEmbedding.content_type == content.get('content_type')
            ).first()
            
            if existing:
                # Update existing record
                existing.title = content.get('title') or content.get('name', '')
                existing.overview = content.get('overview', '')
                existing.genres = [genre.get('name') for genre in content.get('genres', [])]
                existing.release_date = content.get('release_date') or content.get('first_air_date', '')
                existing.poster_path = content.get('poster_path', '')
                existing.vote_average = content.get('vote_average', 0.0)
                existing.vote_count = content.get('vote_count', 0)
                existing.embedding_vector = embedding.tolist()
                existing.popularity = content.get('popularity', 0.0)
                existing.original_language = content.get('original_language', '')
                existing.original_title = content.get('original_title') or content.get('original_name', '')
            else:
                # Create new record
                db_content = ContentEmbedding(
                    tmdb_id=content.get('tmdb_id'),
                    content_type=content.get('content_type'),
                    title=content.get('title') or content.get('name', ''),
                    overview=content.get('overview', ''),
                    genres=[genre.get('name') for genre in content.get('genres', [])],
                    release_date=content.get('release_date') or content.get('first_air_date', ''),
                    poster_path=content.get('poster_path', ''),
                    vote_average=content.get('vote_average', 0.0),
                    vote_count=content.get('vote_count', 0),
                    embedding_vector=embedding.tolist(),
                    popularity=content.get('popularity', 0.0),
                    original_language=content.get('original_language', ''),
                    original_title=content.get('original_title') or content.get('original_name', '')
                )
                db.add(db_content)
            
            db.commit()
            logger.info(f"Saved content {content.get('tmdb_id')} to database")
            return True
            
        except Exception as e:
            logger.error(f"Error saving content to database: {str(e)}")
            db.rollback()
            return False
    
    def add_content(self, content: Dict[str, Any]) -> bool:
        """Add content to the embedding index (legacy method)"""
        return self.add_content_with_details(content)
    
    def search_similar_content(self, query_text: str = "", top_k: int = 10, content_type: Optional[str] = None, user_embedding: Optional[np.ndarray] = None, query_embedding: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
        """Search for similar content based on text query, user embedding, or direct query embedding"""
        try:
            # Check if index is empty
            if self.index.ntotal == 0:
                logger.warning("Embedding index is empty")
                return []
            
            # Use query_embedding if provided, otherwise user_embedding, otherwise generate from query text
            if query_embedding is not None:
                search_embedding = query_embedding
            elif user_embedding is not None:
                search_embedding = user_embedding
            elif query_text:
                # Generate embedding for query
                search_embedding = self.model.encode([query_text])[0]
            else:
                logger.error("No query text, user embedding, or query embedding provided")
                return []
            
            # Normalize the search embedding for cosine similarity
            search_embedding = search_embedding / np.linalg.norm(search_embedding)
            
            # Search in FAISS index
            scores, indices = self.index.search(search_embedding.reshape(1, -1), top_k * 2)  # Get more results for filtering
            
            # Prepare results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.content_data):
                    content = self.content_data[idx].copy()
                    
                    # Filter by content type if specified
                    if content_type and content["content_type"] != content_type:
                        continue
                    
                    # Ensure tmdb_id exists (map from 'id' if needed)
                    if "tmdb_id" not in content and "id" in content:
                        content["tmdb_id"] = content["id"]
                    
                    # Convert FAISS score to cosine similarity (0-1 range)
                    # FAISS returns inner product, we need to convert to cosine similarity
                    cosine_similarity = float(score)  # Already normalized embeddings
                    
                    content["similarity_score"] = cosine_similarity
                    content["rank"] = len(results) + 1
                    results.append(content)
                    
                    # Stop if we have enough results
                    if len(results) >= top_k:
                        break
            
            logger.info(f"Found {len(results)} similar content items for query")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar content: {str(e)}")
            return []
    
    def get_user_preference_embedding(self, user_ratings: List[Dict[str, Any]]) -> Optional[np.ndarray]:
        """Generate embedding based on user's rated content"""
        try:
            if not user_ratings:
                return None
            
            # Get embeddings for rated content
            embeddings = []
            weights = []
            
            for rating in user_ratings:
                tmdb_id = rating.get("tmdb_id")
                content_type = rating.get("content_type", "movie")
                
                # Get content embedding
                content_embedding = self.get_content_embedding(tmdb_id, content_type)
                if content_embedding is not None:
                    embeddings.append(content_embedding)
                    # Weight by rating (higher rating = higher weight)
                    weight = rating.get("rating", 5) / 10.0
                    weights.append(weight)
            
            if not embeddings:
                return None
            
            # Calculate weighted average
            weights = np.array(weights)
            weights = weights / weights.sum()  # Normalize weights
            
            weighted_embedding = np.average(embeddings, axis=0, weights=weights)
            
            # Normalize the final embedding
            weighted_embedding = weighted_embedding / np.linalg.norm(weighted_embedding)
            
            logger.info(f"Generated user preference embedding from {len(embeddings)} rated items")
            return weighted_embedding
            
        except Exception as e:
            logger.error(f"Error generating user preference embedding: {str(e)}")
            return None
    
    def get_hybrid_recommendations(self, 
                                 emotion_text: str, 
                                 user_ratings: List[Dict[str, Any]], 
                                 top_k: int = 10,
                                 emotion_weight: float = 0.7,
                                 content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get hybrid recommendations based on emotion and user history"""
        try:
            # Check if index is empty
            if self.index.ntotal == 0:
                logger.warning("Embedding index is empty")
                return []
            
            # Generate emotion embedding
            emotion_embedding = self.model.encode([emotion_text])[0]
            
            # Generate user preference embedding
            user_embedding = self.get_user_preference_embedding(user_ratings)
            
            if user_embedding is None:
                # If no user history, use only emotion
                final_embedding = emotion_embedding
            else:
                # Combine emotion and user preference embeddings
                final_embedding = (emotion_weight * emotion_embedding + 
                                 (1 - emotion_weight) * user_embedding)
            
            # Search for similar content
            scores, indices = self.index.search(final_embedding.reshape(1, -1), top_k * 2)  # Get more results for filtering
            
            # Prepare results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.content_data):
                    content = self.content_data[idx].copy()
                    
                    # Filter by content type if specified
                    if content_type and content["content_type"] != content_type:
                        continue
                    
                    content["similarity_score"] = float(score)
                    content["rank"] = len(results) + 1
                    content["recommendation_type"] = "hybrid"
                    results.append(content)
                    
                    # Stop if we have enough results
                    if len(results) >= top_k:
                        break
            
            logger.info(f"Generated {len(results)} hybrid recommendations")
            return results
            
        except Exception as e:
            logger.error(f"Error generating hybrid recommendations: {str(e)}")
            return []
    
    def save_index(self):
        """Save the current index and content data"""
        self._save_index()
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the embedding index"""
        try:
            total_items = self.index.ntotal if self.index else 0
            movie_count = sum(1 for item in self.content_data if item.get("content_type") == "movie")
            tv_count = sum(1 for item in self.content_data if item.get("content_type") == "tv")
            
            return {
                "total_items": total_items,
                "movie_count": movie_count,
                "tv_count": tv_count,
                "index_dimension": self.index.d if self.index else 0,
                "model_name": self.model_name
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {"error": str(e)}
    
    def get_content_list(self, content_type: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of content in embedding index"""
        try:
            filtered_data = self.content_data
            
            if content_type:
                filtered_data = [item for item in filtered_data if item.get("content_type") == content_type]
            
            # Apply pagination
            start_idx = offset
            end_idx = start_idx + limit
            paginated_data = filtered_data[start_idx:end_idx]
            
            # Format the data for display
            formatted_data = []
            for item in paginated_data:
                formatted_item = {
                    "tmdb_id": item.get("tmdb_id"),
                    "content_type": item.get("content_type"),
                    "title": item.get("title") or item.get("name"),
                    "overview": item.get("overview", "")[:100] + "..." if item.get("overview") else "",
                    "genres": [genre.get("name", "") for genre in item.get("genres", [])],
                    "release_date": item.get("release_date") or item.get("first_air_date"),
                    "vote_average": item.get("vote_average"),
                    "popularity": item.get("popularity")
                }
                formatted_data.append(formatted_item)
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Error getting content list: {str(e)}")
            return []
    
    def test_embedding(self, text: str) -> np.ndarray:
        """Test method to generate embedding for a text"""
        try:
            embedding = self.model.encode([text])[0]
            return embedding
        except Exception as e:
            logger.error(f"Error generating test embedding: {str(e)}")
            raise
    
    def encode_text(self, text: str) -> np.ndarray:
        """Encode text to embedding vector"""
        try:
            embedding = self.model.encode([text])[0]
            return embedding
        except Exception as e:
            logger.error(f"Error encoding text: {str(e)}")
            return np.array([])
    
    def get_content_embedding(self, tmdb_id: int, content_type: str) -> Optional[np.ndarray]:
        """Get embedding for specific content by tmdb_id and content_type"""
        try:
            # Find content in our data
            for item in self.content_data:
                if item.get("tmdb_id") == tmdb_id and item.get("content_type") == content_type:
                    return item.get("embedding_vector")
            
            # If not found in cache, try to generate from TMDB data
            logger.info(f"Content {tmdb_id} ({content_type}) not found in cache, attempting to generate embedding")
            
            # Get content data from TMDB
            from app.core.tmdb_service import TMDBServiceFactory
            tmdb_service = TMDBServiceFactory.create_service()
            
            if content_type == "movie":
                # Get basic movie details
                content_data = tmdb_service.get_movie_details(tmdb_id)
                if content_data:
                    # Get additional details
                    try:
                        credits = tmdb_service.movie_service.get_movie_credits(tmdb_id)
                        if credits and hasattr(credits, 'data'):
                            content_data.data['credits'] = credits.data
                    except:
                        pass  # Credits not essential
            elif content_type == "tv":
                content_data = tmdb_service.get_tv_details(tmdb_id)
            else:
                return None
            
            if not content_data:
                logger.warning(f"Could not fetch content data for {tmdb_id} ({content_type})")
                return None
            
            # Convert TMDBResponse to dict and add metadata
            if hasattr(content_data, 'data'):
                content_dict = content_data.data
            else:
                content_dict = content_data.__dict__ if hasattr(content_data, '__dict__') else dict(content_data)
            
            content_dict["content_type"] = content_type
            content_dict["tmdb_id"] = tmdb_id
            text = self.generate_content_text(content_dict)
            
            if not text:
                logger.warning(f"Could not generate text for {tmdb_id} ({content_type})")
                return None
            
            # Generate embedding
            embedding = self.model.encode([text])[0]
            
            # Cache the result
            content_dict["embedding_vector"] = embedding
            self.content_data.append(content_dict)
            
            logger.info(f"Generated and cached embedding for {tmdb_id} ({content_type})")
            return embedding
            
        except Exception as e:
            logger.error(f"Error getting content embedding: {str(e)}")
            return None 

    def update_user_emotional_profile(self, user_id: int, db: Session) -> bool:
        """Update user's emotional profile based on their watched movies"""
        try:
            from app.repositories.user_interaction_repository import UserRatingRepository
            from app.models.user_interaction import UserEmotionalProfile
            
            # Get user's ratings
            rating_repo = UserRatingRepository(db)
            user_ratings = rating_repo.get_user_ratings(user_id, "movie")
            
            if not user_ratings:
                logger.warning(f"No ratings found for user {user_id}")
                return False
            
            # Get or create emotional profile
            profile = db.query(UserEmotionalProfile).filter(
                UserEmotionalProfile.user_id == user_id
            ).first()
            
            if not profile:
                profile = UserEmotionalProfile(user_id=user_id)
                db.add(profile)
            
            # Calculate emotional embedding from watched movies
            embeddings = []
            weights = []
            
            for rating in user_ratings:
                # Get movie embedding (from cache or generate)
                movie_embedding = self.get_content_embedding(rating.tmdb_id, "movie")
                if movie_embedding is not None:
                    embeddings.append(movie_embedding)
                    # Weight by rating (higher rating = higher weight)
                    weights.append(rating.rating / 10.0)
            
            if not embeddings:
                logger.warning(f"No valid embeddings found for user {user_id}")
                return False
            
            # Calculate weighted average emotional embedding
            weights = np.array(weights)
            weights = weights / weights.sum()  # Normalize weights
            
            emotional_embedding = np.average(embeddings, axis=0, weights=weights)
            emotional_embedding = emotional_embedding / np.linalg.norm(emotional_embedding)  # Normalize
            
            # Update profile
            profile.emotional_embedding = [float(x) for x in emotional_embedding.tolist()]
            profile.total_watched_movies = len(user_ratings)
            profile.last_updated = datetime.utcnow()
            profile.profile_confidence = min(1.0, len(user_ratings) / 10.0)  # More movies = higher confidence
            
            # Calculate emotional tendencies from embedding
            profile.emotional_tendencies = self._calculate_emotional_tendencies(emotional_embedding)
            
            db.commit()
            logger.info(f"Updated emotional profile for user {user_id} with {len(user_ratings)} movies")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user emotional profile: {str(e)}")
            db.rollback()
            return False
    
    def _calculate_emotional_tendencies(self, emotional_embedding: np.ndarray) -> Dict[str, float]:
        """Calculate emotional tendencies from user's emotional embedding"""
        try:
            # Define emotional query texts
            emotional_queries = {
                "lonely": "yalnız değersiz terk edilmiş",
                "happy": "mutlu neşeli sevinçli",
                "sad": "üzgün hüzünlü kederli",
                "excited": "heyecanlı enerjik coşkulu",
                "calm": "sakin huzurlu rahat",
                "angry": "kızgın öfkeli sinirli",
                "anxious": "endişeli kaygılı stresli",
                "romantic": "romantik aşık tutkulu",
                "inspired": "ilham verici motivasyonlu cesaretli"
            }
            
            tendencies = {}
            
            for emotion, query in emotional_queries.items():
                # Generate embedding for emotional query
                query_embedding = self.model.encode([query])[0]
                query_embedding = query_embedding / np.linalg.norm(query_embedding)
                
                # Calculate similarity with user's emotional embedding
                similarity = np.dot(emotional_embedding, query_embedding)
                tendencies[emotion] = float(similarity)
            
            return tendencies
            
        except Exception as e:
            logger.error(f"Error calculating emotional tendencies: {str(e)}")
            return {}
    
    def get_user_emotional_profile(self, user_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Get user's emotional profile"""
        try:
            from app.models.user_interaction import UserEmotionalProfile
            
            profile = db.query(UserEmotionalProfile).filter(
                UserEmotionalProfile.user_id == user_id
            ).first()
            
            if not profile:
                return None
            
            return {
                "user_id": profile.user_id,
                "emotional_embedding": np.array(profile.emotional_embedding) if profile.emotional_embedding else None,
                "total_watched_movies": profile.total_watched_movies,
                "emotional_tendencies": profile.emotional_tendencies,
                "profile_confidence": profile.profile_confidence,
                "last_updated": profile.last_updated
            }
            
        except Exception as e:
            logger.error(f"Error getting user emotional profile: {str(e)}")
            return None
    
    def get_hybrid_recommendations_efficient(self, 
                                          user_id: int,
                                          emotion_text: str,
                                          db: Session,
                                          top_k: int = 10,
                                          emotion_weight: float = 0.7,
                                          content_type: str = "movie") -> List[Dict[str, Any]]:
        """Get hybrid recommendations using pre-calculated user emotional profile"""
        try:
            # Get user's emotional profile
            user_profile = self.get_user_emotional_profile(user_id, db)
            
            if not user_profile or user_profile["emotional_embedding"] is None:
                logger.warning(f"No emotional profile found for user {user_id}, falling back to basic method")
                return self.get_hybrid_recommendations(emotion_text, [], top_k, emotion_weight, content_type)
            
            # Generate emotion embedding for current text
            emotion_embedding = self.model.encode([emotion_text])[0]
            emotion_embedding = emotion_embedding / np.linalg.norm(emotion_embedding)
            
            # Get user's historical emotional embedding
            user_emotional_embedding = user_profile["emotional_embedding"]
            
            # Combine current emotion with historical profile
            hybrid_embedding = (emotion_weight * emotion_embedding + 
                              (1 - emotion_weight) * user_emotional_embedding)
            hybrid_embedding = hybrid_embedding / np.linalg.norm(hybrid_embedding)
            
            # Search for similar content
            scores, indices = self.index.search(hybrid_embedding.reshape(1, -1), top_k * 2)
            
            # Prepare results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.content_data):
                    content = self.content_data[idx].copy()
                    
                    if content_type and content["content_type"] != content_type:
                        continue
                    
                    content["similarity_score"] = float(score)
                    content["rank"] = len(results) + 1
                    content["recommendation_type"] = "hybrid_efficient"
                    content["user_profile_confidence"] = user_profile["profile_confidence"]
                    
                    results.append(content)
                    
                    if len(results) >= top_k:
                        break
            
            logger.info(f"Generated {len(results)} efficient hybrid recommendations for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error generating efficient hybrid recommendations: {str(e)}")
            return [] 