from enum import IntEnum

class MovieGenre(IntEnum):
    """TMDB Movie Genres - https://developer.themoviedb.org/reference/genre-movie-list"""
    ACTION = 28
    ADVENTURE = 12
    ANIMATION = 16
    COMEDY = 35
    CRIME = 80
    DOCUMENTARY = 99
    DRAMA = 18
    FAMILY = 10751
    FANTASY = 14
    HISTORY = 36
    HORROR = 27
    MUSIC = 10402
    MYSTERY = 9648
    ROMANCE = 10749
    SCIENCE_FICTION = 878
    TV_MOVIE = 10770
    THRILLER = 53
    WAR = 10752
    WESTERN = 37

class TVGenre(IntEnum):
    """TMDB TV Genres - https://developer.themoviedb.org/reference/genre-tv-list"""
    ACTION_ADVENTURE = 10759
    ANIMATION = 16
    COMEDY = 35
    CRIME = 80
    DOCUMENTARY = 99
    DRAMA = 18
    FAMILY = 10751
    KIDS = 10762
    MYSTERY = 9648
    NEWS = 10763
    REALITY = 10764
    SCIENCE_FICTION_FANTASY = 10765
    SOAP = 10766
    TALK = 10767
    WAR_POLITICS = 10768
    WESTERN = 37

class GenreHelper:
    """Genre yardımcı sınıfı"""
    
    @staticmethod
    def get_movie_genre_name(genre_id: int) -> str:
        """Movie genre ID'sinden isim döndür"""
        try:
            return MovieGenre(genre_id).name.replace('_', ' ').title()
        except ValueError:
            return "Unknown"
    
    @staticmethod
    def get_tv_genre_name(genre_id: int) -> str:
        """TV genre ID'sinden isim döndür"""
        try:
            return TVGenre(genre_id).name.replace('_', ' ').title()
        except ValueError:
            return "Unknown"
    
    @staticmethod
    def get_all_movie_genres() -> dict:
        """Tüm movie genre'lerini ID:Name formatında döndür"""
        return {genre.value: genre.name.replace('_', ' ').title() for genre in MovieGenre}
    
    @staticmethod
    def get_all_tv_genres() -> dict:
        """Tüm TV genre'lerini ID:Name formatında döndür"""
        return {genre.value: genre.name.replace('_', ' ').title() for genre in TVGenre}
    
    @staticmethod
    def get_popular_movie_genres() -> list:
        """En popüler movie genre'lerini döndür"""
        popular_ids = [
            MovieGenre.ACTION.value,
            MovieGenre.COMEDY.value,
            MovieGenre.DRAMA.value,
            MovieGenre.HORROR.value,
            MovieGenre.ROMANCE.value,
            MovieGenre.THRILLER.value,
            MovieGenre.SCIENCE_FICTION.value,
            MovieGenre.ADVENTURE.value
        ]
        return [MovieGenre(genre_id) for genre_id in popular_ids]
    
    @staticmethod
    def get_popular_tv_genres() -> list:
        """En popüler TV genre'lerini döndür"""
        popular_ids = [
            TVGenre.DRAMA.value,
            TVGenre.COMEDY.value,
            TVGenre.ACTION_ADVENTURE.value,
            TVGenre.SCIENCE_FICTION_FANTASY.value,
            TVGenre.CRIME.value,
            TVGenre.MYSTERY.value,
            TVGenre.ANIMATION.value,
            TVGenre.FAMILY.value
        ]
        return [TVGenre(genre_id) for genre_id in popular_ids]

