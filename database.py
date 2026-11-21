from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Isletme(db.Model):
    __tablename__ = 'isletmeler'
    isletme_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isletme_adi = db.Column(db.String(100), unique=True, nullable=False)
    sifre = db.Column(db.String(200), nullable=False)
    
    urunler = db.relationship('Urun', backref='isletme', cascade='all, delete-orphan')

class Urun(db.Model):
    __tablename__ = 'urunler'
    urun_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isletme_id = db.Column(db.Integer, db.ForeignKey('isletmeler.isletme_id'), nullable=False)
    sira_no = db.Column(db.Integer, nullable=False)
    barkod_no = db.Column(db.String(100), nullable=False)
    urun_adi = db.Column(db.String(150), nullable=False)
    fiyat = db.Column(db.Float, default=0.0)
    maliyet = db.Column(db.Float, default=0.0)     # Alış / Maliyet Fiyatı
    # Sadece mevcut stok miktarı var, uyarı sınırı yok
    stok_miktari = db.Column(db.Integer, default=0, nullable=False)
    
    resim_yolu = db.Column(db.String(255), nullable=True)
    barkod_gorsel_yolu = db.Column(db.String(255), nullable=True)
    
    loglar = db.relationship('UrunLog', backref='urun', cascade='all, delete-orphan') 
    hatirlatici = db.relationship('Hatirlatici', backref='urun', uselist=False, cascade='all, delete-orphan')
 

class UrunLog(db.Model):
    __tablename__ = 'urun_loglar'
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isletme_id = db.Column(db.Integer, db.ForeignKey('isletmeler.isletme_id'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.urun_id'), nullable=False)
    
    islem_turu = db.Column(db.String(50), nullable=False) # Örn: 'STOK_EKLEME', 'SATIS_CIKIS'
    miktar_degisimi = db.Column(db.Integer, default=0)
    aciklama = db.Column(db.Text, nullable=True)
    tarih = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Hatirlatici(db.Model):
    """Bir ürünün stoğu 'esik' değerine veya altına düşünce bildirim üretir."""
    __tablename__ = 'hatirlaticilar'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isletme_id = db.Column(db.Integer, db.ForeignKey('isletmeler.isletme_id'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.urun_id'), nullable=False, unique=True)
    esik = db.Column(db.Integer, nullable=False)
    tetiklendi = db.Column(db.Boolean, default=False, nullable=False)  # aynı uyarı tekrar tekrar gelmesin

class Bildirim(db.Model):
    __tablename__ = 'bildirimler'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isletme_id = db.Column(db.Integer, db.ForeignKey('isletmeler.isletme_id'), nullable=False)
    mesaj = db.Column(db.Text, nullable=False)
    okundu = db.Column(db.Boolean, default=False, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
