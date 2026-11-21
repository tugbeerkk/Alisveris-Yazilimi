import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, send_file
import io, zipfile
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import *
from barkodcreate import *
from datetime import datetime
from hatirlatici import hatirlatici_bp, hatirlatici_kontrol, bildirim_context

app = Flask(__name__)
app.secret_key = 'isletme_yonetim_gizli_anahtari'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def dosya_uzantisi_uygun_mu(dosya_adi):
    return '.' in dosya_adi and dosya_adi.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)
app.register_blueprint(hatirlatici_bp)
app.context_processor(bildirim_context)

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
@app.route('/kayit', methods=['GET', 'POST'])
def kayit():
    if 'isletme_id' in session:
        return redirect(url_for('panel'))

    if request.method == 'POST':
        isletme_adi = request.form['isletme_adi']
        sifre = request.form['sifre']

        existing = Isletme.query.filter_by(isletme_adi=isletme_adi).first()
        if existing:
            flash('Bu işletme adı zaten sistemde kayıtlı!', 'danger')
            return redirect(url_for('kayit'))

        hashed_password = generate_password_hash(sifre, method='pbkdf2:sha256')
        yeni_isletme = Isletme(isletme_adi=isletme_adi, sifre=hashed_password)
        
        db.session.add(yeni_isletme)
        db.session.commit()

        session['isletme_id'] = yeni_isletme.isletme_id
        session['isletme_adi'] = yeni_isletme.isletme_adi
        return redirect(url_for('panel'))

    return render_template('kayit.html')

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    if 'isletme_id' in session:
        return redirect(url_for('panel'))

    if request.method == 'POST':
        isletme_adi = request.form['isletme_adi']
        sifre = request.form['sifre']

        isletme = Isletme.query.filter_by(isletme_adi=isletme_adi).first()
        if isletme and check_password_hash(isletme.sifre, sifre):
            session['isletme_id'] = isletme.isletme_id
            session['isletme_adi'] = isletme.isletme_adi
            return redirect(url_for('panel'))
        else:
            flash('İşletme adı veya şifre hatalı!', 'danger')

    return render_template('giris.html')

@app.route('/barkod', methods=['GET', 'POST'])
def barkod():
    if 'isletme_id' not in session:
        flash('Lütfen önce kayıt olun veya giriş yapın.', 'warning')
        return redirect(url_for('kayit'))

    isletme = db.session.get(Isletme, session['isletme_id'])
    if not isletme:
        session.clear()
        return redirect(url_for('kayit'))

    if request.method == 'POST':
        urun_adi = request.form.get('urun_adi', '').strip()
        if not urun_adi:
            flash('Lütfen bir ürün adı giriniz!', 'danger')
            return redirect(url_for('barkod'))

        try:
            fiyat = float(request.form.get('fiyat', 0.0))
        except ValueError:
            fiyat = 0.0

        try:
            maliyet = float(request.form.get('maliyet', 0.0))
        except ValueError:
            maliyet = 0.0

        try:
            stok_miktari = int(request.form.get('stok_miktari', 0))
        except ValueError:
            stok_miktari = 0

        en_buyuk_sira = db.session.query(db.func.max(Urun.sira_no)).filter_by(isletme_id=isletme.isletme_id).scalar()
        
        sira_no = (en_buyuk_sira or 0) + 1
        
        barkod_no = createbaracodecode(isletme.isletme_id, sira_no)
        
        barkod_gorsel_yolu = createbar(barkod_no, barkod_no)

        resim_yolu = None
        if 'resim' in request.files:
            dosya = request.files['resim']
            if dosya and dosya.filename != '' and dosya_uzantisi_uygun_mu(dosya.filename):
                guvenli_isim = secure_filename(dosya.filename)
                dosya_adi = f"urun_{isletme.isletme_id}_{guvenli_isim}"
                kayit_yeri = os.path.join(app.config['UPLOAD_FOLDER'], dosya_adi)
                dosya.save(kayit_yeri)
                resim_yolu = f"uploads/{dosya_adi}"

        yeni_urun = Urun(
            isletme_id=isletme.isletme_id,
            sira_no=sira_no,
            barkod_no=barkod_no,
            urun_adi=urun_adi,
            fiyat=fiyat,
            maliyet=maliyet,        
            stok_miktari=stok_miktari,
            resim_yolu=resim_yolu,
            barkod_gorsel_yolu=barkod_gorsel_yolu
        )
        db.session.add(yeni_urun)
        db.session.commit()
        
        flash('Ürün, maliyet, stok ve barkod görseli başarıyla eklendi!', 'success')
        return redirect(url_for('barkod'))

    urunler = Urun.query.filter_by(isletme_id=isletme.isletme_id).all()
    return render_template('barkod.html', isletme=isletme, urunler=urunler)

