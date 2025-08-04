# Parotia - Film ve Dizi Öneri Sistemi

Parotia, kullanıcıların duygu durumlarına göre kişiselleştirilmiş film ve dizi önerileri sunan akıllı bir platform'dur.

## 🌟 Özellikler

### 🤖 AI Tabanlı Akıllı Sistemler

- **Hibrit Öneri Motoru**: Duygu analizi + İçerik embeddings + Kullanıcı geçmişi
- **Duygu Analizi**: 10 farklı duygu kategorisinde NLP tabanlı analiz
- **Embedding Benzerlik**: Sentence-Transformers ile semantik benzerlik
- **FAISS Indexing**: Milyonlarca içerik için optimized vektör arama
- **Sürekli Öğrenme**: Kullanıcı geri bildirimlerine dayalı profil geliştirme

### 📊 Platform Özellikleri

- **Film & Dizi Veritabanı**: TMDB entegrasyonu ile geniş içerik kütüphanesi
- **Kullanıcı Yönetimi**: Güvenli kayıt ve giriş sistemi
- **İzleme Listesi**: Favori içerikleri kaydetme ve takip etme
- **Duygusal Ton Analizi**: İçeriklerin ruh haline uygunluk skorları
- **Akıllı Bildirim Sistemi**: Kişiselleştirilmiş geri bildirim talepleri

## 🚀 Teknolojiler

### 🧠 AI & Machine Learning
- **Sentence-Transformers**: all-MiniLM-L6-v2 modeli ile metin embedding
- **FAISS**: Facebook AI Similarity Search - Optimized vektör indexing
- **Cosine Similarity**: Embedding vektörleri arası benzerlik hesaplama
- **NLP**: Natural Language Processing ile duygu analizi
- **Scikit-learn**: Machine learning algoritmaları
- **NumPy**: Matematik ve vektör işlemleri

### 🖥️ Backend
- **FastAPI**: Modern, hızlı web API framework'ü
- **Python 3.8+**: Ana programlama dili
- **SQLAlchemy**: ORM ve veritabanı yönetimi
- **TMDB API**: Film ve dizi verileri
- **JWT**: Güvenli kimlik doğrulama


## 🛠️ Kurulum

### Backend Kurulumu

1. Repository'yi klonlayın:
```bash
git clone https://github.com/kullaniciadi/parotia.git
cd parotia
```

2. Sanal ortam oluşturun:
```bash
cd backend
python -m venv venv
```

3. Sanal ortamı aktifleştirin:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

4. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

5. Environment değişkenlerini ayarlayın:
```bash
# .env dosyası oluşturun
TMDB_API_KEY=your_tmdb_api_key_here
DATABASE_URL=sqlite:///./parotia.db
```

6. Veritabanını oluşturun:
```bash
python create_tables.py
```

7. AI modelleri indirin (ilk çalıştırmada otomatik):
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

8. Uygulamayı başlatın:
```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> **Not**: İlk çalıştırmada AI modeli (~90MB) indirilir ve FAISS index oluşturulur. Bu işlem 5-10 dakika sürebilir.

## 📚 API Dokümantasyonu

API detayları için `FRONTEND_API_DOKUMANTASYONU.md` dosyasını inceleyebilirsiniz.

Swagger dokümantasyonu: `http://localhost:8000/docs`

## 🗂️ Proje Yapısı

```
parotia/
├── backend/
│   ├── app/
│   │   ├── core/          # Temel konfigürasyon ve servisler
│   │   ├── models/        # Veritabanı modelleri
│   │   ├── routers/       # API endpoint'leri
│   │   ├── services/      # İş mantığı servisleri
│   │   └── schemas/       # Pydantic şemaları
│   └── requirements.txt
├── frontend/              # (Planlanan)
└── README.md
```



## 🧠 AI Sistemi Teknik Detayları

### Hibrit Öneri Mimarisi

Parotia, 3 farklı AI sistemini birleştiren gelişmiş bir hibrit yapı kullanır:

 **Embedding Benzerlik Sistemi**
   - Sentence-Transformers all-MiniLM-L6-v2 modeli
   - 384 boyutlu vektör embeddings
   - Cosine similarity ile benzerlik hesaplama
   - FAISS ile optimized vektör arama

 **Kolaboratif Filtreleme**
   - Kullanıcı izleme geçmişi analizi
   - Benzer kullanıcı davranış kalıpları
   - Rating tabanlı öneriler


### Embedding Oluşturma Süreci

1. **TMDB Veri Toplama**: Film/dizi metadata'sı
2. **Metin Oluşturma**: Başlık + özet + tür + oyuncular
3. **Embedding**: Sentence-Transformers ile vektörizasyon
4. **Indexing**: FAISS ile optimized depolama
5. **Cache**: Pickle ile performans optimizasyonu


## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## 📞 İletişim

Proje ile ilgili sorularınız için issue açabilir veya geliştiricilerle iletişime geçebilirsiniz.