@app.route('/Panele')
def Panele():
    if 'isletme_id' not in session:
            return redirect(url_for('kayit'))

    return redirect(url_for('panel'))

@app.route('/urun')
def urun():
    if 'isletme_id' not in session:
        flash('Lütfen önce kayıt olun veya giriş yapın.', 'warning')
        return redirect(url_for('kayit'))

    isletme = db.session.get(Isletme, session['isletme_id'])
    if not isletme:
        session.clear()
        return redirect(url_for('kayit'))

    urunler = Urun.query.filter_by(isletme_id=isletme.isletme_id).all()

    return render_template('urun.html', isletme=isletme, urunler=urunler)

@app.route('/urun-sil/<int:urun_id>')
def urun_sil(urun_id):
    if 'isletme_id' not in session:
        flash('Lütfen önce giriş yapın.', 'warning')
        return redirect(url_for('kayit'))
    
    urun = db.session.get(Urun, urun_id)
    
    if not urun or urun.isletme_id != session['isletme_id']:
        flash('Bu işlemi gerçekleştirmeye yetkiniz yok veya ürün bulunamadı.', 'danger')
        return redirect(url_for('barkod'))
    
    if urun.barkod_gorsel_yolu and os.path.exists(urun.barkod_gorsel_yolu):
        try:
            os.remove(urun.barkod_gorsel_yolu)
        except Exception as e:
            print(f"Barkod görseli silinirken hata oluştu: {e}")
            
    if urun.resim_yolu and os.path.exists(urun.resim_yolu):
        try:
            os.remove(urun.resim_yolu)
        except Exception as e:
            print(f"Ürün resmi silinirken hata oluştu: {e}")
            
    db.session.delete(urun)
    db.session.commit()
    
    flash('Ürün ve ilgili tüm görseller başarıyla silindi.', 'info')
    return redirect(url_for('barkod'))

@app.route('/panel', methods=['GET', 'POST'])
def panel():
    if 'isletme_id' not in session:
        flash('Lütfen önce kayıt olun veya giriş yapın.', 'warning')
        return redirect(url_for('kayit'))
    
    isletme = db.session.get(Isletme, session['isletme_id'])
    if not isletme:
        session.clear()
        return redirect(url_for('kayit'))
    
    urunler = Urun.query.filter_by(isletme_id=isletme.isletme_id).all()
    return render_template('panel.html', isletme=isletme, urunler=urunler)

@app.route('/stok-ekle/<int:urun_id>', methods=['POST'])
def stok_ekle(urun_id):
    if 'isletme_id' not in session:
        flash('Lütfen önce giriş yapın.', 'warning')
        return redirect(url_for('kayit'))

    urun = db.session.get(Urun, urun_id)
    if not urun or urun.isletme_id != session['isletme_id']:
        flash('Ürün bulunamadı.', 'danger')
        return redirect(url_for('urun'))

    try:
        miktar = int(request.form.get('miktar', ''))
        if miktar <= 0:
            raise ValueError
    except ValueError:
        flash('Lütfen 1 veya daha büyük bir adet girin.', 'danger')
        return redirect(url_for('urun'))

    urun.stok_miktari += miktar
    db.session.add(UrunLog(
        isletme_id=urun.isletme_id,
        urun_id=urun.urun_id,
        islem_turu='STOK_EKLEME',
        miktar_degisimi=miktar,
        aciklama=f"'{urun.urun_adi}' ürününe {miktar} adet stok eklendi. Yeni stok: {urun.stok_miktari}"
    ))
    db.session.commit()
    flash(f"'{urun.urun_adi}' stoğuna {miktar} adet eklendi. Yeni stok: {urun.stok_miktari}", 'success')
    return redirect(url_for('urun'))

@app.route('/barkod-indir/<int:urun_id>')
def barkod_indir(urun_id):
    if 'isletme_id' not in session:
        return redirect(url_for('kayit'))
    urun = db.session.get(Urun, urun_id)
    if not urun or urun.isletme_id != session['isletme_id'] or not urun.barkod_gorsel_yolu:
        flash('Barkod görseli bulunamadı.', 'danger')
        return redirect(url_for('urun'))
    if not os.path.exists(os.path.join(app.static_folder, urun.barkod_gorsel_yolu)):
        flash('Barkod dosyası sunucuda bulunamadı.', 'danger')
        return redirect(url_for('urun'))
    isim = secure_filename(f"{urun.urun_adi}_{urun.barkod_no}") or urun.barkod_no
    return send_from_directory(app.static_folder, urun.barkod_gorsel_yolu,
                               as_attachment=True, download_name=f"{isim}.png")

@app.route('/barkodlar-indir')
def barkodlar_indir():
    if 'isletme_id' not in session:
        return redirect(url_for('kayit'))
    urunler = Urun.query.filter_by(isletme_id=session['isletme_id']).all()
    tampon = io.BytesIO()
    adet = 0
    with zipfile.ZipFile(tampon, 'w', zipfile.ZIP_DEFLATED) as zf:
        for u in urunler:
            if not u.barkod_gorsel_yolu:
                continue
            yol = os.path.join(app.static_folder, u.barkod_gorsel_yolu)
            if os.path.exists(yol):
                isim = secure_filename(f"{u.urun_adi}_{u.barkod_no}") or u.barkod_no
                zf.write(yol, f"{isim}.png")
                adet += 1
    if adet == 0:
        flash('İndirilecek barkod görseli yok.', 'warning')
        return redirect(url_for('urun'))
    tampon.seek(0)
    return send_file(tampon, mimetype='application/zip', as_attachment=True, download_name='barkodlar.zip')

@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('kayit'))

@app.route('/kasa', methods=['GET', 'POST'])
def kasa():
    if 'isletme_id' not in session:
        flash('Lütfen önce giriş yapın.', 'warning')
        return redirect(url_for('kayit'))

    isletme = db.session.get(Isletme, session['isletme_id'])
    
    if 'sepet' not in session:
        session['sepet'] = {} 

    if request.method == 'POST':
        barkod_no = request.form.get('barkod_no', '').strip()
        
        urun = Urun.query.filter_by(isletme_id=isletme.isletme_id, barkod_no=barkod_no).first()
        
        if urun:
            sepet = session['sepet']
            sepetteki = sepet.get(barkod_no, {}).get('adet', 0)
            if urun.stok_miktari <= 0:
                flash(f"'{urun.urun_adi}' ürününün stoğu tükenmiştir!", "danger")
            elif sepetteki >= urun.stok_miktari:
                flash(f"'{urun.urun_adi}' için yeterli stok yok (stok: {urun.stok_miktari}).", "danger")
            else:
                if barkod_no in sepet:
                    sepet[barkod_no]['adet'] += 1
                else:
                    sepet[barkod_no] = {
                        'urun_id': urun.urun_id,
                        'urun_adi': urun.urun_adi,
                        'fiyat': urun.fiyat,
                        'adet': 1
                    }
                session.modified = True
                flash(f"'{urun.urun_adi}' sepete eklendi.", "success")
        else:
            flash("Bu barkoda ait ürün bulunamadı!", "danger")
            
        return redirect(url_for('kasa'))

    loglar = UrunLog.query.filter_by(isletme_id=isletme.isletme_id).order_by(UrunLog.tarih.desc()).limit(15).all()
    
    return render_template('kasa.html', isletme=isletme, sepet=session.get('sepet', {}), loglar=loglar)

@app.route('/raporlar')
def raporlar():
    if 'isletme_id' not in session:
        return redirect(url_for('kayit'))

    isletme = db.session.get(Isletme, session['isletme_id'])

    satis_loglari = UrunLog.query.filter_by(
        isletme_id=isletme.isletme_id, 
        islem_turu='SATIS_CIKIS'
    ).all()

    aylik_veriler = {}

    for log in satis_loglari:
        ay_yil = log.tarih.strftime('%Y-%m')
        
        urun = db.session.get(Urun, log.urun_id)
        if urun:
            satis_fiyati = urun.fiyat
            maliyet = urun.maliyet
            birim_kar = satis_fiyati - maliyet
            
            if ay_yil not in aylik_veriler:
                aylik_veriler[ay_yil] = {'adet': 0, 'ciro': 0.0, 'kar': 0.0}
            
            n = abs(log.miktar_degisimi) or 1
            aylik_veriler[ay_yil]['adet'] += n
            aylik_veriler[ay_yil]['ciro'] += satis_fiyati * n
            aylik_veriler[ay_yil]['kar'] += birim_kar * n

    etiketler = list(aylik_veriler.keys()) 
    ciro_listesi = [veri['ciro'] for veri in aylik_veriler.values()]
    kar_listesi = [veri['kar'] for veri in aylik_veriler.values()]
    adet_listesi = [veri['adet'] for veri in aylik_veriler.values()]

    return render_template(
        'raporlar.html', 
        isletme=isletme, 
        aylik_veriler=aylik_veriler,
        etiketler=etiketler,
        ciro_listesi=ciro_listesi,
        kar_listesi=kar_listesi,
        adet_listesi=adet_listesi
    )

@app.route('/sepet-cikar/<barkod_no>')
def sepet_cikar(barkod_no):
    sepet = session.get('sepet', {})
    if barkod_no in sepet:
        sepet[barkod_no]['adet'] -= 1
        if sepet[barkod_no]['adet'] <= 0:
            del sepet[barkod_no]
        session['sepet'] = sepet
        session.modified = True
    return redirect(url_for('kasa'))

@app.route('/sepeti-bosalt')
def sepeti_bosalt():
    session.pop('sepet', None)
    flash('Sepet temizlendi.', 'info')
    return redirect(url_for('kasa'))

@app.route('/satis-tamamla')
def satis_tamamla():
    if 'isletme_id' not in session:
        flash('Lütfen önce giriş yapın.', 'warning')
        return redirect(url_for('kayit'))

    sepet = session.get('sepet', {})
    if not sepet:
        flash('Sepet boş, tamamlanacak satış yok.', 'warning')
        return redirect(url_for('kasa'))

    isletme_id = session['isletme_id']

    # 1) Önce hepsini doğrula: biri bile yetersizse hiçbir şey değişmesin
    satirlar = []
    for barkod_no, item in sepet.items():
        urun = db.session.get(Urun, item['urun_id'])
        if not urun or urun.isletme_id != isletme_id:
            flash(f"'{item['urun_adi']}' artık sistemde yok. Sepetten çıkarıp tekrar deneyin.", 'danger')
            return redirect(url_for('kasa'))
        if urun.stok_miktari < item['adet']:
            flash(f"'{urun.urun_adi}' için yeterli stok yok (stok: {urun.stok_miktari}, sepette: {item['adet']}).", 'danger')
            return redirect(url_for('kasa'))
        satirlar.append((barkod_no, urun, item))

    # 2) Stoğu düş ve her ürün için log yaz
    genel_toplam = 0
    for barkod_no, urun, item in satirlar:
        adet = item['adet']
        fiyat = item['fiyat'] or 0.0
        maliyet = urun.maliyet or 0.0
        toplam_kar = (fiyat - maliyet) * adet
        genel_toplam += fiyat * adet

        urun.stok_miktari -= adet
        db.session.add(UrunLog(
            isletme_id=isletme_id,
            urun_id=urun.urun_id,
            islem_turu='SATIS_CIKIS',
            miktar_degisimi=-adet,
            aciklama=f"'{urun.urun_adi}' x{adet} satıldı. Satış: {fiyat * adet}₺, Kâr: {toplam_kar:.2f}₺ (Barkod: {barkod_no})"
        ))
    db.session.commit()

    # 3) Stok hatırlatıcılarını kontrol et
    for barkod_no, urun, item in satirlar:
        uyari = hatirlatici_kontrol(urun)
        if uyari:
            flash(uyari, 'warning')

    session.pop('sepet', None)
    flash(f'Satış tamamlandı. Toplam: {genel_toplam} ₺', 'success')
    return redirect(url_for('kasa'))

if __name__ == '__main__':
    app.run(debug=True)